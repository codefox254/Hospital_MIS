"""
Availability, booking, and check-in (BRD §6.2; Solution Spec Flow 5.2).
Double-booking prevention is a real DB constraint (Appointment's
UniqueConstraint on doctor+scheduled_at for active statuses), not just an
application-level check — the same "DB constraint is the real safety net,
application code translates the collision" pattern as patient MRN
generation.
"""

from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone as django_timezone

from apps.appointments.models import Appointment, AppointmentReminder, DoctorSchedule, QueueEntry
from apps.appointments.realtime import publish_queue_update


class SlotAlreadyBookedError(Exception):
    pass


class InvalidCheckInError(Exception):
    pass


def get_available_slots(*, doctor, department, date):
    day_of_week = date.weekday()
    schedules = DoctorSchedule.objects.filter(
        doctor=doctor, department=department, day_of_week=day_of_week, deleted_at__isnull=True
    )

    # A set, not a list: two overlapping DoctorSchedule rows for the same
    # doctor/department/day (e.g. one added without noticing an existing
    # one already covers that window) must not surface the same slot
    # twice — found live, via the web console, as a React "duplicate key"
    # warning that traced back to a real duplicate in the API response,
    # not a frontend rendering bug.
    candidate_slots = set()
    for schedule in schedules:
        current = django_timezone.make_aware(datetime.combine(date, schedule.start_time))
        end = django_timezone.make_aware(datetime.combine(date, schedule.end_time))
        step = timedelta(minutes=schedule.slot_duration_minutes)
        while current + step <= end:
            candidate_slots.add(current)
            current += step

    booked_slots = set(
        Appointment.objects.filter(doctor=doctor, scheduled_at__date=date)
        .exclude(status__in=[Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW])
        .values_list("scheduled_at", flat=True)
    )

    return sorted(slot for slot in candidate_slots if slot not in booked_slots)


def book_appointment(
    *,
    facility,
    patient,
    doctor,
    department,
    scheduled_at,
    duration_minutes,
    booking_channel,
    created_by=None,
    actor=None,
    ip_address=None,
):
    appointment = Appointment(
        facility=facility,
        patient=patient,
        doctor=doctor,
        department=department,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
        booking_channel=booking_channel,
        created_by=created_by,
    )
    try:
        with transaction.atomic():
            appointment.save(actor=actor, ip_address=ip_address)
    except IntegrityError as exc:
        raise SlotAlreadyBookedError(
            f"{doctor} already has an appointment at {scheduled_at}."
        ) from exc

    from apps.appointments.tasks import schedule_appointment_reminder

    schedule_appointment_reminder.delay(str(appointment.id))
    return appointment


def check_in_appointment(appointment, *, actor=None, ip_address=None):
    if appointment.status != Appointment.Status.SCHEDULED:
        raise InvalidCheckInError(
            f"Cannot check in an appointment with status={appointment.status!r}."
        )

    appointment.status = Appointment.Status.CHECKED_IN
    appointment.save(actor=actor, ip_address=ip_address)

    same_day_max = QueueEntry.objects.filter(
        appointment__department=appointment.department,
        appointment__scheduled_at__date=appointment.scheduled_at.date(),
    ).aggregate(Max("queue_number"))["queue_number__max"]
    queue_entry = QueueEntry.objects.create(
        appointment=appointment, queue_number=(same_day_max or 0) + 1
    )

    publish_queue_update(appointment, queue_entry)
    return queue_entry


def schedule_reminder(appointment, *, channel=AppointmentReminder.Channel.SMS, hours_before=24):
    return AppointmentReminder.objects.create(
        appointment=appointment,
        channel=channel,
        scheduled_at=appointment.scheduled_at - timedelta(hours=hours_before),
    )
