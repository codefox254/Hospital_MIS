"""
Live queue publishing (TRD §4.4; Solution Spec Flow 5.2) — a check-in
publishes to the group every subscribed Web Client (reception, nursing,
doctor views) is listening on, keyed by facility+department so a queue
update never leaks across facilities.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def queue_group_name(facility_id, department_id):
    return f"queue-{facility_id}-{department_id}"


def publish_queue_update(appointment, queue_entry):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return  # CHANNEL_LAYERS not configured (e.g. some test contexts) — no-op, not an error

    async_to_sync(channel_layer.group_send)(
        queue_group_name(appointment.facility_id, appointment.department_id),
        {
            "type": "queue.update",
            "appointment_id": str(appointment.id),
            "patient_id": str(appointment.patient_id),
            "status": appointment.status,
            "queue_number": queue_entry.queue_number,
            "priority": queue_entry.priority,
        },
    )
