import pytest

from apps.laboratory.factories import (
    LabOrderFactory,
    LabOrderItemFactory,
    LabResultFactory,
    LabResultValueFactory,
    LabSampleFactory,
)
from apps.laboratory.models import LabOrder

pytestmark = pytest.mark.django_db


class TestLabOrder:
    def test_defaults_to_pending_and_routine(self):
        order = LabOrderFactory()
        assert order.status == LabOrder.Status.PENDING
        assert order.priority == LabOrder.Priority.ROUTINE

    def test_hard_delete_is_disabled(self):
        order = LabOrderFactory()
        with pytest.raises(NotImplementedError):
            order.delete()


class TestLabOrderItem:
    def test_audit_facility_resolves_through_lab_order(self):
        from apps.audit.models import AuditLogEntry

        item = LabOrderItemFactory()
        entry = AuditLogEntry.objects.get(record_id=item.pk, action=AuditLogEntry.Action.CREATE)
        assert entry.facility_id == item.lab_order.facility_id


class TestLabSample:
    def test_defaults_to_collected(self):
        sample = LabSampleFactory()
        assert sample.status == "collected"

    def test_one_sample_per_order_item(self):
        from django.db import IntegrityError, transaction

        item = LabOrderItemFactory()
        LabSampleFactory(lab_order_item=item)
        with pytest.raises(IntegrityError), transaction.atomic():
            LabSampleFactory(lab_order_item=item)

    def test_audit_facility_resolves_through_order_item(self):
        from apps.audit.models import AuditLogEntry

        sample = LabSampleFactory()
        entry = AuditLogEntry.objects.get(record_id=sample.pk, action=AuditLogEntry.Action.CREATE)
        assert entry.facility_id == sample.lab_order_item.lab_order.facility_id


class TestLabResult:
    def test_defaults_to_entered_and_not_critical(self):
        result = LabResultFactory()
        assert result.status == "entered"
        assert result.is_critical is False

    def test_one_result_per_order_item(self):
        from django.db import IntegrityError, transaction

        item = LabOrderItemFactory()
        LabResultFactory(lab_order_item=item)
        with pytest.raises(IntegrityError), transaction.atomic():
            LabResultFactory(lab_order_item=item)


class TestLabResultValue:
    def test_defaults_to_normal_flag(self):
        value = LabResultValueFactory()
        assert value.flag == "normal"

    def test_audit_facility_resolves_through_result_chain(self):
        from apps.audit.models import AuditLogEntry

        value = LabResultValueFactory()
        entry = AuditLogEntry.objects.get(record_id=value.pk, action=AuditLogEntry.Action.CREATE)
        assert entry.facility_id == value.lab_result.lab_order_item.lab_order.facility_id
