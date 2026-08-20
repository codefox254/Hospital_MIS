"""
AuditableModel — every clinical/financial write flows through this (TRD
§8.4; CLAUDE.md core principle: no clinical/financial table is ever hard-
deleted or silently overwritten). Combine with FacilityScopedModel:

    class Patient(FacilityScopedModel, AuditableModel):
        ...

save() computes a field-level diff against the previous DB row (the full
initial snapshot on create) and writes it to the independent audit app.
delete() is deliberately disabled — use soft_delete().

apps.audit is imported lazily inside methods, not at module scope: this
module is part of apps.core, which apps.audit itself depends on (for
Facility), so a module-level import here would be a real import cycle.
"""

import datetime
import decimal
import uuid

from django.db import models
from django.utils import timezone


def _serialize(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    return str(value)


class AuditableModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        abstract = True

    def _audited_field_names(self):
        excluded = {"id", "created_at", "updated_at", "created_by_id", "updated_by_id"}
        return [f.attname for f in self._meta.concrete_fields if f.attname not in excluded]

    def _diff_against_db(self):
        try:
            old = type(self).objects.get(pk=self.pk)
        except type(self).DoesNotExist:
            return {}
        diff = {}
        for name in self._audited_field_names():
            old_value, new_value = getattr(old, name), getattr(self, name)
            if old_value != new_value:
                diff[name] = {"old": _serialize(old_value), "new": _serialize(new_value)}
        return diff

    def _write_audit_entry(self, *, action, diff, actor, ip_address):
        from apps.audit.models import AuditLogEntry

        if not diff:
            return
        AuditLogEntry.objects.create(
            actor=actor,
            facility_id=self.facility_id,
            model_name=self._meta.label,
            record_id=self.pk,
            action=action,
            field_diff=diff,
            ip_address=ip_address,
        )

    def save(self, *args, actor=None, ip_address=None, **kwargs):
        from apps.audit.models import AuditLogEntry

        is_create = self._state.adding
        diff = {} if is_create else self._diff_against_db()

        super().save(*args, **kwargs)

        if is_create:
            diff = {
                name: {"old": None, "new": _serialize(getattr(self, name))}
                for name in self._audited_field_names()
            }

        self._write_audit_entry(
            action=AuditLogEntry.Action.CREATE if is_create else AuditLogEntry.Action.UPDATE,
            diff=diff,
            actor=actor,
            ip_address=ip_address,
        )

    def soft_delete(self, *, actor=None, ip_address=None):
        from apps.audit.models import AuditLogEntry

        if self.deleted_at is not None:
            return
        old_deleted_at = self.deleted_at
        self.deleted_at = timezone.now()
        super().save(update_fields=["deleted_at"])
        self._write_audit_entry(
            action=AuditLogEntry.Action.SOFT_DELETE,
            diff={
                "deleted_at": {
                    "old": _serialize(old_deleted_at),
                    "new": _serialize(self.deleted_at),
                }
            },
            actor=actor,
            ip_address=ip_address,
        )

    def delete(self, *args, **kwargs):
        raise NotImplementedError(
            "Hard delete is disabled on audited models (TRD §8.4) — use soft_delete() instead."
        )
