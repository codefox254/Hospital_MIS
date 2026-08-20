"""
Billing & Revenue Management (BRD §6.9; Data Dictionary §8) — every module
above generates InvoiceLineItem records here; this module never accepts a
hand-entered charge (apps.billing.views deliberately exposes no
create/update endpoint for InvoiceLineItem — apps.billing.services.
add_line_item() is the only way one gets created).

InvoiceLineItem, Payment, MpesaTransaction, and Refund don't carry their
own facility column (Data Dictionary §8 doesn't define one for them), so
each resolves it through Invoice via `_get_audit_facility_id()`, same
pattern used throughout this codebase.
"""

from django.conf import settings
from django.db import models

from apps.core.mixins import AuditableModel
from apps.core.models import FacilityScopedModel, UUIDModel
from apps.patients.models import Patient


class Invoice(FacilityScopedModel, AuditableModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PENDING_CONFIRMATION = "pending_confirmation", "Pending Confirmation"
        PAID = "paid", "Paid"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"
        WRITTEN_OFF = "written_off", "Written Off"

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="invoices")
    visit = models.ForeignKey(
        "opd.Visit", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices"
    )
    invoice_number = models.CharField(max_length=30, unique=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.OPEN)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.invoice_number} ({self.status})"


class InvoiceLineItem(UUIDModel, AuditableModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    source_module = models.CharField(
        max_length=30, help_text="opd | laboratory | pharmacy | inpatient | ..."
    )
    source_reference_id = models.UUIDField(help_text="Points back to the originating record.")
    description = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Locked at time of service — never repriced."
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.description} x{self.quantity} = {self.amount}"

    def _get_audit_facility_id(self):
        return self.invoice.facility_id


class Payment(UUIDModel, AuditableModel):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        MPESA = "mpesa", "M-Pesa"
        CARD = "card", "Card"
        BANK = "bank", "Bank"
        INSURANCE = "insurance", "Insurance"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    method = models.CharField(max_length=20, choices=Method.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Cashier — null for patient-initiated mobile payments.",
    )
    received_at = models.DateTimeField()

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.method} {self.amount} for {self.invoice} ({self.status})"

    def _get_audit_facility_id(self):
        return self.invoice.facility_id


class MpesaTransaction(UUIDModel, AuditableModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        CONFIRMED = "confirmed", "Confirmed"
        FAILED = "failed", "Failed"

    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, related_name="mpesa_transaction"
    )
    checkout_request_id = models.CharField(
        max_length=100, unique=True, help_text="Idempotency key for the STK Push request."
    )
    mpesa_receipt_number = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    callback_payload = models.JSONField(null=True, blank=True, help_text="Raw Daraja callback.")

    def __str__(self):
        return f"M-Pesa {self.checkout_request_id} ({self.status})"

    def _get_audit_facility_id(self):
        return self.payment.invoice.facility_id


class Refund(UUIDModel, AuditableModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="refunds")
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Accountant — never the cashier who took the payment, BRD §6.9.",
    )
    approved_at = models.DateTimeField()

    class Meta:
        ordering = ["-approved_at"]

    def __str__(self):
        return f"Refund {self.amount} on {self.invoice}"

    def _get_audit_facility_id(self):
        return self.invoice.facility_id
