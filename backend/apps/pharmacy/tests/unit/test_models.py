import pytest
from django.db import IntegrityError, transaction

from apps.pharmacy.factories import (
    DispenseRecordFactory,
    DrugFactory,
    PrescriptionFactory,
    PrescriptionItemFactory,
    StockBatchFactory,
)
from apps.pharmacy.models import Prescription

pytestmark = pytest.mark.django_db


class TestDrug:
    def test_defaults_to_not_controlled(self):
        drug = DrugFactory()
        assert drug.is_controlled is False

    def test_str_includes_strength(self):
        drug = DrugFactory(name="Paracetamol", strength="500mg")
        assert "Paracetamol" in str(drug)
        assert "500mg" in str(drug)


class TestStockBatch:
    def test_hard_delete_is_disabled(self):
        batch = StockBatchFactory()
        with pytest.raises(NotImplementedError):
            batch.delete()

    def test_quantity_cannot_go_negative(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            StockBatchFactory(quantity_on_hand=-1)


class TestPrescription:
    def test_defaults_to_pending(self):
        prescription = PrescriptionFactory()
        assert prescription.status == Prescription.Status.PENDING

    def test_audit_facility_resolves_through_consultation_visit(self):
        from apps.audit.models import AuditLogEntry

        prescription = PrescriptionFactory()
        entry = AuditLogEntry.objects.get(
            record_id=prescription.pk, action=AuditLogEntry.Action.CREATE
        )
        assert entry.facility_id == prescription.consultation.visit.facility_id


class TestPrescriptionItem:
    def test_audit_facility_resolves_through_prescription_chain(self):
        from apps.audit.models import AuditLogEntry

        item = PrescriptionItemFactory()
        entry = AuditLogEntry.objects.get(record_id=item.pk, action=AuditLogEntry.Action.CREATE)
        assert entry.facility_id == item.prescription.consultation.visit.facility_id


class TestDispenseRecord:
    def test_audit_facility_resolves_through_the_full_chain(self):
        from apps.audit.models import AuditLogEntry

        record = DispenseRecordFactory()
        entry = AuditLogEntry.objects.get(record_id=record.pk, action=AuditLogEntry.Action.CREATE)
        expected = record.prescription_item.prescription.consultation.visit.facility_id
        assert entry.facility_id == expected
