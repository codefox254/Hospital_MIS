"""
Walks Solution Spec Flow 5.6 end-to-end via the real API: prescription
created against an OPD consultation, pharmacist checks stock + allergy
screening, confirms dispensing, and stock decrements transactionally.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.opd.factories import ConsultationFactory
from apps.pharmacy.factories import DrugFactory, StockBatchFactory

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
def test_full_pharmacy_dispensing_journey():
    client = APIClient()
    consultation = ConsultationFactory()
    facility = consultation.visit.facility
    drug = DrugFactory(name="Amoxicillin", strength="250mg")
    batch = StockBatchFactory(drug=drug, facility=facility, quantity_on_hand=50)

    doctor = _staff_user(facility, "pharmacy.prescription.create", "pharmacy.prescription.view")
    client.force_authenticate(user=doctor)

    # 1. Prescription created in OPD.
    prescription_response = client.post(
        reverse("pharmacy:prescription-list"),
        {
            "consultation": str(consultation.pk),
            "items": [
                {
                    "drug": str(drug.pk),
                    "dosage": "1 capsule",
                    "frequency": "three times daily",
                    "duration_days": 5,
                    "qty_prescribed": 15,
                }
            ],
        },
        format="json",
    )
    assert prescription_response.status_code == 201
    item_id = prescription_response.data["items"][0]["id"]

    # 2. Pharmacist checks stock and allergy screening.
    pharmacist = _staff_user(
        facility, "pharmacy.stock_batch.view", "pharmacy.dispense_record.create"
    )
    client.force_authenticate(user=pharmacist)

    screen_response = client.get(
        reverse("pharmacy:stock-batch-allergy-check"),
        {"patient": str(consultation.visit.patient.pk), "drug": str(drug.pk)},
    )
    assert screen_response.status_code == 200
    assert screen_response.data["conflicts"] == []

    # 3. Pharmacist confirms dispensing.
    dispense_response = client.post(
        reverse("pharmacy:dispense-record-list"),
        {"prescription_item": item_id, "batch": str(batch.pk), "qty_dispensed": 15},
        format="json",
    )
    assert dispense_response.status_code == 201

    # Stock decremented transactionally.
    batch.refresh_from_db()
    assert batch.quantity_on_hand == 35

    # Prescription fully dispensed.
    client.force_authenticate(user=doctor)
    final_prescription = client.get(
        reverse("pharmacy:prescription-detail", args=[prescription_response.data["id"]])
    )
    assert final_prescription.data["status"] == "dispensed"
