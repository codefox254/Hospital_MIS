"""
OPD / Clinical API (BRD §6.3; Solution Spec Flow 5.3). Starting a visit,
recording vitals, and the consultation draft/lock/addendum rules always go
through apps.opd.services — never a bare ModelViewSet.perform_create() —
so the appointment-status handoff, abnormal-vitals check, and the
never-silently-edit-a-signed-note rule stay in one place.
"""

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework import serializers as drf_serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from apps.core.models import Department
from apps.opd.models import Consultation, ConsultationAddendum, Diagnosis, Visit, Vitals
from apps.opd.serializers import (
    ConsultationAddendumSerializer,
    ConsultationSerializer,
    DiagnosisSerializer,
    StartVisitSerializer,
    VisitSerializer,
    VitalsSerializer,
)
from apps.opd.services import (
    ConsultationLockedError,
    ConsultationNotLockedError,
    InvalidVisitStartError,
    add_addendum,
    add_diagnosis,
    complete_consultation,
    record_vitals,
    start_visit,
    update_consultation_draft,
)


class VisitViewSet(viewsets.ModelViewSet):
    serializer_class = VisitSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "opd.visit.view",
        "retrieve": "opd.visit.view",
        "create": "opd.visit.create",
    }
    http_method_names = ["get", "post", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["doctor", "department", "patient", "status"]
    queryset = Visit.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Visit.objects.none()
        return Visit.objects.filter(facility=self.request.user.facility, deleted_at__isnull=True)

    def get_serializer_class(self):
        if self.action == "create":
            return StartVisitSerializer
        return VisitSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.accounts.models import User
        from apps.appointments.models import Appointment
        from apps.patients.models import Patient

        facility = request.user.facility
        patient = get_object_or_404(Patient, pk=data["patient"], facility=facility)
        doctor = get_object_or_404(User, pk=data["doctor"], facility=facility)
        department = get_object_or_404(Department, pk=data["department"], facility=facility)
        appointment = None
        if data.get("appointment"):
            appointment = get_object_or_404(Appointment, pk=data["appointment"], facility=facility)

        try:
            visit = start_visit(
                facility=facility,
                patient=patient,
                doctor=doctor,
                department=department,
                appointment=appointment,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except InvalidVisitStartError as exc:
            raise drf_serializers.ValidationError(str(exc), code="invalid_visit_start")

        output = VisitSerializer(visit)
        return Response(output.data, status=201)


class VitalsViewSet(viewsets.ModelViewSet):
    serializer_class = VitalsSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "opd.vitals.view",
        "retrieve": "opd.vitals.view",
        "create": "opd.vitals.create",
    }
    http_method_names = ["get", "post", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["visit"]
    queryset = Vitals.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Vitals.objects.none()
        return Vitals.objects.filter(visit__facility=self.request.user.facility)

    def perform_create(self, serializer):
        vitals = record_vitals(
            serializer.validated_data.pop("visit"),
            recorded_by=self.request.user,
            actor=self.request.user,
            ip_address=self.request.META.get("REMOTE_ADDR"),
            **serializer.validated_data,
        )
        serializer.instance = vitals


class ConsultationViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    No CreateModelMixin/DestroyModelMixin on purpose: a Consultation is only
    ever created alongside its Visit (apps.opd.services.start_visit) — a
    generic POST /consultations/ would let a caller create one detached
    from any visit, bypassing that invariant. `complete` is the one POST
    this ViewSet does allow, as a custom detail action.
    """

    serializer_class = ConsultationSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "opd.consultation.view",
        "retrieve": "opd.consultation.view",
        "update": "opd.consultation.update",
        "partial_update": "opd.consultation.update",
        "complete": "opd.consultation.complete",
    }
    http_method_names = ["get", "put", "patch", "post", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["visit"]
    queryset = Consultation.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Consultation.objects.none()
        return Consultation.objects.filter(visit__facility=self.request.user.facility)

    def perform_update(self, serializer):
        try:
            update_consultation_draft(
                serializer.instance,
                actor=self.request.user,
                ip_address=self.request.META.get("REMOTE_ADDR"),
                **serializer.validated_data,
            )
        except ConsultationLockedError as exc:
            raise drf_serializers.ValidationError(str(exc), code="consultation_locked")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        consultation = self.get_object()
        try:
            complete_consultation(
                consultation, actor=request.user, ip_address=request.META.get("REMOTE_ADDR")
            )
        except ConsultationLockedError as exc:
            raise drf_serializers.ValidationError(str(exc), code="consultation_locked")
        return Response(ConsultationSerializer(consultation).data)


class DiagnosisViewSet(viewsets.ModelViewSet):
    serializer_class = DiagnosisSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "opd.diagnosis.view",
        "retrieve": "opd.diagnosis.view",
        "create": "opd.diagnosis.create",
    }
    http_method_names = ["get", "post", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["consultation"]
    queryset = Diagnosis.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Diagnosis.objects.none()
        return Diagnosis.objects.filter(consultation__visit__facility=self.request.user.facility)

    def perform_create(self, serializer):
        try:
            diagnosis = add_diagnosis(
                serializer.validated_data.pop("consultation"),
                actor=self.request.user,
                ip_address=self.request.META.get("REMOTE_ADDR"),
                **serializer.validated_data,
            )
        except ConsultationLockedError as exc:
            raise drf_serializers.ValidationError(str(exc), code="consultation_locked")
        serializer.instance = diagnosis


class ConsultationAddendumViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultationAddendumSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "opd.addendum.view",
        "retrieve": "opd.addendum.view",
        "create": "opd.addendum.create",
    }
    http_method_names = ["get", "post", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["consultation"]
    queryset = ConsultationAddendum.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ConsultationAddendum.objects.none()
        return ConsultationAddendum.objects.filter(
            consultation__visit__facility=self.request.user.facility
        )

    def perform_create(self, serializer):
        try:
            addendum = add_addendum(
                serializer.validated_data.pop("consultation"),
                author=self.request.user,
                actor=self.request.user,
                ip_address=self.request.META.get("REMOTE_ADDR"),
                **serializer.validated_data,
            )
        except ConsultationNotLockedError as exc:
            raise drf_serializers.ValidationError(str(exc), code="consultation_not_locked")
        serializer.instance = addendum
