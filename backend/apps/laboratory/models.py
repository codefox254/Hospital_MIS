"""
Laboratory Information System (BRD §6.6; Data Dictionary §6) — order to
verified result, with the technician/scientist separation of duties
enforced at the service layer (apps.laboratory.services.verify_result):
distinct entered_by/verified_by, and a technician can never verify their
own entry.

LabOrder is audited (AuditableModel, has its own facility). LabOrderItem,
LabSample, LabResult, and LabResultValue don't carry their own facility
column (Data Dictionary §6 doesn't define one for them), so each resolves
it through LabOrder via `_get_audit_facility_id()`, same pattern as OPD's
child models. None of the four expose an update endpoint either — a
sample collection, a result entry, and a result value are point-in-time
facts superseded by a new state transition (collected → rejected/received,
entered → verified), not edited in place.
"""

from django.conf import settings
from django.db import models

from apps.core.mixins import AuditableModel
from apps.core.models import FacilityScopedModel, UUIDModel
from apps.opd.models import Visit


class LabOrder(FacilityScopedModel, AuditableModel):
    class Priority(models.TextChoices):
        ROUTINE = "routine", "Routine"
        STAT = "stat", "Stat"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COLLECTED = "collected", "Collected"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"

    visit = models.ForeignKey(Visit, on_delete=models.PROTECT, related_name="lab_orders")
    ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.ROUTINE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    ordered_at = models.DateTimeField()

    class Meta:
        ordering = ["-ordered_at"]

    def __str__(self):
        return f"LabOrder for {self.visit} ({self.status})"


class LabOrderItem(UUIDModel, AuditableModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    lab_order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name="items")
    test_code = models.CharField(max_length=20)
    test_name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.test_code} — {self.test_name}"

    def _get_audit_facility_id(self):
        return self.lab_order.facility_id


class LabSample(UUIDModel, AuditableModel):
    class Status(models.TextChoices):
        COLLECTED = "collected", "Collected"
        REJECTED = "rejected", "Rejected"
        RECEIVED = "received", "Received"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    lab_order_item = models.OneToOneField(
        LabOrderItem, on_delete=models.CASCADE, related_name="sample"
    )
    barcode = models.CharField(max_length=50, unique=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    collected_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COLLECTED)
    rejection_reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Sample {self.barcode} ({self.status})"

    def _get_audit_facility_id(self):
        return self.lab_order_item.lab_order.facility_id


class LabResult(UUIDModel, AuditableModel):
    class Status(models.TextChoices):
        ENTERED = "entered", "Entered"
        VERIFIED = "verified", "Verified"
        AMENDED = "amended", "Amended"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    lab_order_item = models.OneToOneField(
        LabOrderItem, on_delete=models.CASCADE, related_name="result"
    )
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    entered_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ENTERED)
    is_critical = models.BooleanField(default=False)
    released_to_portal_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Result for {self.lab_order_item} ({self.status})"

    def _get_audit_facility_id(self):
        return self.lab_order_item.lab_order.facility_id


class LabResultValue(UUIDModel, AuditableModel):
    class Flag(models.TextChoices):
        NORMAL = "normal", "Normal"
        LOW = "low", "Low"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    lab_result = models.ForeignKey(LabResult, on_delete=models.CASCADE, related_name="values")
    parameter = models.CharField(max_length=50)
    value = models.CharField(max_length=30)
    unit = models.CharField(max_length=20, blank=True)
    reference_range = models.CharField(max_length=50, blank=True)
    flag = models.CharField(max_length=20, choices=Flag.choices, default=Flag.NORMAL)

    def __str__(self):
        return f"{self.parameter}: {self.value} {self.unit} ({self.flag})"

    def _get_audit_facility_id(self):
        return self.lab_result.lab_order_item.lab_order.facility_id
