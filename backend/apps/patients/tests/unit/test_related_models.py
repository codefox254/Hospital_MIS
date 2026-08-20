import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.models import AuditLogEntry
from apps.patients.factories import (
    AllergyFactory,
    ChronicConditionFactory,
    ConsentFactory,
    EmergencyContactFactory,
    GuardianFactory,
    PatientFactory,
    PatientInsuranceFactory,
)
from apps.patients.models import Allergy, Consent

pytestmark = pytest.mark.django_db


class TestGuardian:
    def test_str_includes_relationship(self):
        guardian = GuardianFactory(name="Mary Wanjiru", relationship="Mother")
        assert "Mary Wanjiru" in str(guardian)
        assert "Mother" in str(guardian)

    def test_access_revoked_at_defaults_null(self):
        guardian = GuardianFactory()
        assert guardian.access_revoked_at is None

    def test_hard_delete_is_disabled(self):
        guardian = GuardianFactory()
        with pytest.raises(NotImplementedError):
            guardian.delete()

    def test_soft_delete_writes_an_audit_entry_scoped_to_patient_facility(self):
        patient = PatientFactory()
        guardian = GuardianFactory(patient=patient)
        guardian.soft_delete()

        entry = AuditLogEntry.objects.get(
            record_id=guardian.pk, action=AuditLogEntry.Action.SOFT_DELETE
        )
        assert entry.facility_id == patient.facility_id


class TestEmergencyContact:
    def test_str_includes_patient(self):
        patient = PatientFactory(first_name="Jane", last_name="M", mrn="X-1")
        contact = EmergencyContactFactory(patient=patient, name="John Doe")
        assert "John Doe" in str(contact)


class TestAllergy:
    def test_severity_choices(self):
        assert set(Allergy.Severity.values) == {"mild", "moderate", "severe"}

    def test_hard_delete_is_disabled(self):
        allergy = AllergyFactory()
        with pytest.raises(NotImplementedError):
            allergy.delete()

    def test_create_writes_audit_entry_with_facility_from_patient(self):
        patient = PatientFactory()
        allergy = Allergy(patient=patient, substance="Penicillin", severity="severe")
        allergy.save()

        entry = AuditLogEntry.objects.get(record_id=allergy.pk, action=AuditLogEntry.Action.CREATE)
        assert entry.facility_id == patient.facility_id
        assert entry.field_diff["substance"]["new"] == "Penicillin"


class TestChronicCondition:
    def test_diagnosed_date_can_be_null(self):
        condition = ChronicConditionFactory(diagnosed_date=None)
        assert condition.diagnosed_date is None


class TestConsent:
    def test_is_active_true_when_not_revoked(self):
        consent = ConsentFactory()
        assert consent.is_active is True

    def test_is_active_false_once_revoked(self):
        consent = ConsentFactory(revoked_at=timezone.now())
        assert consent.is_active is False

    def test_consent_type_choices_match_data_dictionary(self):
        assert set(Consent.ConsentType.values) == {"data_use", "treatment", "portal_release"}


class TestPatientInsurance:
    def test_only_one_primary_policy_per_patient(self):
        patient = PatientFactory()
        PatientInsuranceFactory(patient=patient, is_primary=True)
        with pytest.raises(IntegrityError), transaction.atomic():
            PatientInsuranceFactory(patient=patient, is_primary=True)

    def test_multiple_non_primary_policies_are_allowed(self):
        patient = PatientFactory()
        PatientInsuranceFactory(patient=patient, is_primary=False)
        PatientInsuranceFactory(patient=patient, is_primary=False)  # should not raise

    def test_two_patients_can_each_have_a_primary_policy(self):
        PatientInsuranceFactory(is_primary=True)
        PatientInsuranceFactory(is_primary=True)  # different patient — should not raise
