"""
AuditLogEntry (Data Dictionary §2, TRD §8.4): an independent, append-only
record of every clinical/financial write. Independent so an audit doesn't
require trusting the module being audited — this app never imports models
from any app that writes to it (apps.core.mixins.AuditableModel does the
writing, from the other direction).
"""

import uuid

from django.conf import settings
from django.db import models

from apps.core.models import Facility


class AuditLogEntry(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        SOFT_DELETE = "soft_delete", "Soft delete"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_log_entries",
        help_text="Null for system-actor writes (e.g. a Celery job).",
    )
    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, related_name="audit_log_entries"
    )
    model_name = models.CharField(max_length=100)
    record_id = models.UUIDField()
    action = models.CharField(max_length=20, choices=Action.choices)
    field_diff = models.JSONField(null=True, blank=True, help_text="Before/after values per field.")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["facility", "model_name", "record_id"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name_plural = "audit log entries"

    def __str__(self):
        return f"{self.action} {self.model_name}#{self.record_id} by {self.actor_id}"
