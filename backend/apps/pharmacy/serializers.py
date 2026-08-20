from rest_framework import serializers

from apps.pharmacy.models import DispenseRecord, Drug, Prescription, PrescriptionItem, StockBatch

COMMON_READ_ONLY_FIELDS = ["id", "created_at", "updated_at"]


class DrugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = [
            "id",
            "name",
            "generic_name",
            "form",
            "strength",
            "is_controlled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = COMMON_READ_ONLY_FIELDS


class StockBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockBatch
        fields = [
            "id",
            "facility",
            "drug",
            "batch_number",
            "expiry_date",
            "quantity_on_hand",
            "unit_cost",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "facility", "deleted_at", "created_at", "updated_at"]


class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = [
            "id",
            "prescription",
            "drug",
            "dosage",
            "frequency",
            "duration_days",
            "qty_prescribed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)

    class Meta:
        model = Prescription
        fields = [
            "id",
            "consultation",
            "patient",
            "prescribed_by",
            "status",
            "items",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "consultation",
            "patient",
            "prescribed_by",
            "status",
            "items",
            "deleted_at",
            "created_at",
            "updated_at",
        ]


class PrescriptionItemInputSerializer(serializers.Serializer):
    drug = serializers.UUIDField()
    dosage = serializers.CharField(max_length=50)
    frequency = serializers.CharField(max_length=50)
    duration_days = serializers.IntegerField(required=False, allow_null=True, default=None)
    qty_prescribed = serializers.IntegerField(min_value=1)


class CreatePrescriptionSerializer(serializers.Serializer):
    consultation = serializers.UUIDField()
    items = PrescriptionItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item must be prescribed.")
        return value


class DispenseRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispenseRecord
        fields = [
            "id",
            "prescription_item",
            "batch",
            "dispensed_by",
            "qty_dispensed",
            "dispensed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DispenseSerializer(serializers.Serializer):
    prescription_item = serializers.UUIDField()
    batch = serializers.UUIDField()
    qty_dispensed = serializers.IntegerField(min_value=1)
