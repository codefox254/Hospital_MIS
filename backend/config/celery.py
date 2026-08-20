"""
Celery application bootstrap (TRD §4.4). Loaded by both the `celery worker`
and `celery beat` processes in docker-compose.yml via `-A config`.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("hospital_mis")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
