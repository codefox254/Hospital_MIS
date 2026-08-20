"""
Read-only audit query API (TRD §8.4): every entry is scoped to the
requesting user's facility, gated by the standard permission engine like
every other endpoint — the audit *store* is independent of the modules it
audits, not independent of access control.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from apps.accounts.permissions import HasModulePermission
from apps.audit.models import AuditLogEntry
from apps.audit.serializers import AuditLogEntrySerializer


class AuditLogEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogEntrySerializer
    permission_classes = [HasModulePermission]
    permission_code = "audit.log.view"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["model_name", "record_id", "action"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AuditLogEntry.objects.none()
        return AuditLogEntry.objects.filter(facility=self.request.user.facility)
