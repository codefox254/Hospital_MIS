"""
Walks Solution Spec Flow 5.4 end-to-end via the real API: order created
against an OPD visit, sample collected, result entered by a technician,
verified by a different user (a scientist can never self-verify), and
released.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.core.factories import DepartmentFactory, FacilityFactory
from apps.opd.factories import VisitFactory

pytestmark = pytest.mark.django_db


def _staff_user(facility, *codes):
    user = UserFactory(facility=facility)
    role = RoleFactory()
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code)
        RolePermissionFactory(role=role, permission=permission)
    UserRoleFactory(user=user, role=role, facility=None)
    return user


@pytest.mark.smoke
def test_full_lab_order_journey():
    client = APIClient()
    facility = FacilityFactory()
    visit = VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)

    doctor = _staff_user(facility, "laboratory.lab_order.create", "laboratory.lab_order.view")
    client.force_authenticate(user=doctor)

    # 1. Doctor orders a CBC and FBS against the visit.
    order_response = client.post(
        reverse("laboratory:lab-order-list"),
        {
            "visit": str(visit.pk),
            "items": [
                {"test_code": "CBC", "test_name": "Complete Blood Count"},
                {"test_code": "FBS", "test_name": "Fasting Blood Sugar"},
            ],
        },
        format="json",
    )
    assert order_response.status_code == 201
    assert order_response.data["status"] == "pending"
    item_ids = [item["id"] for item in order_response.data["items"]]
    assert len(item_ids) == 2

    # 2. Lab technician collects both samples.
    technician = _staff_user(
        facility, "laboratory.lab_sample.create", "laboratory.lab_result.create"
    )
    client.force_authenticate(user=technician)

    for i, item_id in enumerate(item_ids):
        collect_response = client.post(
            reverse("laboratory:sample-list"),
            {"lab_order_item": item_id, "barcode": f"BC{i:03d}"},
            format="json",
        )
        assert collect_response.status_code == 201

    client.force_authenticate(user=doctor)
    order_after_collection = client.get(
        reverse("laboratory:lab-order-detail", args=[order_response.data["id"]])
    )
    client.force_authenticate(user=technician)

    # 3. Technician enters raw results against each item.
    result_ids = []
    for item_id in item_ids:
        result_response = client.post(
            reverse("laboratory:result-list"),
            {
                "lab_order_item": item_id,
                "values": [
                    {"parameter": "WBC", "value": "7.2", "unit": "x10^9/L", "flag": "normal"}
                ],
            },
            format="json",
        )
        assert result_response.status_code == 201
        assert result_response.data["status"] == "entered"
        result_ids.append(result_response.data["id"])

    # 4. Lab scientist (not the technician) verifies both.
    scientist = _staff_user(facility, "laboratory.lab_result.verify")
    client.force_authenticate(user=scientist)

    for result_id in result_ids:
        verify_response = client.post(reverse("laboratory:result-verify", args=[result_id]))
        assert verify_response.status_code == 200
        assert verify_response.data["status"] == "verified"
        assert verify_response.data["released_to_portal_at"] is not None

    # 5. Order is now completed — visible to the ordering doctor.
    client.force_authenticate(user=doctor)
    final_order = client.get(
        reverse("laboratory:lab-order-detail", args=[order_response.data["id"]])
    )
    assert final_order.data["status"] == "completed"
    assert order_after_collection.data["status"] == "collected"
