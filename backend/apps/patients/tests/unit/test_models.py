import pytest
from django.db import IntegrityError, transaction

from apps.patients.factories import PatientFactory

pytestmark = pytest.mark.django_db


class TestPatient:
    def test_mrn_must_be_unique(self):
        PatientFactory(mrn="DUPMRN")
        with pytest.raises(IntegrityError), transaction.atomic():
            PatientFactory(mrn="DUPMRN")

    def test_str_includes_name_and_mrn(self):
        patient = PatientFactory(first_name="Jane", last_name="Mwangi", mrn="NBI01-2026-000001")
        assert str(patient) == "Jane Mwangi (NBI01-2026-000001)"

    def test_is_provisional_defaults_false(self):
        patient = PatientFactory()
        assert patient.is_provisional is False

    def test_date_of_birth_can_be_null_for_provisional_registration(self):
        patient = PatientFactory(is_provisional=True, date_of_birth=None)
        assert patient.date_of_birth is None

    def test_is_merged_false_by_default(self):
        patient = PatientFactory()
        assert patient.is_merged is False

    def test_is_merged_true_once_merged_into_another_patient(self):
        canonical = PatientFactory()
        duplicate = PatientFactory(merged_into_patient=canonical)
        assert duplicate.is_merged is True

    def test_hard_delete_is_disabled(self):
        """Patient is audited (TRD §8.4) — delete() must never run."""
        patient = PatientFactory()
        with pytest.raises(NotImplementedError):
            patient.delete()

    def test_soft_delete_sets_deleted_at(self):
        patient = PatientFactory()
        patient.soft_delete()
        patient.refresh_from_db()
        assert patient.deleted_at is not None
