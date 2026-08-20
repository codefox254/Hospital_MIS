import datetime
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.appointments.factories import AppointmentFactory, DoctorScheduleFactory
from apps.appointments.models import Appointment, AppointmentReminder
from apps.appointments.services import (
    InvalidCheckInError,
    SlotAlreadyBookedError,
    book_appointment,
    check_in_appointment,
    get_available_slots,
    schedule_reminder,
)
from apps.core.factories import DepartmentFactory
from apps.patients.factories import PatientFactory

pytestmark = pytest.mark.django_db


def _next_monday():
    today = timezone.localdate()
    days_ahead = (0 - today.weekday()) % 7 or 7
    return today + datetime.timedelta(days=days_ahead)


class TestGetAvailableSlots:
    def test_generates_slots_across_the_full_window(self):
        department = DepartmentFactory()
        doctor = UserFactory(facility=department.facility)
        schedule = DoctorScheduleFactory(
            doctor=doctor,
            department=department,
            day_of_week=0,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(10, 0),
            slot_duration_minutes=30,
        )
        target_date = _next_monday()

        slots = get_available_slots(doctor=doctor, department=department, date=target_date)

        assert len(slots) == 2
        assert slots[0].time() == datetime.time(9, 0)
        assert slots[1].time() == datetime.time(9, 30)
        assert schedule.doctor_id == doctor.id  # sanity: schedule actually used

    def test_overlapping_schedules_do_not_produce_duplicate_slots(self):
        """Two DoctorSchedule rows covering the same window for the same
        doctor/department/day — found live via the web console, where it
        surfaced as a React duplicate-key warning traced back to the API
        genuinely returning the same slot twice."""
        department = DepartmentFactory()
        doctor = UserFactory(facility=department.facility)
        for _ in range(2):
            DoctorScheduleFactory(
                doctor=doctor,
                department=department,
                day_of_week=0,
                start_time=datetime.time(9, 0),
                end_time=datetime.time(10, 0),
                slot_duration_minutes=30,
            )
        target_date = _next_monday()

        slots = get_available_slots(doctor=doctor, department=department, date=target_date)

        assert len(slots) == 2
        assert len(slots) == len(set(slots))

    def test_no_schedule_for_that_day_returns_no_slots(self):
        department = DepartmentFactory()
        doctor = UserFactory(facility=department.facility)
        DoctorScheduleFactory(doctor=doctor, department=department, day_of_week=0)

        tuesday = _next_monday() + datetime.timedelta(days=1)
        slots = get_available_slots(doctor=doctor, department=department, date=tuesday)
        assert slots == []

    def test_already_booked_slot_is_excluded(self):
        department = DepartmentFactory()
        doctor = UserFactory(facility=department.facility)
        DoctorScheduleFactory(
            doctor=doctor,
            department=department,
            day_of_week=0,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(10, 0),
            slot_duration_minutes=30,
        )
        target_date = _next_monday()
        booked_at = timezone.make_aware(datetime.datetime.combine(target_date, datetime.time(9, 0)))
        AppointmentFactory(
            doctor=doctor,
            department=department,
            facility=department.facility,
            scheduled_at=booked_at,
        )

        slots = get_available_slots(doctor=doctor, department=department, date=target_date)
        assert booked_at not in slots
        assert len(slots) == 1

    def test_cancelled_appointment_frees_the_slot_again(self):
        department = DepartmentFactory()
        doctor = UserFactory(facility=department.facility)
        DoctorScheduleFactory(
            doctor=doctor,
            department=department,
            day_of_week=0,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(10, 0),
            slot_duration_minutes=30,
        )
        target_date = _next_monday()
        booked_at = timezone.make_aware(datetime.datetime.combine(target_date, datetime.time(9, 0)))
        appointment = AppointmentFactory(
            doctor=doctor,
            department=department,
            facility=department.facility,
            scheduled_at=booked_at,
        )
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()

        slots = get_available_slots(doctor=doctor, department=department, date=target_date)
        assert booked_at in slots


class TestBookAppointment:
    @pytest.mark.smoke
    def test_books_successfully(self):
        department = DepartmentFactory()
        doctor = UserFactory(facility=department.facility)
        patient = PatientFactory(facility=department.facility)
        actor = UserFactory(facility=department.facility)
        scheduled_at = timezone.now() + datetime.timedelta(days=1)

        appointment = book_appointment(
            facility=department.facility,
            patient=patient,
            doctor=doctor,
            department=department,
            scheduled_at=scheduled_at,
            duration_minutes=30,
            booking_channel=Appointment.BookingChannel.WEB,
            actor=actor,
        )

        assert appointment.status == Appointment.Status.SCHEDULED
        assert Appointment.objects.filter(pk=appointment.pk).exists()

    def test_booking_enqueues_a_reminder_task_without_blocking(self):
        """
        The reminder dispatch is fire-and-forget (Solution Spec Flow 5.2:
        "never blocks the booking response") — verified here as "the task
        was enqueued with the right appointment," not by actually running a
        worker in-process, which is what the live docker-compose smoke test
        (see PR description) confirms end-to-end instead.
        """
        department = DepartmentFactory()
        doctor = UserFactory(facility=department.facility)
        patient = PatientFactory(facility=department.facility)

        with patch("apps.appointments.tasks.schedule_appointment_reminder.delay") as mock_delay:
            appointment = book_appointment(
                facility=department.facility,
                patient=patient,
                doctor=doctor,
                department=department,
                scheduled_at=timezone.now() + datetime.timedelta(days=1),
                duration_minutes=30,
                booking_channel=Appointment.BookingChannel.WEB,
            )

        mock_delay.assert_called_once_with(str(appointment.id))

    def test_double_booking_raises_domain_error_not_integrity_error(self):
        existing = AppointmentFactory()
        patient = PatientFactory(facility=existing.facility)

        with pytest.raises(SlotAlreadyBookedError):
            book_appointment(
                facility=existing.facility,
                patient=patient,
                doctor=existing.doctor,
                department=existing.department,
                scheduled_at=existing.scheduled_at,
                duration_minutes=30,
                booking_channel=Appointment.BookingChannel.WALK_IN,
            )


class TestCheckInAppointment:
    @pytest.mark.smoke
    def test_check_in_creates_a_queue_entry_and_flips_status(self):
        appointment = AppointmentFactory()
        queue_entry = check_in_appointment(appointment)

        appointment.refresh_from_db()
        assert appointment.status == Appointment.Status.CHECKED_IN
        assert queue_entry.appointment_id == appointment.id
        assert queue_entry.queue_number == 1

    def test_queue_numbers_increment_within_the_same_department_and_day(self):
        department = DepartmentFactory()
        first = AppointmentFactory(department=department, facility=department.facility)
        second = AppointmentFactory(
            department=department,
            facility=department.facility,
            scheduled_at=first.scheduled_at + datetime.timedelta(hours=1),
        )

        first_entry = check_in_appointment(first)
        second_entry = check_in_appointment(second)

        assert first_entry.queue_number == 1
        assert second_entry.queue_number == 2

    def test_cannot_check_in_an_already_checked_in_appointment(self):
        appointment = AppointmentFactory()
        check_in_appointment(appointment)
        appointment.refresh_from_db()

        with pytest.raises(InvalidCheckInError):
            check_in_appointment(appointment)

    def test_cannot_check_in_a_cancelled_appointment(self):
        appointment = AppointmentFactory()
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()

        with pytest.raises(InvalidCheckInError):
            check_in_appointment(appointment)


class TestScheduleReminder:
    def test_reminder_is_scheduled_24_hours_before_by_default(self):
        appointment = AppointmentFactory()
        reminder = schedule_reminder(appointment)

        assert reminder.scheduled_at == appointment.scheduled_at - datetime.timedelta(hours=24)
        assert reminder.status == AppointmentReminder.Status.PENDING
