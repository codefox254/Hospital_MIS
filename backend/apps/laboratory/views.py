"""
Laboratory API (BRD §6.6; Solution Spec Flow 5.4). Order creation, sample
collection, and result entry/verification always go through
apps.laboratory.services — never a bare ModelViewSet.perform_create() —
so the order-status lifecycle and the entered-by/verified-by separation of
duties stay in one place.
"""

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework import serializers as drf_serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from apps.laboratory.models import LabOrder, LabOrderItem, LabResult, LabSample
from apps.laboratory.serializers import (
    CreateLabOrderSerializer,
    EnterResultSerializer,
    LabOrderItemSerializer,
    LabOrderSerializer,
    LabResultSerializer,
    LabSampleSerializer,
    RejectSampleSerializer,
)
from apps.laboratory.services import (
    AlreadyVerifiedError,
    SelfVerificationError,
    collect_sample,
    create_lab_order,
    enter_result,
    reject_sample,
    verify_result,
)


class LabOrderViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = LabOrderSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "laboratory.lab_order.view",
        "retrieve": "laboratory.lab_order.view",
        "create": "laboratory.lab_order.create",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["visit", "status", "priority"]
    queryset = LabOrder.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LabOrder.objects.none()
        return LabOrder.objects.filter(facility=self.request.user.facility, deleted_at__isnull=True)

    def get_serializer_class(self):
        if self.action == "create":
            return CreateLabOrderSerializer
        return LabOrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.opd.models import Visit

        facility = request.user.facility
        visit = get_object_or_404(Visit, pk=data["visit"], facility=facility)

        order = create_lab_order(
            facility=facility,
            visit=visit,
            ordered_by=request.user,
            items=data["items"],
            priority=data["priority"],
            actor=request.user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(LabOrderSerializer(order).data, status=201)


class LabOrderItemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LabOrderItemSerializer
    permission_classes = [HasModulePermission]
    permission_code = "laboratory.lab_order.view"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["lab_order"]
    queryset = LabOrderItem.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LabOrderItem.objects.none()
        return LabOrderItem.objects.filter(lab_order__facility=self.request.user.facility)


class LabSampleViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = LabSampleSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "laboratory.lab_sample.view",
        "retrieve": "laboratory.lab_sample.view",
        "create": "laboratory.lab_sample.create",
        "reject": "laboratory.lab_sample.reject",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["lab_order_item", "status"]
    queryset = LabSample.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LabSample.objects.none()
        return LabSample.objects.filter(
            lab_order_item__lab_order__facility=self.request.user.facility
        )

    def perform_create(self, serializer):
        sample = collect_sample(
            serializer.validated_data.pop("lab_order_item"),
            collected_by=self.request.user,
            barcode=serializer.validated_data["barcode"],
            actor=self.request.user,
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )
        serializer.instance = sample

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        sample = self.get_object()
        serializer = RejectSampleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reject_sample(
            sample,
            reason=serializer.validated_data["reason"],
            actor=request.user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(LabSampleSerializer(sample).data)


class LabResultViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = LabResultSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "laboratory.lab_result.view",
        "retrieve": "laboratory.lab_result.view",
        "create": "laboratory.lab_result.create",
        "verify": "laboratory.lab_result.verify",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["lab_order_item", "status"]
    queryset = LabResult.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LabResult.objects.none()
        return LabResult.objects.filter(
            lab_order_item__lab_order__facility=self.request.user.facility
        )

    def get_serializer_class(self):
        if self.action == "create":
            return EnterResultSerializer
        return LabResultSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        facility = request.user.facility
        lab_order_item = get_object_or_404(
            LabOrderItem, pk=data["lab_order_item"], lab_order__facility=facility
        )

        result = enter_result(
            lab_order_item,
            entered_by=request.user,
            values=data["values"],
            actor=request.user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(LabResultSerializer(result).data, status=201)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        result = self.get_object()
        try:
            verify_result(
                result,
                verified_by=request.user,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except SelfVerificationError as exc:
            raise drf_serializers.ValidationError(str(exc), code="self_verification")
        except AlreadyVerifiedError as exc:
            raise drf_serializers.ValidationError(str(exc), code="already_verified")
        return Response(LabResultSerializer(result).data)
