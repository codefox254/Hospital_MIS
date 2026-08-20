"""A trivial task proving the Celery/Redis wiring actually works end-to-end
(TRD §4.4) — business tasks (notifications, reminders, ...) land with the
modules that need them."""

from celery import shared_task


@shared_task
def ping():
    return "pong"
