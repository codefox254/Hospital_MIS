import pytest

from apps.accounts.factories import UserFactory
from apps.billing.factories import InvoiceFactory, PaymentFactory
from apps.billing.models import Invoice, MpesaTransaction, Payment
from apps.billing.services import (
    DISCOUNT_APPROVAL_THRESHOLD,
    DiscountApprovalRequiredError,
    RefundExceedsPaymentError,
    SameCashierRefundError,
    add_line_item,
    apply_discount,
    approve_refund,
    get_or_create_open_invoice,
    initiate_mpesa_stk_push,
    process_mpesa_callback,
    record_payment,
)
from apps.core.factories import FacilityFactory
from apps.opd.factories import VisitFactory
from apps.patients.factories import PatientFactory

pytestmark = pytest.mark.django_db


class TestGetOrCreateOpenInvoice:
    @pytest.mark.smoke
    def test_creates_a_new_invoice_with_a_generated_number(self):
        facility = FacilityFactory()
        patient = PatientFactory(facility=facility)
        creator = UserFactory(facility=facility)

        invoice = get_or_create_open_invoice(facility=facility, patient=patient, created_by=creator)

        assert invoice.invoice_number.startswith(f"INV-{facility.code}-")
        assert invoice.status == Invoice.Status.OPEN

    def test_reuses_the_open_invoice_for_the_same_visit(self):
        visit = VisitFactory()
        creator = UserFactory(facility=visit.facility)

        first = get_or_create_open_invoice(
            facility=visit.facility, patient=visit.patient, visit=visit, created_by=creator
        )
        second = get_or_create_open_invoice(
            facility=visit.facility, patient=visit.patient, visit=visit, created_by=creator
        )

        assert first.id == second.id

    def test_different_visits_get_different_invoices(self):
        visit_one = VisitFactory()
        visit_two = VisitFactory(facility=visit_one.facility, department=visit_one.department)
        creator = UserFactory(facility=visit_one.facility)

        invoice_one = get_or_create_open_invoice(
            facility=visit_one.facility,
            patient=visit_one.patient,
            visit=visit_one,
            created_by=creator,
        )
        invoice_two = get_or_create_open_invoice(
            facility=visit_two.facility,
            patient=visit_two.patient,
            visit=visit_two,
            created_by=creator,
        )

        assert invoice_one.id != invoice_two.id


class TestAddLineItem:
    @pytest.mark.smoke
    def test_adds_a_line_item_and_recomputes_totals(self):
        invoice = InvoiceFactory()

        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
            quantity=1,
        )

        invoice.refresh_from_db()
        assert invoice.subtotal == 500
        assert invoice.total == 500
        assert invoice.balance == 500

    def test_multiple_line_items_accumulate(self):
        invoice = InvoiceFactory()

        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
        )
        add_line_item(
            invoice,
            source_module="pharmacy",
            source_reference_id="00000000-0000-0000-0000-000000000002",
            description="Amoxicillin x15",
            unit_price="20.00",
            quantity=15,
        )

        invoice.refresh_from_db()
        assert invoice.subtotal == 800
        assert invoice.balance == 800


class TestApplyDiscount:
    @pytest.mark.smoke
    def test_small_discount_does_not_require_approval(self):
        invoice = InvoiceFactory()
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
        )

        apply_discount(invoice, amount=100)

        invoice.refresh_from_db()
        assert invoice.discount == 100
        assert invoice.total == 400

    def test_large_discount_requires_approval(self):
        invoice = InvoiceFactory()

        with pytest.raises(DiscountApprovalRequiredError):
            apply_discount(invoice, amount=DISCOUNT_APPROVAL_THRESHOLD + 1)

    def test_large_discount_succeeds_when_approved(self):
        invoice = InvoiceFactory()
        approver = UserFactory(facility=invoice.facility)
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Major procedure",
            unit_price="5000.00",
        )

        apply_discount(invoice, amount=DISCOUNT_APPROVAL_THRESHOLD + 1, approved_by=approver)

        invoice.refresh_from_db()
        assert invoice.discount == DISCOUNT_APPROVAL_THRESHOLD + 1


class TestRecordPayment:
    @pytest.mark.smoke
    def test_cash_payment_settles_the_balance(self):
        invoice = InvoiceFactory()
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
        )
        cashier = UserFactory(facility=invoice.facility)

        record_payment(invoice, method=Payment.Method.CASH, amount=500, received_by=cashier)

        invoice.refresh_from_db()
        assert invoice.balance == 0
        assert invoice.status == Invoice.Status.PAID

    def test_partial_payment_marks_the_invoice_partially_paid(self):
        invoice = InvoiceFactory()
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
        )
        cashier = UserFactory(facility=invoice.facility)

        record_payment(invoice, method=Payment.Method.CASH, amount=200, received_by=cashier)

        invoice.refresh_from_db()
        assert invoice.balance == 300
        assert invoice.status == Invoice.Status.PARTIALLY_PAID


class TestMpesaFlow:
    @pytest.mark.smoke
    def test_stk_push_creates_a_pending_payment_and_marks_the_invoice_pending_confirmation(self):
        invoice = InvoiceFactory()
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
        )

        mpesa_transaction = initiate_mpesa_stk_push(
            invoice, phone_number="254712345678", amount=500
        )

        invoice.refresh_from_db()
        assert invoice.status == Invoice.Status.PENDING_CONFIRMATION
        assert mpesa_transaction.status == MpesaTransaction.Status.REQUESTED
        assert mpesa_transaction.payment.status == Payment.Status.PENDING

    def test_successful_callback_confirms_the_payment_and_settles_the_invoice(self):
        invoice = InvoiceFactory()
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
        )
        mpesa_transaction = initiate_mpesa_stk_push(
            invoice, phone_number="254712345678", amount=500
        )

        process_mpesa_callback(
            mpesa_transaction.checkout_request_id, success=True, mpesa_receipt_number="QGH7XYZ123"
        )

        invoice.refresh_from_db()
        mpesa_transaction.refresh_from_db()
        assert invoice.status == Invoice.Status.PAID
        assert invoice.balance == 0
        assert mpesa_transaction.status == MpesaTransaction.Status.CONFIRMED
        assert mpesa_transaction.mpesa_receipt_number == "QGH7XYZ123"

    def test_failed_callback_marks_the_payment_failed_without_settling(self):
        invoice = InvoiceFactory()
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
        )
        mpesa_transaction = initiate_mpesa_stk_push(
            invoice, phone_number="254712345678", amount=500
        )

        process_mpesa_callback(mpesa_transaction.checkout_request_id, success=False)

        mpesa_transaction.refresh_from_db()
        invoice.refresh_from_db()
        assert mpesa_transaction.status == MpesaTransaction.Status.FAILED
        assert mpesa_transaction.payment.status == Payment.Status.FAILED
        assert invoice.balance == 500

    def test_a_retried_callback_is_idempotent(self):
        invoice = InvoiceFactory()
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
        )
        mpesa_transaction = initiate_mpesa_stk_push(
            invoice, phone_number="254712345678", amount=500
        )

        process_mpesa_callback(
            mpesa_transaction.checkout_request_id, success=True, mpesa_receipt_number="QGH7XYZ123"
        )
        # A retried callback with different (or malicious) data must be a no-op.
        process_mpesa_callback(
            mpesa_transaction.checkout_request_id, success=False, mpesa_receipt_number="BOGUS"
        )

        mpesa_transaction.refresh_from_db()
        assert mpesa_transaction.status == MpesaTransaction.Status.CONFIRMED
        assert mpesa_transaction.mpesa_receipt_number == "QGH7XYZ123"


class TestApproveRefund:
    @pytest.mark.smoke
    def test_approving_a_refund_by_a_different_user_succeeds(self):
        invoice = InvoiceFactory()
        cashier = UserFactory(facility=invoice.facility)
        accountant = UserFactory(facility=invoice.facility)
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
        )
        payment = record_payment(
            invoice, method=Payment.Method.CASH, amount=500, received_by=cashier
        )

        refund = approve_refund(
            invoice, payment, amount=200, reason="Overcharged", approved_by=accountant
        )

        assert refund.approved_by_id == accountant.id
        payment.refresh_from_db()
        assert payment.status == Payment.Status.REFUNDED

    def test_the_cashier_cannot_approve_their_own_refund(self):
        invoice = InvoiceFactory()
        cashier = UserFactory(facility=invoice.facility)
        payment = PaymentFactory(invoice=invoice, received_by=cashier)

        with pytest.raises(SameCashierRefundError):
            approve_refund(invoice, payment, amount=100, reason="x", approved_by=cashier)

    def test_cannot_refund_more_than_was_paid(self):
        invoice = InvoiceFactory()
        cashier = UserFactory(facility=invoice.facility)
        accountant = UserFactory(facility=invoice.facility)
        payment = PaymentFactory(invoice=invoice, amount=100, received_by=cashier)

        with pytest.raises(RefundExceedsPaymentError):
            approve_refund(invoice, payment, amount=200, reason="x", approved_by=accountant)
