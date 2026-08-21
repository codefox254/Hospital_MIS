import pytest
from django.db import IntegrityError, transaction

from apps.appointments.factories import (
    AppointmentFactory,
    AppointmentReminderFactory,
    DoctorScheduleFactory,
    QueueEntryFactory,
)
from apps.appointments.models import Appointment, QueueEntry

pytestmark = pytest.mark.django_db


class TestDoctorSchedule:
    def test_day_of_week_must_be_in_range(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            DoctorScheduleFactory(day_of_week=7)

    def test_negative_day_of_week_is_rejected(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            DoctorScheduleFactory(day_of_week=-1)

    def test_slot_duration_must_be_positive(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            DoctorScheduleFactory(slot_duration_minutes=0)

    def test_hard_delete_is_disabled(self):
        schedule = DoctorScheduleFactory()
        with pytest.raises(NotImplementedError):
            schedule.delete()

    def test_audit_facility_resolves_through_department(self):
        from apps.audit.models import AuditLogEntry

        schedule = DoctorScheduleFactory()
        entry = AuditLogEntry.objects.get(record_id=schedule.pk, action=AuditLogEntry.Action.CREATE)
        assert entry.facility_id == schedule.department.facility_id


class TestAppointment:
    def test_double_booking_same_doctor_same_slot_is_rejected(self):
        appointment = AppointmentFactory()
        with pytest.raises(IntegrityError), transaction.atomic():
            AppointmentFactory(
                doctor=appointment.doctor,
                department=appointment.department,
                facility=appointment.facility,
                scheduled_at=appointment.scheduled_at,
            )

    def test_double_booking_is_allowed_once_original_is_cancelled(self):
        appointment = AppointmentFactory()
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()

        # Should not raise — a cancelled slot frees up.
        AppointmentFactory(
            doctor=appointment.doctor,
            department=appointment.department,
            facility=appointment.facility,
            scheduled_at=appointment.scheduled_at,
        )

    def test_different_doctors_can_share_the_same_time_slot(self):
        appointment = AppointmentFactory()
        # Different doctor, same time — should not raise.
        AppointmentFactory(scheduled_at=appointment.scheduled_at)

    def test_status_defaults_to_scheduled(self):
        appointment = AppointmentFactory()
        assert appointment.status == Appointment.Status.SCHEDULED

    def test_hard_delete_is_disabled(self):
        appointment = AppointmentFactory()
        with pytest.raises(NotImplementedError):
            appointment.delete()


class TestQueueEntry:
    def test_one_queue_entry_per_appointment(self):
        appointment = AppointmentFactory()
        QueueEntryFactory(appointment=appointment)
        with pytest.raises(IntegrityError), transaction.atomic():
            QueueEntryFactory(appointment=appointment)

    def test_called_at_defaults_null(self):
        entry = QueueEntryFactory()
        assert entry.called_at is None

    def test_emergency_patients_sort_first_not_last(self):
        """Regression: Meta.ordering used to be `["-priority", ...]`, a
        plain descending sort on the CharField's string value. Since
        "priority" > "normal" > "emergency" alphabetically, that put
        EMERGENCY patients *last* in the queue — a clinical-safety bug,
        not just a display quirk. Explicit Case/When ranking fixes it;
        this proves emergency comes first regardless of arrival order."""
        normal = QueueEntryFactory(priority=QueueEntry.Priority.NORMAL, queue_number=1)
        priority = QueueEntryFactory(priority=QueueEntry.Priority.PRIORITY, queue_number=2)
        emergency = QueueEntryFactory(priority=QueueEntry.Priority.EMERGENCY, queue_number=3)

        ordered = list(QueueEntry.objects.filter(id__in=[normal.id, priority.id, emergency.id]))

        assert ordered == [emergency, priority, normal]

    def test_same_priority_breaks_tie_by_queue_number(self):
        second = QueueEntryFactory(priority=QueueEntry.Priority.NORMAL, queue_number=2)
        first = QueueEntryFactory(priority=QueueEntry.Priority.NORMAL, queue_number=1)

        ordered = list(QueueEntry.objects.filter(id__in=[first.id, second.id]))

        assert ordered == [first, second]


class TestAppointmentReminder:
    def test_status_defaults_pending(self):
        reminder = AppointmentReminderFactory()
        assert reminder.status == "pending"

    def test_sent_at_defaults_null(self):
        reminder = AppointmentReminderFactory()
        assert reminder.sent_at is None
