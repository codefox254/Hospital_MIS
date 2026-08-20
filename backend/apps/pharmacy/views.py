"""
Pharmacy API (BRD §6.8; Solution Spec Flow 5.6). Prescribing and
dispensing always go through apps.pharmacy.services — never a bare
ModelViewSet.perform_create() — so the transactional stock decrement and
the controlled-substance permission gate stay in one place.
"""

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework import serializers as drf_serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from apps.accounts.services import user_has_permission
from apps.pharmacy.models import DispenseRecord, Drug, Prescription, PrescriptionItem, StockBatch
from apps.pharmacy.serializers import (
    CreatePrescriptionSerializer,
    DispenseRecordSerializer,
    DispenseSerializer,
    DrugSerializer,
    PrescriptionItemSerializer,
    PrescriptionSerializer,
    StockBatchSerializer,
)
from apps.pharmacy.services import (
    InsufficientStockError,
    OverDispenseError,
    WrongDrugForBatchError,
    check_patient_allergies,
    create_prescription,
    dispense_medication,
)


class DrugViewSet(viewsets.ModelViewSet):
    """Global reference catalog — no facility scoping (Drug has no facility_id)."""

    serializer_class = DrugSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "pharmacy.drug.view",
        "retrieve": "pharmacy.drug.view",
        "create": "pharmacy.drug.create",
        "update": "pharmacy.drug.update",
        "partial_update": "pharmacy.drug.update",
    }
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_controlled"]
    queryset = Drug.objects.all()


class StockBatchViewSet(viewsets.ModelViewSet):
    serializer_class = StockBatchSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "pharmacy.stock_batch.view",
        "retrieve": "pharmacy.stock_batch.view",
        "create": "pharmacy.stock_batch.create",
        "update": "pharmacy.stock_batch.update",
        "partial_update": "pharmacy.stock_batch.update",
        "allergy_check": "pharmacy.stock_batch.view",
    }
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["drug"]
    queryset = StockBatch.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return StockBatch.objects.none()
        return StockBatch.objects.filter(
            facility=self.request.user.facility, deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        instance = StockBatch(facility=self.request.user.facility, **serializer.validated_data)
        instance.save(actor=self.request.user, ip_address=self.request.META.get("REMOTE_ADDR"))
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = serializer.instance
        for attr, value in serializer.validated_data.items():
            setattr(instance, attr, value)
        instance.save(actor=self.request.user, ip_address=self.request.META.get("REMOTE_ADDR"))

    @action(detail=False, methods=["get"])
    def allergy_check(self, request):
        """
        GET /stock/allergy_check/?patient=<uuid>&drug=<uuid> — Solution Spec
        Flow 5.6 step 2's "cross-referenced with patient allergy data",
        surfaced as a flag for the pharmacist, never a hard block.
        """
        from apps.patients.models import Patient

        patient = get_object_or_404(
            Patient, pk=request.query_params.get("patient"), facility=request.user.facility
        )
        drug = get_object_or_404(Drug, pk=request.query_params.get("drug"))
        conflicts = check_patient_allergies(patient, drug)
        return Response(
            {"conflicts": [{"substance": c.substance, "reaction": c.reaction} for c in conflicts]}
        )


class PrescriptionViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PrescriptionSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "pharmacy.prescription.view",
        "retrieve": "pharmacy.prescription.view",
        "create": "pharmacy.prescription.create",
        "cancel": "pharmacy.prescription.cancel",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["patient", "consultation", "status"]
    queryset = Prescription.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Prescription.objects.none()
        return Prescription.objects.filter(
            consultation__visit__facility=self.request.user.facility, deleted_at__isnull=True
        )

    def get_serializer_class(self):
        if self.action == "create":
            return CreatePrescriptionSerializer
        return PrescriptionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.opd.models import Consultation

        facility = request.user.facility
        consultation = get_object_or_404(
            Consultation, pk=data["consultation"], visit__facility=facility
        )

        items = []
        for item in data["items"]:
            drug = get_object_or_404(Drug, pk=item.pop("drug"))
            items.append({"drug": drug, **item})

        prescription = create_prescription(
            consultation=consultation,
            patient=consultation.visit.patient,
            prescribed_by=request.user,
            items=items,
            actor=request.user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(PrescriptionSerializer(prescription).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        prescription = self.get_object()
        if prescription.status != Prescription.Status.PENDING:
            raise drf_serializers.ValidationError(
                f"Cannot cancel a prescription with status={prescription.status!r}.",
                code="cannot_cancel",
            )
        prescription.status = Prescription.Status.CANCELLED
        prescription.save(actor=request.user, ip_address=request.META.get("REMOTE_ADDR"))
        return Response(PrescriptionSerializer(prescription).data)


class PrescriptionItemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PrescriptionItemSerializer
    permission_classes = [HasModulePermission]
    permission_code = "pharmacy.prescription.view"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["prescription"]
    queryset = PrescriptionItem.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PrescriptionItem.objects.none()
        return PrescriptionItem.objects.filter(
            prescription__consultation__visit__facility=self.request.user.facility
        )


class DispenseRecordViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DispenseRecordSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "pharmacy.dispense_record.view",
        "retrieve": "pharmacy.dispense_record.view",
        "create": "pharmacy.dispense_record.create",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["prescription_item", "batch"]
    queryset = DispenseRecord.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return DispenseRecord.objects.none()
        return DispenseRecord.objects.filter(
            prescription_item__prescription__consultation__visit__facility=(
                self.request.user.facility
            )
        )

    def get_serializer_class(self):
        if self.action == "create":
            return DispenseSerializer
        return DispenseRecordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        facility = request.user.facility
        prescription_item = get_object_or_404(
            PrescriptionItem,
            pk=data["prescription_item"],
            prescription__consultation__visit__facility=facility,
        )
        batch = get_object_or_404(StockBatch, pk=data["batch"], facility=facility)

        if prescription_item.drug.is_controlled and not user_has_permission(
            request.user, "pharmacy.dispense_record.create_controlled"
        ):
            raise PermissionDenied(
                "Dispensing a controlled substance requires elevated permission."
            )

        try:
            record = dispense_medication(
                prescription_item,
                batch=batch,
                dispensed_by=request.user,
                qty_dispensed=data["qty_dispensed"],
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except WrongDrugForBatchError as exc:
            raise drf_serializers.ValidationError(str(exc), code="wrong_drug_for_batch")
        except OverDispenseError as exc:
            raise drf_serializers.ValidationError(str(exc), code="over_dispense")
        except InsufficientStockError as exc:
            raise drf_serializers.ValidationError(str(exc), code="insufficient_stock")

        return Response(DispenseRecordSerializer(record).data, status=201)
