from rest_framework import serializers

from apps.opd.models import Consultation, ConsultationAddendum, Diagnosis, Visit, Vitals

COMMON_READ_ONLY_FIELDS = ["id", "created_at", "updated_at"]


class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = [
            "id",
            "facility",
            "patient",
            "appointment",
            "doctor",
            "department",
            "status",
            "checked_in_at",
            "completed_at",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "facility",
            "status",
            "checked_in_at",
            "completed_at",
            "deleted_at",
            "created_at",
            "updated_at",
        ]


class StartVisitSerializer(serializers.Serializer):
    patient = serializers.UUIDField()
    doctor = serializers.UUIDField()
    department = serializers.UUIDField()
    appointment = serializers.UUIDField(required=False, allow_null=True)


class VitalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vitals
        fields = [
            "id",
            "visit",
            "recorded_by",
            "bp_systolic",
            "bp_diastolic",
            "pulse",
            "temperature_c",
            "respiration_rate",
            "spo2_percent",
            "weight_kg",
            "height_cm",
            "recorded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "recorded_by", "recorded_at", "created_at", "updated_at"]


class ConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = [
            "id",
            "visit",
            "chief_complaint",
            "history_of_present_illness",
            "examination_notes",
            "is_draft",
            "locked_at",
            "signed_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "visit",
            "is_draft",
            "locked_at",
            "signed_by",
            "created_at",
            "updated_at",
        ]


class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = [
            "id",
            "consultation",
            "icd_code",
            "description",
            "type",
            "created_at",
            "updated_at",
        ]
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ConsultationAddendumSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationAddendum
        fields = ["id", "consultation", "author", "text", "created_at"]
        read_only_fields = ["id", "author", "created_at"]
