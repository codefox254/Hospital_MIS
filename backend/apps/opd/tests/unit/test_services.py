from unittest.mock import patch

import pytest

from apps.accounts.factories import UserFactory
from apps.appointments.factories import AppointmentFactory
from apps.appointments.models import Appointment
from apps.core.factories import DepartmentFactory
from apps.opd.factories import ConsultationFactory, VisitFactory
from apps.opd.models import Consultation, Diagnosis, Visit
from apps.opd.services import (
    ConsultationLockedError,
    ConsultationNotLockedError,
    InvalidVisitStartError,
    add_addendum,
    add_diagnosis,
    complete_consultation,
    record_vitals,
    start_visit,
    update_consultation_draft,
)
from apps.patients.factories import PatientFactory

pytestmark = pytest.mark.django_db


class TestStartVisit:
    @pytest.mark.smoke
    def test_starts_a_visit_with_an_empty_draft_consultation(self):
        department = DepartmentFactory()
        patient = PatientFactory(facility=department.facility)
        doctor = UserFactory(facility=department.facility)

        visit = start_visit(
            facility=department.facility,
            patient=patient,
            doctor=doctor,
            department=department,
        )

        assert visit.status == Visit.Status.IN_PROGRESS
        assert Consultation.objects.filter(visit=visit, is_draft=True).exists()

    def test_starting_from_a_checked_in_appointment_moves_it_to_in_consultation(self):
        appointment = AppointmentFactory(status=Appointment.Status.CHECKED_IN)
        patient = appointment.patient

        visit = start_visit(
            facility=appointment.facility,
            patient=patient,
            doctor=appointment.doctor,
            department=appointment.department,
            appointment=appointment,
        )

        appointment.refresh_from_db()
        assert appointment.status == Appointment.Status.IN_CONSULTATION
        assert visit.appointment_id == appointment.id

    def test_cannot_start_a_visit_from_an_appointment_that_isnt_checked_in(self):
        appointment = AppointmentFactory(status=Appointment.Status.SCHEDULED)

        with pytest.raises(InvalidVisitStartError):
            start_visit(
                facility=appointment.facility,
                patient=appointment.patient,
                doctor=appointment.doctor,
                department=appointment.department,
                appointment=appointment,
            )

    def test_walk_in_visit_has_no_appointment(self):
        department = DepartmentFactory()
        patient = PatientFactory(facility=department.facility)
        doctor = UserFactory(facility=department.facility)

        visit = start_visit(
            facility=department.facility, patient=patient, doctor=doctor, department=department
        )

        assert visit.appointment_id is None


class TestRecordVitals:
    @pytest.mark.smoke
    def test_records_vitals_against_the_visit(self):
        visit = VisitFactory()
        nurse = UserFactory(facility=visit.facility)

        vitals = record_vitals(
            visit,
            recorded_by=nurse,
            bp_systolic=120,
            bp_diastolic=80,
            pulse=72,
            temperature_c="36.8",
            respiration_rate=16,
            spo2_percent=98,
            weight_kg="70.00",
            height_cm="170.00",
        )

        assert vitals.visit_id == visit.id
        assert vitals.recorded_by_id == nurse.id

    def test_normal_readings_do_not_trigger_a_notification(self):
        visit = VisitFactory()
        nurse = UserFactory(facility=visit.facility)

        with patch("apps.opd.tasks.notify_abnormal_vitals.delay") as mock_delay:
            record_vitals(visit, recorded_by=nurse, bp_systolic=120, pulse=72, spo2_percent=98)

        mock_delay.assert_not_called()

    def test_out_of_range_reading_triggers_a_notification(self):
        visit = VisitFactory()
        nurse = UserFactory(facility=visit.facility)

        with patch("apps.opd.tasks.notify_abnormal_vitals.delay") as mock_delay:
            vitals = record_vitals(visit, recorded_by=nurse, spo2_percent=80)

        mock_delay.assert_called_once_with(str(vitals.id))


class TestConsultationDraftAndLock:
    @pytest.mark.smoke
    def test_can_update_a_draft_consultation(self):
        consultation = ConsultationFactory()

        update_consultation_draft(consultation, chief_complaint="Headache for 3 days")

        consultation.refresh_from_db()
        assert consultation.chief_complaint == "Headache for 3 days"

    def test_cannot_update_a_locked_consultation(self):
        consultation = ConsultationFactory()
        complete_consultation(consultation, actor=UserFactory(facility=consultation.visit.facility))

        with pytest.raises(ConsultationLockedError):
            update_consultation_draft(consultation, chief_complaint="Edited after signing")

    @pytest.mark.smoke
    def test_complete_consultation_locks_it_and_closes_the_visit(self):
        consultation = ConsultationFactory()
        doctor = consultation.visit.doctor

        complete_consultation(consultation, actor=doctor)

        consultation.refresh_from_db()
        assert consultation.is_draft is False
        assert consultation.locked_at is not None
        assert consultation.signed_by_id == doctor.id

        consultation.visit.refresh_from_db()
        assert consultation.visit.status == Visit.Status.COMPLETED
        assert consultation.visit.completed_at is not None

    def test_completing_an_already_locked_consultation_raises(self):
        consultation = ConsultationFactory()
        doctor = consultation.visit.doctor
        complete_consultation(consultation, actor=doctor)

        with pytest.raises(ConsultationLockedError):
            complete_consultation(consultation, actor=doctor)

    def test_completing_a_visit_with_an_appointment_completes_the_appointment_too(self):
        appointment = AppointmentFactory(status=Appointment.Status.CHECKED_IN)
        visit = start_visit(
            facility=appointment.facility,
            patient=appointment.patient,
            doctor=appointment.doctor,
            department=appointment.department,
            appointment=appointment,
        )

        complete_consultation(visit.consultation, actor=appointment.doctor)

        appointment.refresh_from_db()
        assert appointment.status == Appointment.Status.COMPLETED


class TestDiagnosisAndAddendum:
    @pytest.mark.smoke
    def test_can_add_a_diagnosis_to_a_draft_consultation(self):
        consultation = ConsultationFactory()

        diagnosis = add_diagnosis(
            consultation,
            description="Essential hypertension",
            type=Diagnosis.Type.PRIMARY,
            icd_code="I10",
        )

        assert diagnosis.consultation_id == consultation.id

    def test_cannot_add_a_diagnosis_to_a_locked_consultation(self):
        consultation = ConsultationFactory()
        complete_consultation(consultation, actor=consultation.visit.doctor)

        with pytest.raises(ConsultationLockedError):
            add_diagnosis(consultation, description="Late diagnosis", type=Diagnosis.Type.PRIMARY)

    def test_cannot_add_an_addendum_to_an_unlocked_consultation(self):
        consultation = ConsultationFactory()

        with pytest.raises(ConsultationNotLockedError):
            add_addendum(consultation, author=consultation.visit.doctor, text="Too early")

    @pytest.mark.smoke
    def test_can_add_an_addendum_once_locked(self):
        consultation = ConsultationFactory()
        doctor = consultation.visit.doctor
        complete_consultation(consultation, actor=doctor)

        addendum = add_addendum(consultation, author=doctor, text="Follow-up note")

        assert addendum.consultation_id == consultation.id
        assert addendum.author_id == doctor.id
