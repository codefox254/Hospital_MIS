from rest_framework import serializers

from apps.patients.models import Patient


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "id",
            "facility",
            "mrn",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "national_id",
            "phone",
            "email",
            "photo_url",
            "blood_group",
            "is_provisional",
            "merged_into_patient",
            "is_merged",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "facility",
            "mrn",
            "merged_into_patient",
            "is_merged",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
