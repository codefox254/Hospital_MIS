"""
Billing API (BRD §6.9; Solution Spec Flow 5.7). Invoice numbering,
totals, payments, and refunds always go through apps.billing.services —
never a bare ModelViewSet.perform_create() — so "every service-generating
action lands on one open invoice per visit, never a hand-entered charge"
and "the cashier who took a payment can never approve its own refund"
stay enforced in one place.
"""

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework import serializers as drf_serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from apps.accounts.services import user_has_permission
from apps.billing.models import Invoice, InvoiceLineItem, MpesaTransaction, Payment, Refund
from apps.billing.serializers import (
    ApplyDiscountSerializer,
    ApproveRefundSerializer,
    InvoiceLineItemSerializer,
    InvoiceSerializer,
    MpesaCallbackSerializer,
    MpesaStkPushSerializer,
    MpesaTransactionSerializer,
    PaymentSerializer,
    RecordPaymentSerializer,
    RefundSerializer,
    StartInvoiceSerializer,
)
from apps.billing.services import (
    DISCOUNT_APPROVAL_THRESHOLD,
    DiscountApprovalRequiredError,
    RefundExceedsPaymentError,
    SameCashierRefundError,
    apply_discount,
    approve_refund,
    get_or_create_open_invoice,
    initiate_mpesa_stk_push,
    process_mpesa_callback,
    record_payment,
)


class InvoiceViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = InvoiceSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "billing.invoice.view",
        "retrieve": "billing.invoice.view",
        "create": "billing.invoice.create",
        "discount": "billing.invoice.discount",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["patient", "visit", "status"]
    queryset = Invoice.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Invoice.objects.none()
        return Invoice.objects.filter(facility=self.request.user.facility, deleted_at__isnull=True)

    def get_serializer_class(self):
        if self.action == "create":
            return StartInvoiceSerializer
        return InvoiceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.opd.models import Visit
        from apps.patients.models import Patient

        facility = request.user.facility
        patient = get_object_or_404(Patient, pk=data["patient"], facility=facility)
        visit = None
        if data.get("visit"):
            visit = get_object_or_404(Visit, pk=data["visit"], facility=facility)

        invoice = get_or_create_open_invoice(
            facility=facility,
            patient=patient,
            visit=visit,
            created_by=request.user,
            actor=request.user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(InvoiceSerializer(invoice).data, status=201)

    @action(detail=True, methods=["post"])
    def discount(self, request, pk=None):
        """
        Above DISCOUNT_APPROVAL_THRESHOLD requires billing.invoice.
        discount_approve, not just billing.invoice.discount (BRD §6.9) —
        approved_by is only set to the requester when they actually hold
        the elevated permission, otherwise apply_discount() itself raises
        DiscountApprovalRequiredError. Passing approved_by=request.user
        unconditionally here would make every discount self-approved by
        whoever happens to hold the base permission, defeating the rule.
        """
        invoice = self.get_object()
        serializer = ApplyDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        approved_by = None
        if amount <= DISCOUNT_APPROVAL_THRESHOLD or user_has_permission(
            request.user, "billing.invoice.discount_approve"
        ):
            approved_by = request.user

        try:
            apply_discount(
                invoice,
                amount=amount,
                approved_by=approved_by,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except DiscountApprovalRequiredError as exc:
            raise drf_serializers.ValidationError(str(exc), code="discount_approval_required")
        return Response(InvoiceSerializer(invoice).data)


class InvoiceLineItemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceLineItemSerializer
    permission_classes = [HasModulePermission]
    permission_code = "billing.invoice.view"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["invoice", "source_module"]
    queryset = InvoiceLineItem.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return InvoiceLineItem.objects.none()
        return InvoiceLineItem.objects.filter(invoice__facility=self.request.user.facility)


class PaymentViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PaymentSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "billing.payment.view",
        "retrieve": "billing.payment.view",
        "create": "billing.payment.create",
        "mpesa_stk_push": "billing.payment.create",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["invoice", "method", "status"]
    queryset = Payment.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Payment.objects.none()
        return Payment.objects.filter(invoice__facility=self.request.user.facility)

    def get_serializer_class(self):
        if self.action == "create":
            return RecordPaymentSerializer
        if self.action == "mpesa_stk_push":
            return MpesaStkPushSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        facility = request.user.facility
        invoice = get_object_or_404(Invoice, pk=data.pop("invoice"), facility=facility)

        payment = record_payment(
            invoice,
            received_by=request.user,
            actor=request.user,
            ip_address=request.META.get("REMOTE_ADDR"),
            **data,
        )
        return Response(PaymentSerializer(payment).data, status=201)

    @action(detail=False, methods=["post"])
    def mpesa_stk_push(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        invoice = get_object_or_404(Invoice, pk=data["invoice"], facility=request.user.facility)
        mpesa_transaction = initiate_mpesa_stk_push(
            invoice,
            phone_number=data["phone_number"],
            amount=data["amount"],
            actor=request.user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(MpesaTransactionSerializer(mpesa_transaction).data, status=201)


class MpesaTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MpesaTransactionSerializer
    permission_classes = [HasModulePermission]
    permission_code = "billing.payment.view"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["payment", "status"]
    queryset = MpesaTransaction.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return MpesaTransaction.objects.none()
        return MpesaTransaction.objects.filter(
            payment__invoice__facility=self.request.user.facility
        )

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def callback(self, request):
        """
        POST /mpesa-transactions/callback/ — the Daraja webhook endpoint
        (Solution Spec Flow 5.7 step 4). Deliberately unauthenticated
        (AllowAny): this is called by Safaricom's infrastructure, not a
        logged-in user — a real deployment would add IP allowlisting or a
        shared webhook secret, per Safaricom's actual Daraja callback
        auth requirements, which this stub doesn't have credentials to
        verify against. The checkout_request_id (a 128-bit random token,
        apps.billing.services.initiate_mpesa_stk_push) is the only thing
        gating this in the meantime — good enough for a stub that doesn't
        move real money, not a substitute for real webhook auth in
        production.
        """
        serializer = MpesaCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        mpesa_transaction = get_object_or_404(
            MpesaTransaction, checkout_request_id=data["checkout_request_id"]
        )
        process_mpesa_callback(
            data["checkout_request_id"],
            success=data["success"],
            mpesa_receipt_number=data.get("mpesa_receipt_number", ""),
            raw_payload=data.get("raw_payload"),
        )
        mpesa_transaction.refresh_from_db()
        return Response(MpesaTransactionSerializer(mpesa_transaction).data)


class RefundViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = RefundSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "billing.refund.view",
        "retrieve": "billing.refund.view",
        "create": "billing.refund.create",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["invoice", "payment"]
    queryset = Refund.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Refund.objects.none()
        return Refund.objects.filter(invoice__facility=self.request.user.facility)

    def get_serializer_class(self):
        if self.action == "create":
            return ApproveRefundSerializer
        return RefundSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        facility = request.user.facility
        invoice = get_object_or_404(Invoice, pk=data["invoice"], facility=facility)
        payment = get_object_or_404(Payment, pk=data["payment"], invoice=invoice)

        try:
            refund = approve_refund(
                invoice,
                payment,
                amount=data["amount"],
                reason=data["reason"],
                approved_by=request.user,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except SameCashierRefundError as exc:
            raise drf_serializers.ValidationError(str(exc), code="same_cashier_refund")
        except RefundExceedsPaymentError as exc:
            raise drf_serializers.ValidationError(str(exc), code="refund_exceeds_payment")

        return Response(RefundSerializer(refund).data, status=201)
