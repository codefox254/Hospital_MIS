import pytest

from apps.accounts.factories import UserFactory
from apps.opd.factories import ConsultationFactory
from apps.patients.factories import PatientFactory
from apps.patients.models import Allergy
from apps.pharmacy.factories import DrugFactory, PrescriptionItemFactory, StockBatchFactory
from apps.pharmacy.models import Prescription
from apps.pharmacy.services import (
    InsufficientStockError,
    OverDispenseError,
    WrongDrugForBatchError,
    check_patient_allergies,
    create_prescription,
    dispense_medication,
)

pytestmark = pytest.mark.django_db


class TestCreatePrescription:
    @pytest.mark.smoke
    def test_creates_a_prescription_with_its_items(self):
        consultation = ConsultationFactory()
        drug = DrugFactory()

        prescription = create_prescription(
            consultation=consultation,
            patient=consultation.visit.patient,
            prescribed_by=consultation.visit.doctor,
            items=[
                {
                    "drug": drug,
                    "dosage": "1 tablet",
                    "frequency": "twice daily",
                    "qty_prescribed": 14,
                }
            ],
        )

        assert prescription.status == Prescription.Status.PENDING
        assert prescription.items.count() == 1


class TestCheckPatientAllergies:
    def test_flags_a_matching_substance(self):
        patient = PatientFactory()
        Allergy.objects.create(
            patient=patient, substance="Penicillin", reaction="Rash", severity="mild"
        )
        drug = DrugFactory(name="Penicillin", generic_name="")

        conflicts = check_patient_allergies(patient, drug)

        assert len(conflicts) == 1

    def test_no_conflict_for_an_unrelated_drug(self):
        patient = PatientFactory()
        Allergy.objects.create(
            patient=patient, substance="Penicillin", reaction="Rash", severity="mild"
        )
        drug = DrugFactory(name="Paracetamol", generic_name="Acetaminophen")

        conflicts = check_patient_allergies(patient, drug)

        assert conflicts == []


class TestDispenseMedication:
    @pytest.mark.smoke
    def test_dispenses_and_decrements_stock(self):
        item = PrescriptionItemFactory(qty_prescribed=10)
        batch = StockBatchFactory(
            drug=item.drug,
            facility=item.prescription.consultation.visit.facility,
            quantity_on_hand=100,
        )
        pharmacist = UserFactory(facility=item.prescription.consultation.visit.facility)

        record = dispense_medication(item, batch=batch, dispensed_by=pharmacist, qty_dispensed=10)

        batch.refresh_from_db()
        assert batch.quantity_on_hand == 90
        assert record.qty_dispensed == 10

    def test_fully_dispensing_marks_the_prescription_dispensed(self):
        item = PrescriptionItemFactory(qty_prescribed=10)
        batch = StockBatchFactory(
            drug=item.drug,
            facility=item.prescription.consultation.visit.facility,
            quantity_on_hand=100,
        )
        pharmacist = UserFactory(facility=item.prescription.consultation.visit.facility)

        dispense_medication(item, batch=batch, dispensed_by=pharmacist, qty_dispensed=10)

        item.prescription.refresh_from_db()
        assert item.prescription.status == Prescription.Status.DISPENSED

    def test_partially_dispensing_marks_the_prescription_partially_dispensed(self):
        item = PrescriptionItemFactory(qty_prescribed=10)
        batch = StockBatchFactory(
            drug=item.drug,
            facility=item.prescription.consultation.visit.facility,
            quantity_on_hand=100,
        )
        pharmacist = UserFactory(facility=item.prescription.consultation.visit.facility)

        dispense_medication(item, batch=batch, dispensed_by=pharmacist, qty_dispensed=4)

        item.prescription.refresh_from_db()
        assert item.prescription.status == Prescription.Status.PARTIALLY_DISPENSED

    def test_cannot_dispense_more_than_prescribed(self):
        item = PrescriptionItemFactory(qty_prescribed=10)
        batch = StockBatchFactory(
            drug=item.drug,
            facility=item.prescription.consultation.visit.facility,
            quantity_on_hand=100,
        )
        pharmacist = UserFactory(facility=item.prescription.consultation.visit.facility)

        with pytest.raises(OverDispenseError):
            dispense_medication(item, batch=batch, dispensed_by=pharmacist, qty_dispensed=11)

    def test_cannot_dispense_more_than_is_in_stock(self):
        item = PrescriptionItemFactory(qty_prescribed=10)
        batch = StockBatchFactory(
            drug=item.drug,
            facility=item.prescription.consultation.visit.facility,
            quantity_on_hand=5,
        )
        pharmacist = UserFactory(facility=item.prescription.consultation.visit.facility)

        with pytest.raises(InsufficientStockError):
            dispense_medication(item, batch=batch, dispensed_by=pharmacist, qty_dispensed=10)

    def test_cannot_dispense_a_batch_of_the_wrong_drug(self):
        item = PrescriptionItemFactory(qty_prescribed=10)
        wrong_batch = StockBatchFactory(
            facility=item.prescription.consultation.visit.facility, quantity_on_hand=100
        )
        pharmacist = UserFactory(facility=item.prescription.consultation.visit.facility)

        with pytest.raises(WrongDrugForBatchError):
            dispense_medication(item, batch=wrong_batch, dispensed_by=pharmacist, qty_dispensed=1)

    def test_two_partial_dispenses_accumulate_toward_the_prescribed_quantity(self):
        item = PrescriptionItemFactory(qty_prescribed=10)
        batch = StockBatchFactory(
            drug=item.drug,
            facility=item.prescription.consultation.visit.facility,
            quantity_on_hand=100,
        )
        pharmacist = UserFactory(facility=item.prescription.consultation.visit.facility)

        dispense_medication(item, batch=batch, dispensed_by=pharmacist, qty_dispensed=6)
        with pytest.raises(OverDispenseError):
            dispense_medication(item, batch=batch, dispensed_by=pharmacist, qty_dispensed=5)

        dispense_medication(item, batch=batch, dispensed_by=pharmacist, qty_dispensed=4)
        item.prescription.refresh_from_db()
        assert item.prescription.status == Prescription.Status.DISPENSED
