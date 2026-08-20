import datetime

import pytest

from apps.accounts.factories import UserFactory
from apps.audit.models import AuditLogEntry
from apps.core.factories import FacilityFactory
from apps.patients.services import register_patient

pytestmark = pytest.mark.django_db


class TestRegisterPatient:
    @pytest.mark.smoke
    def test_generates_an_mrn_in_the_expected_format(self):
        facility = FacilityFactory(code="NBI01")
        patient = register_patient(facility=facility, first_name="Jane", last_name="Mwangi")

        year = datetime.date.today().year
        assert patient.mrn == f"NBI01-{year}-000001"

    def test_sequence_increments_within_the_same_facility_and_year(self):
        facility = FacilityFactory(code="NBI01")
        first = register_patient(facility=facility, first_name="A", last_name="One")
        second = register_patient(facility=facility, first_name="B", last_name="Two")

        assert first.mrn.endswith("-000001")
        assert second.mrn.endswith("-000002")

    def test_sequence_is_independent_per_facility(self):
        facility_a = FacilityFactory(code="NBI01")
        facility_b = FacilityFactory(code="MSA02")

        patient_a = register_patient(facility=facility_a, first_name="A", last_name="One")
        patient_b = register_patient(facility=facility_b, first_name="B", last_name="Two")

        assert patient_a.mrn.startswith("NBI01-")
        assert patient_b.mrn.startswith("MSA02-")
        assert patient_b.mrn.endswith("-000001")

    def test_client_supplied_mrn_is_ignored(self):
        facility = FacilityFactory(code="NBI01")
        patient = register_patient(
            facility=facility, first_name="A", last_name="One", mrn="HACKED-000000"
        )
        assert patient.mrn != "HACKED-000000"

    def test_registration_writes_an_audit_entry_with_the_actor(self):
        facility = FacilityFactory(code="NBI01")
        actor = UserFactory()
        patient = register_patient(facility=facility, actor=actor, first_name="A", last_name="One")

        entry = AuditLogEntry.objects.get(record_id=patient.pk, action=AuditLogEntry.Action.CREATE)
        assert entry.actor_id == actor.id
