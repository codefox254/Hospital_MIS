"""
Patient Management (BRD §6.1; Data Dictionary §3) — the longitudinal patient
record every other module reads from and writes back into. This PR covers
`Patient` itself; the related entities (Guardian, EmergencyContact, Allergy,
ChronicCondition, Consent, PatientInsurance) land in a follow-up PR.
"""

from django.db import models

from apps.core.mixins import AuditableModel
from apps.core.models import FacilityScopedModel


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
