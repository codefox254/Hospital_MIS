from rest_framework import serializers

from apps.audit.models import AuditLogEntry


class AuditLogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLogEntry
        fields = [
            "id",
            "actor",
            "facility",
            "model_name",
            "record_id",
            "action",
            "field_diff",
            "ip_address",
            "created_at",
        ]
        read_only_fields = fields
