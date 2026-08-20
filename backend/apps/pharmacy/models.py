"""
Pharmacy Management (BRD §6.8; Data Dictionary §7) — prescribing, stock,
and dispensing, with batch-level traceability for recalls.

Drug is deliberately NOT an AuditableModel and NOT facility-scoped: the
Data Dictionary defines no facility_id for it (unlike every other model
in this app), and AuditLogEntry.facility is a required FK — there's no
"which facility's audit log" for a shared drug catalog entry to belong
to. It's global reference data, same category as an ICD code list, not a
per-facility clinical/financial record. StockBatch is where the real
per-facility, audited state lives (quantity on hand, batch traceability).

Prescription, PrescriptionItem, and DispenseRecord don't carry their own
facility column either (Data Dictionary §7 doesn't define one for them),
so each resolves it through Consultation -> Visit -> Facility, same
pattern as OPD's own child models.
"""

from django.conf import settings
from django.db import models

from apps.core.mixins import AuditableModel
from apps.core.models import FacilityScopedModel, UUIDModel
from apps.opd.models import Consultation
from apps.patients.models import Patient


class Drug(UUIDModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=150)
    generic_name = models.CharField(max_length=150, blank=True)
    form = models.CharField(max_length=50, blank=True, help_text="tablet | syrup | injection | ...")
    strength = models.CharField(max_length=30, blank=True, help_text="e.g. 500mg")
    is_controlled = models.BooleanField(
        default=False, help_text="Gates Pharmacy Technician access, BRD §6.8."
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} {self.strength}".strip()


class Prescription(UUIDModel, AuditableModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PARTIALLY_DISPENSED = "partially_dispensed", "Partially Dispensed"
        DISPENSED = "dispensed", "Dispensed"
        CANCELLED = "cancelled", "Cancelled"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    consultation = models.ForeignKey(
        Consultation, on_delete=models.PROTECT, related_name="prescriptions"
    )
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="prescriptions")
    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Prescription for {self.patient} ({self.status})"

    def _get_audit_facility_id(self):
        return self.consultation.visit.facility_id


class PrescriptionItem(UUIDModel, AuditableModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="items")
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT, related_name="+")
    dosage = models.CharField(max_length=50)
    frequency = models.CharField(max_length=50)
    duration_days = models.SmallIntegerField(null=True, blank=True)
    qty_prescribed = models.IntegerField()

    def __str__(self):
        return f"{self.drug} x{self.qty_prescribed}"

    def _get_audit_facility_id(self):
        return self.prescription.consultation.visit.facility_id


class StockBatch(FacilityScopedModel, AuditableModel):
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT, related_name="batches")
    batch_number = models.CharField(max_length=50)
    expiry_date = models.DateField()
    quantity_on_hand = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["expiry_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_on_hand__gte=0),
                name="stock_batch_quantity_not_negative",
            )
        ]

    def __str__(self):
        return f"{self.drug} batch {self.batch_number} ({self.quantity_on_hand} on hand)"


class DispenseRecord(UUIDModel, AuditableModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    prescription_item = models.ForeignKey(
        PrescriptionItem, on_delete=models.PROTECT, related_name="dispense_records"
    )
    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="+")
    dispensed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    qty_dispensed = models.IntegerField()
    dispensed_at = models.DateTimeField()

    class Meta:
        ordering = ["-dispensed_at"]

    def __str__(self):
        return f"Dispensed {self.qty_dispensed} of {self.batch.drug} to {self.prescription_item}"

    def _get_audit_facility_id(self):
        return self.prescription_item.prescription.consultation.visit.facility_id
