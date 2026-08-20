"""
Pharmacy API permission boundary (TRD §4.3). Negative cases first per
CLAUDE.md §4.3.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.core.factories import FacilityFactory
from apps.opd.factories import ConsultationFactory
from apps.patients.models import Allergy
from apps.pharmacy.factories import DrugFactory, PrescriptionItemFactory, StockBatchFactory
from apps.pharmacy.services import create_prescription

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


class TestDrugPermissionBoundary:
    def test_unauthenticated_cannot_list(self, client):
        response = client.get(reverse("pharmacy:drug-list"))
        assert response.status_code == 401

    def test_user_without_create_permission_cannot_add_a_drug(self, client):
        facility = FacilityFactory()
        user = _user_with_permissions(facility, "pharmacy.drug.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:drug-list"), {"name": "Amoxicillin"}, format="json"
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_add_a_drug(self, client):
        facility = FacilityFactory()
        user = _user_with_permissions(facility, "pharmacy.drug.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:drug-list"),
            {"name": "Amoxicillin", "strength": "250mg", "form": "capsule"},
            format="json",
        )
        assert response.status_code == 201


class TestStockBatchPermissionBoundary:
    def test_view_permission_does_not_grant_create(self, client):
        facility = FacilityFactory()
        drug = DrugFactory()
        user = _user_with_permissions(facility, "pharmacy.stock_batch.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:stock-batch-list"),
            {
                "drug": str(drug.pk),
                "batch_number": "B001",
                "expiry_date": "2030-01-01",
                "quantity_on_hand": 100,
            },
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_add_stock(self, client):
        facility = FacilityFactory()
        drug = DrugFactory()
        user = _user_with_permissions(facility, "pharmacy.stock_batch.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:stock-batch-list"),
            {
                "drug": str(drug.pk),
                "batch_number": "B001",
                "expiry_date": "2030-01-01",
                "quantity_on_hand": 100,
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["facility"] == facility.pk

    def test_batches_from_other_facilities_are_not_listed(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        own = StockBatchFactory(facility=facility)
        StockBatchFactory(facility=other_facility)

        user = _user_with_permissions(facility, "pharmacy.stock_batch.view")
        client.force_authenticate(user=user)
        response = client.get(reverse("pharmacy:stock-batch-list"))

        returned_ids = {row["id"] for row in response.data["results"]}
        assert returned_ids == {str(own.pk)}

    @pytest.mark.smoke
    def test_user_with_update_permission_can_restock_a_batch(self, client):
        facility = FacilityFactory()
        batch = StockBatchFactory(facility=facility, quantity_on_hand=10)
        user = _user_with_permissions(facility, "pharmacy.stock_batch.update")
        client.force_authenticate(user=user)

        response = client.patch(
            reverse("pharmacy:stock-batch-detail", args=[batch.pk]),
            {"quantity_on_hand": 50},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["quantity_on_hand"] == 50

    @pytest.mark.smoke
    def test_allergy_check_flags_a_matching_substance(self, client):
        facility = FacilityFactory()
        from apps.patients.factories import PatientFactory

        patient = PatientFactory(facility=facility)
        Allergy.objects.create(
            patient=patient, substance="Penicillin", reaction="Rash", severity="mild"
        )
        drug = DrugFactory(name="Penicillin")
        user = _user_with_permissions(facility, "pharmacy.stock_batch.view")
        client.force_authenticate(user=user)

        response = client.get(
            reverse("pharmacy:stock-batch-allergy-check"),
            {"patient": str(patient.pk), "drug": str(drug.pk)},
        )
        assert response.status_code == 200
        assert len(response.data["conflicts"]) == 1


class TestPrescriptionPermissionBoundary:
    def test_user_without_create_permission_cannot_prescribe(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit__department__facility=facility, visit__facility=facility
        )
        drug = DrugFactory()
        user = _user_with_permissions(facility, "pharmacy.prescription.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:prescription-list"),
            {
                "consultation": str(consultation.pk),
                "items": [
                    {
                        "drug": str(drug.pk),
                        "dosage": "1 tab",
                        "frequency": "bid",
                        "qty_prescribed": 10,
                    }
                ],
            },
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_prescribe(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit__department__facility=facility, visit__facility=facility
        )
        drug = DrugFactory()
        user = _user_with_permissions(facility, "pharmacy.prescription.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:prescription-list"),
            {
                "consultation": str(consultation.pk),
                "items": [
                    {
                        "drug": str(drug.pk),
                        "dosage": "1 tab",
                        "frequency": "bid",
                        "qty_prescribed": 10,
                    }
                ],
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["status"] == "pending"

    def test_cannot_prescribe_against_a_consultation_in_another_facility(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        other_consultation = ConsultationFactory(
            visit__department__facility=other_facility, visit__facility=other_facility
        )
        drug = DrugFactory()
        user = _user_with_permissions(facility, "pharmacy.prescription.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:prescription-list"),
            {
                "consultation": str(other_consultation.pk),
                "items": [
                    {
                        "drug": str(drug.pk),
                        "dosage": "1 tab",
                        "frequency": "bid",
                        "qty_prescribed": 10,
                    }
                ],
            },
            format="json",
        )
        assert response.status_code == 404

    def test_view_permission_does_not_grant_cancel(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit__department__facility=facility, visit__facility=facility
        )
        prescription = create_prescription(
            consultation=consultation,
            patient=consultation.visit.patient,
            prescribed_by=consultation.visit.doctor,
            items=[],
        )
        user = _user_with_permissions(facility, "pharmacy.prescription.view")
        client.force_authenticate(user=user)

        response = client.post(reverse("pharmacy:prescription-cancel", args=[prescription.pk]))
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_cancel_permission_can_cancel_a_pending_prescription(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit__department__facility=facility, visit__facility=facility
        )
        prescription = create_prescription(
            consultation=consultation,
            patient=consultation.visit.patient,
            prescribed_by=consultation.visit.doctor,
            items=[],
        )
        user = _user_with_permissions(facility, "pharmacy.prescription.cancel")
        client.force_authenticate(user=user)

        response = client.post(reverse("pharmacy:prescription-cancel", args=[prescription.pk]))
        assert response.status_code == 200
        assert response.data["status"] == "cancelled"

    def test_cannot_cancel_an_already_cancelled_prescription(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit__department__facility=facility, visit__facility=facility
        )
        prescription = create_prescription(
            consultation=consultation,
            patient=consultation.visit.patient,
            prescribed_by=consultation.visit.doctor,
            items=[],
        )
        user = _user_with_permissions(facility, "pharmacy.prescription.cancel")
        client.force_authenticate(user=user)
        client.post(reverse("pharmacy:prescription-cancel", args=[prescription.pk]))

        response = client.post(reverse("pharmacy:prescription-cancel", args=[prescription.pk]))
        assert response.status_code == 400


class TestDispenseRecordPermissionBoundary:
    def test_view_permission_does_not_grant_create(self, client):
        facility = FacilityFactory()
        item = PrescriptionItemFactory(
            prescription__consultation__visit__department__facility=facility,
            prescription__consultation__visit__facility=facility,
            qty_prescribed=10,
        )
        batch = StockBatchFactory(drug=item.drug, facility=facility, quantity_on_hand=100)
        user = _user_with_permissions(facility, "pharmacy.dispense_record.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:dispense-record-list"),
            {"prescription_item": str(item.pk), "batch": str(batch.pk), "qty_dispensed": 5},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_dispense(self, client):
        facility = FacilityFactory()
        item = PrescriptionItemFactory(
            prescription__consultation__visit__department__facility=facility,
            prescription__consultation__visit__facility=facility,
            qty_prescribed=10,
        )
        batch = StockBatchFactory(drug=item.drug, facility=facility, quantity_on_hand=100)
        user = _user_with_permissions(facility, "pharmacy.dispense_record.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:dispense-record-list"),
            {"prescription_item": str(item.pk), "batch": str(batch.pk), "qty_dispensed": 5},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["dispensed_by"] == user.pk

    def test_cannot_dispense_against_a_batch_in_another_facility(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        item = PrescriptionItemFactory(
            prescription__consultation__visit__department__facility=facility,
            prescription__consultation__visit__facility=facility,
            qty_prescribed=10,
        )
        other_batch = StockBatchFactory(
            drug=item.drug, facility=other_facility, quantity_on_hand=100
        )
        user = _user_with_permissions(facility, "pharmacy.dispense_record.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:dispense-record-list"),
            {"prescription_item": str(item.pk), "batch": str(other_batch.pk), "qty_dispensed": 5},
            format="json",
        )
        assert response.status_code == 404

    def test_cannot_dispense_more_than_is_in_stock_via_the_api(self, client):
        facility = FacilityFactory()
        item = PrescriptionItemFactory(
            prescription__consultation__visit__department__facility=facility,
            prescription__consultation__visit__facility=facility,
            qty_prescribed=10,
        )
        batch = StockBatchFactory(drug=item.drug, facility=facility, quantity_on_hand=3)
        user = _user_with_permissions(facility, "pharmacy.dispense_record.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:dispense-record-list"),
            {"prescription_item": str(item.pk), "batch": str(batch.pk), "qty_dispensed": 5},
            format="json",
        )
        assert response.status_code == 400

    def test_cannot_dispense_more_than_prescribed_via_the_api(self, client):
        facility = FacilityFactory()
        item = PrescriptionItemFactory(
            prescription__consultation__visit__department__facility=facility,
            prescription__consultation__visit__facility=facility,
            qty_prescribed=5,
        )
        batch = StockBatchFactory(drug=item.drug, facility=facility, quantity_on_hand=100)
        user = _user_with_permissions(facility, "pharmacy.dispense_record.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:dispense-record-list"),
            {"prescription_item": str(item.pk), "batch": str(batch.pk), "qty_dispensed": 10},
            format="json",
        )
        assert response.status_code == 400

    def test_cannot_dispense_a_batch_of_the_wrong_drug_via_the_api(self, client):
        facility = FacilityFactory()
        item = PrescriptionItemFactory(
            prescription__consultation__visit__department__facility=facility,
            prescription__consultation__visit__facility=facility,
            qty_prescribed=10,
        )
        wrong_batch = StockBatchFactory(facility=facility, quantity_on_hand=100)
        user = _user_with_permissions(facility, "pharmacy.dispense_record.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:dispense-record-list"),
            {"prescription_item": str(item.pk), "batch": str(wrong_batch.pk), "qty_dispensed": 1},
            format="json",
        )
        assert response.status_code == 400

    def test_dispensing_a_controlled_drug_requires_the_elevated_permission(self, client):
        facility = FacilityFactory()
        controlled_drug = DrugFactory(is_controlled=True)
        item = PrescriptionItemFactory(
            drug=controlled_drug,
            prescription__consultation__visit__department__facility=facility,
            prescription__consultation__visit__facility=facility,
            qty_prescribed=10,
        )
        batch = StockBatchFactory(drug=controlled_drug, facility=facility, quantity_on_hand=100)
        user = _user_with_permissions(facility, "pharmacy.dispense_record.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:dispense-record-list"),
            {"prescription_item": str(item.pk), "batch": str(batch.pk), "qty_dispensed": 5},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_dispensing_a_controlled_drug_succeeds_with_the_elevated_permission(self, client):
        facility = FacilityFactory()
        controlled_drug = DrugFactory(is_controlled=True)
        item = PrescriptionItemFactory(
            drug=controlled_drug,
            prescription__consultation__visit__department__facility=facility,
            prescription__consultation__visit__facility=facility,
            qty_prescribed=10,
        )
        batch = StockBatchFactory(drug=controlled_drug, facility=facility, quantity_on_hand=100)
        user = _user_with_permissions(
            facility,
            "pharmacy.dispense_record.create",
            "pharmacy.dispense_record.create_controlled",
        )
        client.force_authenticate(user=user)

        response = client.post(
            reverse("pharmacy:dispense-record-list"),
            {"prescription_item": str(item.pk), "batch": str(batch.pk), "qty_dispensed": 5},
            format="json",
        )
        assert response.status_code == 201
