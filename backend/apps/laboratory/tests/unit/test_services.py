from unittest.mock import patch

import pytest

from apps.accounts.factories import UserFactory
from apps.laboratory.factories import LabOrderFactory, LabOrderItemFactory
from apps.laboratory.models import LabOrder, LabResult, LabResultValue
from apps.laboratory.services import (
    AlreadyVerifiedError,
    SelfVerificationError,
    collect_sample,
    create_lab_order,
    enter_result,
    reject_sample,
    verify_result,
)
from apps.opd.factories import VisitFactory

pytestmark = pytest.mark.django_db


class TestCreateLabOrder:
    @pytest.mark.smoke
    def test_creates_an_order_with_its_items(self):
        visit = VisitFactory()

        order = create_lab_order(
            facility=visit.facility,
            visit=visit,
            ordered_by=visit.doctor,
            items=[
                {"test_code": "CBC", "test_name": "Complete Blood Count"},
                {"test_code": "FBS", "test_name": "Fasting Blood Sugar"},
            ],
        )

        assert order.status == LabOrder.Status.PENDING
        assert order.items.count() == 2


class TestCollectSample:
    @pytest.mark.smoke
    def test_collects_a_sample_against_an_order_item(self):
        item = LabOrderItemFactory()
        technician = UserFactory(facility=item.lab_order.facility)

        sample = collect_sample(item, collected_by=technician, barcode="BC001")

        assert sample.lab_order_item_id == item.id

    def test_order_moves_to_collected_once_every_item_has_a_sample(self):
        order = LabOrderFactory()
        item_one = LabOrderItemFactory(lab_order=order)
        item_two = LabOrderItemFactory(lab_order=order)
        technician = UserFactory(facility=order.facility)

        collect_sample(item_one, collected_by=technician, barcode="BC001")
        order.refresh_from_db()
        assert order.status == LabOrder.Status.PENDING

        collect_sample(item_two, collected_by=technician, barcode="BC002")
        order.refresh_from_db()
        assert order.status == LabOrder.Status.COLLECTED

    def test_reject_sample_records_the_reason(self):
        item = LabOrderItemFactory()
        technician = UserFactory(facility=item.lab_order.facility)
        sample = collect_sample(item, collected_by=technician, barcode="BC001")

        reject_sample(sample, reason="Hemolyzed")

        sample.refresh_from_db()
        assert sample.status == "rejected"
        assert sample.rejection_reason == "Hemolyzed"


class TestEnterAndVerifyResult:
    @pytest.mark.smoke
    def test_enters_a_result_with_its_values(self):
        item = LabOrderItemFactory()
        technician = UserFactory(facility=item.lab_order.facility)

        result = enter_result(
            item,
            entered_by=technician,
            values=[{"parameter": "WBC", "value": "7.2", "unit": "x10^9/L", "flag": "normal"}],
        )

        assert result.status == "entered"
        assert result.values.count() == 1

    def test_order_moves_to_processing_once_a_result_is_entered(self):
        item = LabOrderItemFactory()
        technician = UserFactory(facility=item.lab_order.facility)

        enter_result(item, entered_by=technician, values=[{"parameter": "WBC", "value": "7.2"}])

        item.lab_order.refresh_from_db()
        assert item.lab_order.status == LabOrder.Status.PROCESSING

    def test_a_critical_value_marks_the_result_critical_and_notifies(self):
        item = LabOrderItemFactory()
        technician = UserFactory(facility=item.lab_order.facility)

        with patch("apps.laboratory.tasks.notify_critical_result.delay") as mock_delay:
            result = enter_result(
                item,
                entered_by=technician,
                values=[{"parameter": "K+", "value": "7.5", "flag": LabResultValue.Flag.CRITICAL}],
            )

        assert result.is_critical is True
        # Notification only fires on verify (§6.6: released once verified), not on entry.
        mock_delay.assert_not_called()

    @pytest.mark.smoke
    def test_verify_result_by_a_different_user_succeeds(self):
        item = LabOrderItemFactory()
        technician = UserFactory(facility=item.lab_order.facility)
        scientist = UserFactory(facility=item.lab_order.facility)
        result = enter_result(
            item, entered_by=technician, values=[{"parameter": "WBC", "value": "7.2"}]
        )

        verify_result(result, verified_by=scientist)

        result.refresh_from_db()
        assert result.status == LabResult.Status.VERIFIED
        assert result.verified_by_id == scientist.id
        assert result.released_to_portal_at is not None

    def test_technician_cannot_verify_their_own_entry(self):
        item = LabOrderItemFactory()
        technician = UserFactory(facility=item.lab_order.facility)
        result = enter_result(
            item, entered_by=technician, values=[{"parameter": "WBC", "value": "7.2"}]
        )

        with pytest.raises(SelfVerificationError):
            verify_result(result, verified_by=technician)

    def test_cannot_verify_an_already_verified_result(self):
        item = LabOrderItemFactory()
        technician = UserFactory(facility=item.lab_order.facility)
        scientist = UserFactory(facility=item.lab_order.facility)
        result = enter_result(
            item, entered_by=technician, values=[{"parameter": "WBC", "value": "7.2"}]
        )
        verify_result(result, verified_by=scientist)

        with pytest.raises(AlreadyVerifiedError):
            verify_result(result, verified_by=scientist)

    def test_a_critical_verified_result_triggers_the_urgent_notification(self):
        item = LabOrderItemFactory()
        technician = UserFactory(facility=item.lab_order.facility)
        scientist = UserFactory(facility=item.lab_order.facility)
        result = enter_result(
            item,
            entered_by=technician,
            values=[{"parameter": "K+", "value": "7.5", "flag": LabResultValue.Flag.CRITICAL}],
        )

        with patch("apps.laboratory.tasks.notify_critical_result.delay") as mock_delay:
            verify_result(result, verified_by=scientist)

        mock_delay.assert_called_once_with(str(result.id))

    def test_order_moves_to_completed_once_every_item_is_verified(self):
        order = LabOrderFactory()
        item_one = LabOrderItemFactory(lab_order=order)
        item_two = LabOrderItemFactory(lab_order=order)
        technician = UserFactory(facility=order.facility)
        scientist = UserFactory(facility=order.facility)

        result_one = enter_result(
            item_one, entered_by=technician, values=[{"parameter": "WBC", "value": "7.2"}]
        )
        result_two = enter_result(
            item_two, entered_by=technician, values=[{"parameter": "FBS", "value": "5.4"}]
        )
        verify_result(result_one, verified_by=scientist)
        order.refresh_from_db()
        assert order.status == LabOrder.Status.PROCESSING

        verify_result(result_two, verified_by=scientist)
        order.refresh_from_db()
        assert order.status == LabOrder.Status.COMPLETED
