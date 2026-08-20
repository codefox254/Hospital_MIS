from rest_framework import serializers

from apps.patients.models import (
    Allergy,
    ChronicCondition,
    Consent,
    EmergencyContact,
    Guardian,
    Patient,
    PatientInsurance,
)

COMMON_READ_ONLY_FIELDS = ["id", "deleted_at", "created_at", "updated_at"]


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


class GuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = ["id", "patient", "name", "relationship", "phone", "access_revoked_at"] + [
            f for f in COMMON_READ_ONLY_FIELDS if f != "id"
        ]
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ["id", "patient", "name", "relationship", "phone"] + [
            f for f in COMMON_READ_ONLY_FIELDS if f != "id"
        ]
        read_only_fields = COMMON_READ_ONLY_FIELDS


class AllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergy
        fields = ["id", "patient", "substance", "reaction", "severity"] + [
            f for f in COMMON_READ_ONLY_FIELDS if f != "id"
        ]
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ChronicConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChronicCondition
        fields = ["id", "patient", "condition", "diagnosed_date"] + [
            f for f in COMMON_READ_ONLY_FIELDS if f != "id"
        ]
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consent
        fields = ["id", "patient", "type", "granted_at", "revoked_at", "is_active"] + [
            f for f in COMMON_READ_ONLY_FIELDS if f != "id"
        ]
        read_only_fields = COMMON_READ_ONLY_FIELDS + ["is_active"]


class PatientInsuranceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientInsurance
        fields = [
            "id",
            "patient",
            "insurer_name",
            "policy_number",
            "member_number",
            "is_primary",
        ] + [f for f in COMMON_READ_ONLY_FIELDS if f != "id"]
        read_only_fields = COMMON_READ_ONLY_FIELDS
