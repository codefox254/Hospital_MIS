import decimal

from rest_framework import serializers

from apps.billing.models import Invoice, InvoiceLineItem, MpesaTransaction, Payment, Refund

COMMON_READ_ONLY_FIELDS = ["id", "created_at", "updated_at"]


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = [
            "id",
            "invoice",
            "source_module",
            "source_reference_id",
            "description",
            "quantity",
            "unit_price",
            "amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "facility",
            "patient",
            "visit",
            "invoice_number",
            "status",
            "subtotal",
            "discount",
            "tax",
            "total",
            "balance",
            "created_by",
            "line_items",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "facility",
            "patient",
            "visit",
            "invoice_number",
            "status",
            "subtotal",
            "discount",
            "tax",
            "total",
            "balance",
            "created_by",
            "line_items",
            "deleted_at",
            "created_at",
            "updated_at",
        ]


class StartInvoiceSerializer(serializers.Serializer):
    patient = serializers.UUIDField()
    visit = serializers.UUIDField(required=False, allow_null=True)


class ApplyDiscountSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=decimal.Decimal("0")
    )


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "invoice",
            "method",
            "amount",
            "reference",
            "status",
            "received_by",
            "received_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RecordPaymentSerializer(serializers.Serializer):
    invoice = serializers.UUIDField()
    method = serializers.ChoiceField(
        choices=[c for c in Payment.Method.choices if c[0] != Payment.Method.MPESA]
    )
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=decimal.Decimal("0.01")
    )
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")


class MpesaStkPushSerializer(serializers.Serializer):
    invoice = serializers.UUIDField()
    phone_number = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=decimal.Decimal("0.01")
    )


class MpesaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MpesaTransaction
        fields = [
            "id",
            "payment",
            "checkout_request_id",
            "mpesa_receipt_number",
            "phone_number",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class MpesaCallbackSerializer(serializers.Serializer):
    checkout_request_id = serializers.CharField(max_length=100)
    success = serializers.BooleanField()
    mpesa_receipt_number = serializers.CharField(
        max_length=30, required=False, allow_blank=True, default=""
    )
    raw_payload = serializers.JSONField(required=False, default=dict)


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = [
            "id",
            "invoice",
            "payment",
            "amount",
            "reason",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ApproveRefundSerializer(serializers.Serializer):
    invoice = serializers.UUIDField()
    payment = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=decimal.Decimal("0.01")
    )
    reason = serializers.CharField()
