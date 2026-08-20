"""
Invoice numbering, line items, payments, M-Pesa, and refunds (BRD §6.9;
Solution Spec Flow 5.7). Invoice numbering mirrors patients.services'
MRN pattern exactly: server-side generation, retry-on-collision against
the UNIQUE constraint rather than a locked sequence (Data Dictionary §8).
"""

import datetime
import decimal
import logging
import uuid

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.billing.models import Invoice, InvoiceLineItem, MpesaTransaction, Payment, Refund

logger = logging.getLogger(__name__)

MAX_INVOICE_NUMBER_ATTEMPTS = 5

# BRD §6.9 requires approval above a discount threshold but the BRD document
# itself isn't in this repo (see docs/README.md) to read the actual figure
# from — this is a placeholder pending the real number, not a guess dressed
# up as spec.
DISCOUNT_APPROVAL_THRESHOLD = 1000


class DiscountApprovalRequiredError(Exception):
    pass


class SameCashierRefundError(Exception):
    pass


class RefundExceedsPaymentError(Exception):
    pass


def _next_invoice_number_candidate(facility):
    year = datetime.date.today().year
    prefix = f"INV-{facility.code}-{year}-"
    last = (
        Invoice.objects.filter(facility=facility, invoice_number__startswith=prefix)
        .order_by("-invoice_number")
        .first()
    )
    next_seq = 1
    if last:
        try:
            next_seq = int(last.invoice_number.rsplit("-", 1)[-1]) + 1
        except ValueError:
            next_seq = 1
    return f"{prefix}{next_seq:06d}"


def get_or_create_open_invoice(
    *, facility, patient, visit=None, created_by, actor=None, ip_address=None
):
    """
    Every service-generating action for the same visit lands on one
    invoice, not a new one per line item — find the visit's still-open
    invoice first, only create when none exists.
    """
    if visit is not None:
        existing = Invoice.objects.filter(
            facility=facility, visit=visit, status=Invoice.Status.OPEN
        ).first()
        if existing:
            return existing

    for _ in range(MAX_INVOICE_NUMBER_ATTEMPTS):
        invoice_number = _next_invoice_number_candidate(facility)
        invoice = Invoice(
            facility=facility,
            patient=patient,
            visit=visit,
            invoice_number=invoice_number,
            created_by=created_by,
        )
        try:
            with transaction.atomic():
                invoice.save(actor=actor, ip_address=ip_address)
            return invoice
        except IntegrityError:
            continue

    raise RuntimeError(
        f"Could not generate a unique invoice number for facility {facility.code} "
        f"after {MAX_INVOICE_NUMBER_ATTEMPTS} attempts."
    )


def _recompute_totals(invoice, *, actor=None, ip_address=None):
    from django.db.models import Sum

    subtotal = invoice.line_items.aggregate(total=Sum("amount"))["total"] or 0
    total = subtotal - invoice.discount + invoice.tax
    # CONFIRMED and REFUNDED both represent money that was actually
    # received — a payment approve_refund() has fully refunded still
    # belongs in "paid", with the refund itself (subtracted below) being
    # what nets it back out. Filtering to CONFIRMED only would double-count
    # the reversal: once as the payment silently dropping out of "paid",
    # and again as the refund amount added back — inflating balance past
    # the invoice's own total, caught live via the web console on a
    # partial refund.
    paid = (
        invoice.payments.filter(
            status__in=[Payment.Status.CONFIRMED, Payment.Status.REFUNDED]
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    refunded = invoice.refunds.aggregate(total=Sum("amount"))["total"] or 0
    net_paid = paid - refunded
    balance = total - net_paid

    invoice.subtotal = subtotal
    invoice.total = total
    invoice.balance = balance
    if balance <= 0:
        invoice.status = Invoice.Status.PAID
    elif net_paid > 0:
        invoice.status = Invoice.Status.PARTIALLY_PAID
    elif invoice.status not in (Invoice.Status.WRITTEN_OFF, Invoice.Status.PENDING_CONFIRMATION):
        invoice.status = Invoice.Status.OPEN
    invoice.save(actor=actor, ip_address=ip_address)


def add_line_item(
    invoice,
    *,
    source_module,
    source_reference_id,
    description,
    unit_price,
    quantity=1,
    actor=None,
    ip_address=None,
):
    line_item = InvoiceLineItem(
        invoice=invoice,
        source_module=source_module,
        source_reference_id=source_reference_id,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
        amount=decimal.Decimal(unit_price) * quantity,
    )
    line_item.save(actor=actor, ip_address=ip_address)
    _recompute_totals(invoice, actor=actor, ip_address=ip_address)
    return line_item


def apply_discount(invoice, *, amount, approved_by=None, actor=None, ip_address=None):
    if amount > DISCOUNT_APPROVAL_THRESHOLD and approved_by is None:
        raise DiscountApprovalRequiredError(
            f"A discount over {DISCOUNT_APPROVAL_THRESHOLD} requires approval."
        )
    invoice.discount = amount
    _recompute_totals(invoice, actor=actor, ip_address=ip_address)
    return invoice


def record_payment(
    invoice, *, method, amount, reference="", received_by=None, actor=None, ip_address=None
):
    """Cash/card/bank/insurance settle immediately. mpesa goes through
    initiate_mpesa_stk_push()/process_mpesa_callback() instead — a payment
    record isn't confirmed until the gateway says so."""
    payment = Payment(
        invoice=invoice,
        method=method,
        amount=amount,
        reference=reference,
        status=Payment.Status.CONFIRMED,
        received_by=received_by,
        received_at=timezone.now(),
    )
    payment.save(actor=actor, ip_address=ip_address)
    _recompute_totals(invoice, actor=actor, ip_address=ip_address)
    return payment


def initiate_mpesa_stk_push(invoice, *, phone_number, amount, actor=None, ip_address=None):
    """
    STUB: no real Safaricom Daraja integration — this hospital doesn't have
    sandbox/production credentials to call out to. Creates the real,
    queryable Payment/MpesaTransaction rows (status=pending/requested) that
    a real integration would create too, so process_mpesa_callback() below
    has something real to react to; just doesn't actually reach Safaricom.
    """
    payment = Payment(
        invoice=invoice,
        method=Payment.Method.MPESA,
        amount=amount,
        status=Payment.Status.PENDING,
        received_at=timezone.now(),
    )
    payment.save(actor=actor, ip_address=ip_address)

    checkout_request_id = f"ws_CO_{uuid.uuid4().hex}"
    mpesa_transaction = MpesaTransaction(
        payment=payment, checkout_request_id=checkout_request_id, phone_number=phone_number
    )
    mpesa_transaction.save(actor=actor, ip_address=ip_address)

    invoice.status = Invoice.Status.PENDING_CONFIRMATION
    invoice.save(actor=actor, ip_address=ip_address)

    logger.warning(
        "M-Pesa STK push requested but not actually sent (no Daraja integration): %s",
        checkout_request_id,
    )
    return mpesa_transaction


def process_mpesa_callback(
    checkout_request_id, *, success, mpesa_receipt_number="", raw_payload=None, actor=None
):
    """Idempotent — a retried callback for an already-resolved transaction
    is a no-op, per Flow 5.7 step 5's idempotency-key requirement."""
    mpesa_transaction = MpesaTransaction.objects.get(checkout_request_id=checkout_request_id)
    if mpesa_transaction.status != MpesaTransaction.Status.REQUESTED:
        return mpesa_transaction

    mpesa_transaction.status = (
        MpesaTransaction.Status.CONFIRMED if success else MpesaTransaction.Status.FAILED
    )
    mpesa_transaction.mpesa_receipt_number = mpesa_receipt_number
    mpesa_transaction.callback_payload = raw_payload
    mpesa_transaction.save(actor=actor)

    payment = mpesa_transaction.payment
    payment.status = Payment.Status.CONFIRMED if success else Payment.Status.FAILED
    payment.reference = mpesa_receipt_number
    payment.save(actor=actor)

    _recompute_totals(payment.invoice, actor=actor)
    return mpesa_transaction


def approve_refund(invoice, payment, *, amount, reason, approved_by, actor=None, ip_address=None):
    if approved_by == payment.received_by:
        raise SameCashierRefundError(
            "The cashier who took this payment cannot also approve its refund."
        )

    from django.db.models import Sum

    already_refunded = payment.refunds.aggregate(total=Sum("amount"))["total"] or 0
    remaining = payment.amount - already_refunded
    if amount > remaining:
        raise RefundExceedsPaymentError(
            f"Cannot refund {amount}, only {remaining} of this payment remains refundable "
            f"({already_refunded} already refunded of {payment.amount})."
        )

    refund = Refund(
        invoice=invoice,
        payment=payment,
        amount=amount,
        reason=reason,
        approved_by=approved_by,
        approved_at=timezone.now(),
    )
    refund.save(actor=actor, ip_address=ip_address)

    # Only a *full* refund flips the payment's own status — Payment.Status
    # has no "partially_refunded" state (Data Dictionary §8), and marking
    # a payment fully REFUNDED after only part of it came back would make
    # _recompute_totals() stop counting any of it as paid, inflating the
    # invoice's balance past its own total. A partial refund is expressed
    # entirely through the Refund row and the balance calculation below,
    # not through the original payment's status.
    if already_refunded + amount >= payment.amount:
        payment.status = Payment.Status.REFUNDED
        payment.save(actor=actor, ip_address=ip_address)

    _recompute_totals(invoice, actor=actor, ip_address=ip_address)
    return refund
