"""
Abnormal-vitals notification (BRD §6.5 edge case). NOTE — this is a stub:
the TRD names a dedicated `notifications` app (§4.1, §9) that hasn't been
built yet, same gap already flagged in apps.appointments.tasks. There is no
Notification model to write a real row to yet, so this task can't even do
what dispatch_reminder does (mark a real record sent) — it's a placeholder
call site so the actual delivery mechanism has exactly one place to land
when the notifications app exists, rather than pretending doctors are
already being paged.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def notify_abnormal_vitals(vitals_id):
    """STUB: see module docstring. Logs only — no real notification sent."""
    logger.warning(
        "Abnormal vitals recorded (notification dispatch not yet implemented): %s", vitals_id
    )
    return vitals_id
