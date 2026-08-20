import pytest

from apps.billing.factories import (
    InvoiceFactory,
    InvoiceLineItemFactory,
    MpesaTransactionFactory,
    PaymentFactory,
    RefundFactory,
)
from apps.billing.models import Invoice

pytestmark = pytest.mark.django_db


class TestInvoice:
    def test_defaults_to_open(self):
        invoice = InvoiceFactory()
        assert invoice.status == Invoice.Status.OPEN

    def test_hard_delete_is_disabled(self):
        invoice = InvoiceFactory()
        with pytest.raises(NotImplementedError):
            invoice.delete()

    def test_invoice_number_is_unique(self):
        from django.db import IntegrityError, transaction

        invoice = InvoiceFactory()
        with pytest.raises(IntegrityError), transaction.atomic():
            InvoiceFactory(invoice_number=invoice.invoice_number)


class TestInvoiceLineItem:
    def test_audit_facility_resolves_through_invoice(self):
        from apps.audit.models import AuditLogEntry

        item = InvoiceLineItemFactory()
        entry = AuditLogEntry.objects.get(record_id=item.pk, action=AuditLogEntry.Action.CREATE)
        assert entry.facility_id == item.invoice.facility_id


class TestPayment:
    def test_audit_facility_resolves_through_invoice(self):
        from apps.audit.models import AuditLogEntry

        payment = PaymentFactory()
        entry = AuditLogEntry.objects.get(record_id=payment.pk, action=AuditLogEntry.Action.CREATE)
        assert entry.facility_id == payment.invoice.facility_id


class TestMpesaTransaction:
    def test_one_transaction_per_payment(self):
        from django.db import IntegrityError, transaction

        payment = PaymentFactory()
        MpesaTransactionFactory(payment=payment)
        with pytest.raises(IntegrityError), transaction.atomic():
            MpesaTransactionFactory(payment=payment)

    def test_audit_facility_resolves_through_payment_invoice(self):
        from apps.audit.models import AuditLogEntry

        transaction_ = MpesaTransactionFactory()
        entry = AuditLogEntry.objects.get(
            record_id=transaction_.pk, action=AuditLogEntry.Action.CREATE
        )
        assert entry.facility_id == transaction_.payment.invoice.facility_id


class TestRefund:
    def test_audit_facility_resolves_through_invoice(self):
        from apps.audit.models import AuditLogEntry

        refund = RefundFactory()
        entry = AuditLogEntry.objects.get(record_id=refund.pk, action=AuditLogEntry.Action.CREATE)
        assert entry.facility_id == refund.invoice.facility_id
