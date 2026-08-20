"""
Patient Management (BRD §6.1; Data Dictionary §3) — the longitudinal patient
record every other module reads from and writes back into.
"""

from django.db import models

from apps.core.mixins import AuditableModel
from apps.core.models import FacilityScopedModel, UUIDModel


class Patient(FacilityScopedModel, AuditableModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        UNSPECIFIED = "unspecified", "Unspecified"

    mrn = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="System-generated at registration, never client-supplied.",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(
        null=True, blank=True, help_text="Nullable for provisional/unidentified registration."
    )
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True)
    national_id = models.CharField(
        max_length=30,
        blank=True,
        help_text="Unverified text unless a government API integration is confirmed (TRD §10).",
    )
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    photo_url = models.CharField(max_length=500, blank=True, help_text="Object storage reference.")
    blood_group = models.CharField(max_length=5, blank=True)
    is_provisional = models.BooleanField(
        default=False, help_text="True for unidentified/emergency quick-registration."
    )
    merged_into_patient = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="merged_duplicates",
        help_text="Set when this record is merged as a duplicate.",
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["facility", "mrn"]),
            models.Index(fields=["last_name", "first_name"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.mrn})"

    @property
    def is_merged(self) -> bool:
        return self.merged_into_patient_id is not None


class PatientChildModel(UUIDModel, AuditableModel):
    """
    Shared base for the patient's related entities (Guardian,
    EmergencyContact, Allergy, ChronicCondition, Consent, PatientInsurance —
    Data Dictionary §3). None of these carry their own facility_id in the
    Data Dictionary — they're scoped through `patient` — so
    `_get_audit_facility_id()` resolves it that way instead of denormalizing
    a facility column the schema doesn't define.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def _get_audit_facility_id(self):
        return self.patient.facility_id


class Guardian(PatientChildModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="guardians")
    name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    access_revoked_at = models.DateTimeField(
        null=True, blank=True, help_text="Supports per-guardian revocation (BRD §6.1 edge case)."
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.relationship} of {self.patient})"


class EmergencyContact(PatientChildModel):
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="emergency_contacts"
    )
    name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=20)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.patient})"


class Allergy(PatientChildModel):
    class Severity(models.TextChoices):
        MILD = "mild", "Mild"
        MODERATE = "moderate", "Moderate"
        SEVERE = "severe", "Severe"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="allergies")
    substance = models.CharField(max_length=150, help_text="e.g. Penicillin, Peanuts")
    reaction = models.CharField(max_length=255, blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, blank=True)

    class Meta:
        ordering = ["substance"]
        verbose_name_plural = "allergies"

    def __str__(self):
        return f"{self.substance} ({self.patient})"


class ChronicCondition(PatientChildModel):
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="chronic_conditions"
    )
    condition = models.CharField(max_length=150, help_text="e.g. Hypertension, Diabetes Type 2")
    diagnosed_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["condition"]

    def __str__(self):
        return f"{self.condition} ({self.patient})"


class Consent(PatientChildModel):
    class ConsentType(models.TextChoices):
        DATA_USE = "data_use", "Data use"
        TREATMENT = "treatment", "Treatment"
        PORTAL_RELEASE = "portal_release", "Portal release"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="consents")
    type = models.CharField(max_length=20, choices=ConsentType.choices)
    granted_at = models.DateTimeField()
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Revocation must never block emergency care (BRD §6.1 edge case) — "
            "enforced by whatever module checks consent, not here."
        ),
    )

    class Meta:
        ordering = ["-granted_at"]

    def __str__(self):
        return f"{self.get_type_display()} — {self.patient}"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


class PatientInsurance(PatientChildModel):
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="insurance_policies"
    )
    insurer_name = models.CharField(max_length=150)
    policy_number = models.CharField(max_length=50)
    member_number = models.CharField(max_length=50, blank=True)
    is_primary = models.BooleanField(
        default=True, help_text="Supports coordination-of-benefits (BRD §6.10 edge case)."
    )

    class Meta:
        ordering = ["-is_primary", "insurer_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient"],
                condition=models.Q(is_primary=True),
                name="unique_primary_insurance_per_patient",
            )
        ]

    def __str__(self):
        return f"{self.insurer_name} ({self.patient})"
