"""
Laboratory API permission boundary (TRD §4.3). Negative cases first per
CLAUDE.md §4.3.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.core.factories import DepartmentFactory, FacilityFactory
from apps.laboratory.factories import LabOrderFactory, LabOrderItemFactory
from apps.laboratory.services import enter_result
from apps.opd.factories import VisitFactory

pytestmark = pytest.mark.django_db


def _user_with_permissions(facility, *codes):
    user = UserFactory(facility=facility)
    role = RoleFactory()
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code)
        RolePermissionFactory(role=role, permission=permission)
    UserRoleFactory(user=user, role=role, facility=None)
    return user


@pytest.fixture
def client():
    return APIClient()


class TestLabOrderPermissionBoundary:
    def test_unauthenticated_cannot_list(self, client):
        response = client.get(reverse("laboratory:lab-order-list"))
        assert response.status_code == 401

    def test_user_without_create_permission_cannot_order(self, client):
        facility = FacilityFactory()
        visit = VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        user = _user_with_permissions(facility, "laboratory.lab_order.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("laboratory:lab-order-list"),
            {"visit": str(visit.pk), "items": [{"test_code": "CBC", "test_name": "CBC"}]},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_order(self, client):
        facility = FacilityFactory()
        visit = VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        user = _user_with_permissions(facility, "laboratory.lab_order.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("laboratory:lab-order-list"),
            {
                "visit": str(visit.pk),
                "items": [{"test_code": "CBC", "test_name": "Complete Blood Count"}],
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["status"] == "pending"
        assert len(response.data["items"]) == 1

    def test_cannot_order_against_a_visit_in_another_facility(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        other_visit = VisitFactory(
            department=DepartmentFactory(facility=other_facility), facility=other_facility
        )
        user = _user_with_permissions(facility, "laboratory.lab_order.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("laboratory:lab-order-list"),
            {"visit": str(other_visit.pk), "items": [{"test_code": "CBC", "test_name": "CBC"}]},
            format="json",
        )
        assert response.status_code == 404

    def test_cannot_order_with_an_empty_item_list(self, client):
        facility = FacilityFactory()
        visit = VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        user = _user_with_permissions(facility, "laboratory.lab_order.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("laboratory:lab-order-list"),
            {"visit": str(visit.pk), "items": []},
            format="json",
        )
        assert response.status_code == 400

    def test_orders_from_other_facilities_are_not_listed(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        own = LabOrderFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        LabOrderFactory(
            visit=VisitFactory(
                department=DepartmentFactory(facility=other_facility), facility=other_facility
            )
        )

        user = _user_with_permissions(facility, "laboratory.lab_order.view")
        client.force_authenticate(user=user)
        response = client.get(reverse("laboratory:lab-order-list"))

        returned_ids = {row["id"] for row in response.data["results"]}
        assert returned_ids == {str(own.pk)}


class TestLabSamplePermissionBoundary:
    def test_view_permission_does_not_grant_create(self, client):
        facility = FacilityFactory()
        item = LabOrderItemFactory(
            lab_order=LabOrderFactory(
                visit=VisitFactory(
                    department=DepartmentFactory(facility=facility), facility=facility
                )
            )
        )
        user = _user_with_permissions(facility, "laboratory.lab_sample.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("laboratory:sample-list"),
            {"lab_order_item": str(item.pk), "barcode": "BC001"},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_collect(self, client):
        facility = FacilityFactory()
        item = LabOrderItemFactory(
            lab_order=LabOrderFactory(
                visit=VisitFactory(
                    department=DepartmentFactory(facility=facility), facility=facility
                )
            )
        )
        user = _user_with_permissions(facility, "laboratory.lab_sample.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("laboratory:sample-list"),
            {"lab_order_item": str(item.pk), "barcode": "BC001"},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["collected_by"] == user.pk

    def test_cannot_collect_against_an_order_item_in_another_facility(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        other_item = LabOrderItemFactory(
            lab_order=LabOrderFactory(
                visit=VisitFactory(
                    department=DepartmentFactory(facility=other_facility), facility=other_facility
                )
            )
        )
        user = _user_with_permissions(facility, "laboratory.lab_sample.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("laboratory:sample-list"),
            {"lab_order_item": str(other_item.pk), "barcode": "BC001"},
            format="json",
        )
        assert response.status_code == 400

    def test_create_permission_does_not_grant_reject(self, client):
        facility = FacilityFactory()
        item = LabOrderItemFactory(
            lab_order=LabOrderFactory(
                visit=VisitFactory(
                    department=DepartmentFactory(facility=facility), facility=facility
                )
            )
        )
        user = _user_with_permissions(facility, "laboratory.lab_sample.create")
        client.force_authenticate(user=user)
        sample = client.post(
            reverse("laboratory:sample-list"),
            {"lab_order_item": str(item.pk), "barcode": "BC001"},
            format="json",
        ).data

        response = client.post(
            reverse("laboratory:sample-reject", args=[sample["id"]]), {"reason": "x"}
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_reject_permission_can_reject(self, client):
        facility = FacilityFactory()
        item = LabOrderItemFactory(
            lab_order=LabOrderFactory(
                visit=VisitFactory(
                    department=DepartmentFactory(facility=facility), facility=facility
                )
            )
        )
        user = _user_with_permissions(
            facility, "laboratory.lab_sample.create", "laboratory.lab_sample.reject"
        )
        client.force_authenticate(user=user)
        sample = client.post(
            reverse("laboratory:sample-list"),
            {"lab_order_item": str(item.pk), "barcode": "BC001"},
            format="json",
        ).data

        response = client.post(
            reverse("laboratory:sample-reject", args=[sample["id"]]),
            {"reason": "Hemolyzed"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "rejected"


class TestLabResultPermissionBoundary:
    def test_view_permission_does_not_grant_create(self, client):
        facility = FacilityFactory()
        item = LabOrderItemFactory(
            lab_order=LabOrderFactory(
                visit=VisitFactory(
                    department=DepartmentFactory(facility=facility), facility=facility
                )
            )
        )
        user = _user_with_permissions(facility, "laboratory.lab_result.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("laboratory:result-list"),
            {"lab_order_item": str(item.pk), "values": [{"parameter": "WBC", "value": "7.2"}]},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_enter_a_result(self, client):
        facility = FacilityFactory()
        item = LabOrderItemFactory(
            lab_order=LabOrderFactory(
                visit=VisitFactory(
                    department=DepartmentFactory(facility=facility), facility=facility
                )
            )
        )
        user = _user_with_permissions(facility, "laboratory.lab_result.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("laboratory:result-list"),
            {"lab_order_item": str(item.pk), "values": [{"parameter": "WBC", "value": "7.2"}]},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["entered_by"] == user.pk

    def test_cannot_enter_a_result_with_no_values(self, client):
        facility = FacilityFactory()
        item = LabOrderItemFactory(
            lab_order=LabOrderFactory(
                visit=VisitFactory(
                    department=DepartmentFactory(facility=facility), facility=facility
                )
            )
        )
        user = _user_with_permissions(facility, "laboratory.lab_result.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("laboratory:result-list"),
            {"lab_order_item": str(item.pk), "values": []},
            format="json",
        )
        assert response.status_code == 400

    def test_create_permission_does_not_grant_verify(self, client):
        facility = FacilityFactory()
        item = LabOrderItemFactory(
            lab_order=LabOrderFactory(
                visit=VisitFactory(
                    department=DepartmentFactory(facility=facility), facility=facility
                )
            )
        )
        technician = UserFactory(facility=facility)
        result = enter_result(
            item, entered_by=technician, values=[{"parameter": "WBC", "value": "7.2"}]
        )
        user = _user_with_permissions(facility, "laboratory.lab_result.create")
        client.force_authenticate(user=user)

        response = client.post(reverse("laboratory:result-verify", args=[result.pk]))
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_verify_permission_can_verify_someone_elses_entry(self, client):
        facility = FacilityFactory()
        item = LabOrderItemFactory(
            lab_order=LabOrderFactory(
                visit=VisitFactory(
                    department=DepartmentFactory(facility=facility), facility=facility
                )
            )
        )
        technician = UserFactory(facility=facility)
        result = enter_result(
            item, entered_by=technician, values=[{"parameter": "WBC", "value": "7.2"}]
        )
        scientist = _user_with_permissions(facility, "laboratory.lab_result.verify")
        client.force_authenticate(user=scientist)

        response = client.post(reverse("laboratory:result-verify", args=[result.pk]))
        assert response.status_code == 200
        assert response.data["status"] == "verified"

    def test_the_entering_technician_cannot_verify_their_own_result_via_the_api(self, client):
        facility = FacilityFactory()
        item = LabOrderItemFactory(
            lab_order=LabOrderFactory(
                visit=VisitFactory(
                    department=DepartmentFactory(facility=facility), facility=facility
                )
            )
        )
        technician = _user_with_permissions(
            facility, "laboratory.lab_result.create", "laboratory.lab_result.verify"
        )
        client.force_authenticate(user=technician)
        result_id = client.post(
            reverse("laboratory:result-list"),
            {"lab_order_item": str(item.pk), "values": [{"parameter": "WBC", "value": "7.2"}]},
            format="json",
        ).data["id"]

        response = client.post(reverse("laboratory:result-verify", args=[result_id]))
        assert response.status_code == 400
