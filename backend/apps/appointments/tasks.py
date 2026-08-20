"""
Async confirmation + reminder dispatch (TRD §4.4; Solution Spec Flow 5.2:
"never blocks the booking response"). NOTE — dispatch is currently a stub:
the TRD names a dedicated `notifications` app (§4.1, §9) wrapping the real
SMS/WhatsApp/push/email providers, which hasn't been built yet. This task
creates the AppointmentReminder row (real, queryable) and immediately marks
it sent rather than actually calling out to a provider — flagged here
rather than silently pretending notifications are live.
"""

from celery import shared_task
from django.utils import timezone

from apps.appointments.models import AppointmentReminder


@shared_task
def schedule_appointment_reminder(appointment_id):
    from apps.appointments.models import Appointment
    from apps.appointments.services import schedule_reminder

    appointment = Appointment.objects.get(pk=appointment_id)
    reminder = schedule_reminder(appointment)
    dispatch_reminder.delay(str(reminder.id))
    return str(reminder.id)


@shared_task
def dispatch_reminder(reminder_id):
    """STUB: marks the reminder sent without calling a real provider — see
    module docstring. Real dispatch lands with the notifications app."""
    updated = AppointmentReminder.objects.filter(pk=reminder_id).update(
        status=AppointmentReminder.Status.SENT, sent_at=timezone.now()
    )
    return bool(updated)
