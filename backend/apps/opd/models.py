"""
OPD / Clinical Management (BRD §6.3; Data Dictionary §5) — the consultation
record and the point where Lab, Radiology, and Pharmacy orders originate
(Solution Spec Flow 5.3).

Scope notes worth flagging:
- Visit and Consultation are audited (AuditableModel): they're the actual
  clinical encounter and its record, same tier as Patient/Appointment.
- Vitals, Diagnosis, and ConsultationAddendum are audited too, per the
  blanket "no clinical write is un-audited" rule — but none of them expose
  an update/destroy endpoint (apps.opd.views): a vitals reading, a
  diagnosis line, and an addendum are all point-in-time clinical facts you
  correct by adding a new one, not by silently editing history. None of
  these four carry their own `facility` column (Data Dictionary §5 doesn't
  define one for them), so each resolves it through Visit via
  `_get_audit_facility_id()`, same pattern as the Patient child models.
- Consultation's `locked_at`/`is_draft` pair implements the BRD §6.3 edge
  case directly: a signed note is never edited, only addended
  (apps.opd.services enforces this — the model layer alone can't).
"""

from django.conf import settings
from django.db import models

from apps.core.mixins import AuditableModel
from apps.core.models import Department, FacilityScopedModel, UUIDModel
from apps.patients.models import Patient


class Visit(FacilityScopedModel, AuditableModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="visits")
    appointment = models.ForeignKey(
        "appointments.Appointment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="visits",
        help_text="Null for walk-in/emergency visits.",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="opd_visits"
    )
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="visits")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    checked_in_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-checked_in_at"]
        indexes = [models.Index(fields=["doctor", "status"])]

    def __str__(self):
        return f"{self.patient} — visit {self.checked_in_at:%Y-%m-%d %H:%M}"


class Vitals(UUIDModel, AuditableModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="vitals")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    bp_systolic = models.SmallIntegerField(null=True, blank=True)
    bp_diastolic = models.SmallIntegerField(null=True, blank=True)
    pulse = models.SmallIntegerField(null=True, blank=True)
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    respiration_rate = models.SmallIntegerField(null=True, blank=True)
    spo2_percent = models.SmallIntegerField(null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    recorded_at = models.DateTimeField()

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name_plural = "vitals"

    def __str__(self):
        return f"Vitals for {self.visit} @ {self.recorded_at:%Y-%m-%d %H:%M}"

    def _get_audit_facility_id(self):
        return self.visit.facility_id


class Consultation(UUIDModel, AuditableModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name="consultation")
    chief_complaint = models.TextField(blank=True)
    history_of_present_illness = models.TextField(blank=True)
    examination_notes = models.TextField(blank=True)
    is_draft = models.BooleanField(default=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Consultation for {self.visit}"

    def _get_audit_facility_id(self):
        return self.visit.facility_id


class Diagnosis(UUIDModel, AuditableModel):
    class Type(models.TextChoices):
        PRIMARY = "primary", "Primary"
        SECONDARY = "secondary", "Secondary"
        DIFFERENTIAL = "differential", "Differential"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    consultation = models.ForeignKey(
        Consultation, on_delete=models.CASCADE, related_name="diagnoses"
    )
    icd_code = models.CharField(max_length=10, blank=True)
    description = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=Type.choices)

    class Meta:
        verbose_name_plural = "diagnoses"

    def __str__(self):
        return f"{self.icd_code or '—'} {self.description} ({self.type})"

    def _get_audit_facility_id(self):
        return self.consultation.visit.facility_id


class ConsultationAddendum(UUIDModel, AuditableModel):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="addenda")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Addendum on {self.consultation} by {self.author}"

    def _get_audit_facility_id(self):
        return self.consultation.visit.facility_id
