"""
Critical-result alert (TRD §3.1: target latency < 60s, bypassing the
standard notification queue). NOTE — this is a stub, same gap already
flagged in apps.appointments.tasks and apps.opd.tasks: the dedicated
notifications app doesn't exist yet, so there's no real provider to call
and no Notification model to write a row to. Placeholder call site only.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(priority=9)
def notify_critical_result(lab_result_id):
    """STUB: see module docstring. Logs only — no real notification sent."""
    logger.critical(
        "Critical lab result verified (notification dispatch not yet implemented): %s",
        lab_result_id,
    )
    return lab_result_id
