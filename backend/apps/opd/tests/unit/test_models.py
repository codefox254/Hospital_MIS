import pytest

from apps.opd.factories import (
    ConsultationAddendumFactory,
    ConsultationFactory,
    DiagnosisFactory,
    VisitFactory,
    VitalsFactory,
)
from apps.opd.models import Diagnosis, Visit

pytestmark = pytest.mark.django_db


class TestVisit:
    def test_defaults_to_in_progress(self):
        visit = VisitFactory()
        assert visit.status == Visit.Status.IN_PROGRESS

    def test_hard_delete_is_disabled(self):
        visit = VisitFactory()
        with pytest.raises(NotImplementedError):
            visit.delete()

    def test_appointment_is_nullable_for_walk_ins(self):
        visit = VisitFactory(appointment=None)
        assert visit.appointment_id is None


class TestVitals:
    def test_hard_delete_is_disabled(self):
        vitals = VitalsFactory()
        with pytest.raises(NotImplementedError):
            vitals.delete()

    def test_audit_facility_resolves_through_visit(self):
        from apps.audit.models import AuditLogEntry

        vitals = VitalsFactory()
        entry = AuditLogEntry.objects.get(record_id=vitals.pk, action=AuditLogEntry.Action.CREATE)
        assert entry.facility_id == vitals.visit.facility_id


class TestConsultation:
    def test_defaults_to_draft_and_unlocked(self):
        consultation = ConsultationFactory()
        assert consultation.is_draft is True
        assert consultation.locked_at is None

    def test_one_consultation_per_visit(self):
        from django.db import IntegrityError, transaction

        visit = VisitFactory()
        ConsultationFactory(visit=visit)
        with pytest.raises(IntegrityError), transaction.atomic():
            ConsultationFactory(visit=visit)

    def test_audit_facility_resolves_through_visit(self):
        from apps.audit.models import AuditLogEntry

        consultation = ConsultationFactory()
        entry = AuditLogEntry.objects.get(
            record_id=consultation.pk, action=AuditLogEntry.Action.CREATE
        )
        assert entry.facility_id == consultation.visit.facility_id


class TestDiagnosis:
    def test_type_choices(self):
        diagnosis = DiagnosisFactory(type=Diagnosis.Type.SECONDARY)
        assert diagnosis.type == "secondary"

    def test_audit_facility_resolves_through_consultation_visit(self):
        from apps.audit.models import AuditLogEntry

        diagnosis = DiagnosisFactory()
        entry = AuditLogEntry.objects.get(
            record_id=diagnosis.pk, action=AuditLogEntry.Action.CREATE
        )
        assert entry.facility_id == diagnosis.consultation.visit.facility_id


class TestConsultationAddendum:
    def test_str_includes_author(self):
        addendum = ConsultationAddendumFactory()
        assert str(addendum.author) in str(addendum)

    def test_audit_facility_resolves_through_consultation_visit(self):
        from apps.audit.models import AuditLogEntry

        addendum = ConsultationAddendumFactory()
        entry = AuditLogEntry.objects.get(record_id=addendum.pk, action=AuditLogEntry.Action.CREATE)
        assert entry.facility_id == addendum.consultation.visit.facility_id
