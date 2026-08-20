from rest_framework import serializers

from apps.core.serializers import FacilityScopedPrimaryKeyRelatedField
from apps.laboratory.models import LabOrder, LabOrderItem, LabResult, LabResultValue, LabSample

COMMON_READ_ONLY_FIELDS = ["id", "created_at", "updated_at"]


class LabOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabOrderItem
        fields = ["id", "lab_order", "test_code", "test_name", "created_at", "updated_at"]
        read_only_fields = fields


class LabOrderSerializer(serializers.ModelSerializer):
    items = LabOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = LabOrder
        fields = [
            "id",
            "facility",
            "visit",
            "ordered_by",
            "priority",
            "status",
            "ordered_at",
            "items",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "facility",
            "visit",
            "ordered_by",
            "status",
            "ordered_at",
            "items",
            "deleted_at",
            "created_at",
            "updated_at",
        ]


class LabOrderItemInputSerializer(serializers.Serializer):
    test_code = serializers.CharField(max_length=20)
    test_name = serializers.CharField(max_length=150)


class CreateLabOrderSerializer(serializers.Serializer):
    visit = serializers.UUIDField()
    priority = serializers.ChoiceField(
        choices=LabOrder.Priority.choices, default=LabOrder.Priority.ROUTINE
    )
    items = LabOrderItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one test must be ordered.")
        return value


class LabSampleSerializer(serializers.ModelSerializer):
    lab_order_item = FacilityScopedPrimaryKeyRelatedField(
        model=LabOrderItem, facility_lookup="lab_order__facility"
    )

    class Meta:
        model = LabSample
        fields = [
            "id",
            "lab_order_item",
            "barcode",
            "collected_by",
            "collected_at",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "collected_by",
            "collected_at",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]


class RejectSampleSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)


class LabResultValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabResultValue
        fields = [
            "id",
            "lab_result",
            "parameter",
            "value",
            "unit",
            "reference_range",
            "flag",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LabResultValueInputSerializer(serializers.Serializer):
    parameter = serializers.CharField(max_length=50)
    value = serializers.CharField(max_length=30)
    unit = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    reference_range = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )
    flag = serializers.ChoiceField(
        choices=LabResultValue.Flag.choices, default=LabResultValue.Flag.NORMAL
    )


class LabResultSerializer(serializers.ModelSerializer):
    values = LabResultValueSerializer(many=True, read_only=True)

    class Meta:
        model = LabResult
        fields = [
            "id",
            "lab_order_item",
            "entered_by",
            "entered_at",
            "verified_by",
            "verified_at",
            "status",
            "is_critical",
            "released_to_portal_at",
            "values",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "lab_order_item",
            "entered_by",
            "entered_at",
            "verified_by",
            "verified_at",
            "status",
            "is_critical",
            "released_to_portal_at",
            "values",
            "created_at",
            "updated_at",
        ]


class EnterResultSerializer(serializers.Serializer):
    lab_order_item = serializers.UUIDField()
    values = LabResultValueInputSerializer(many=True)

    def validate_values(self, value):
        if not value:
            raise serializers.ValidationError("At least one result value must be entered.")
        return value
