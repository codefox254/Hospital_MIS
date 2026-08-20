"""
Patient CRUD + search/de-duplication (BRD §6.1, Solution Spec Flow 5.1).
Hard delete is disabled at the model layer (AuditableModel) and at the API
layer here — `deactivate` (soft delete) is a distinct, separately permission-
gated action, not the DELETE verb.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from apps.patients.models import Patient
from apps.patients.serializers import PatientSerializer
from apps.patients.services import register_patient


class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "patients.patient.view",
        "retrieve": "patients.patient.view",
        "create": "patients.patient.create",
        "update": "patients.patient.update",
        "partial_update": "patients.patient.update",
        "deactivate": "patients.patient.deactivate",
    }
    http_method_names = ["get", "post", "put", "patch", "head", "options"]  # no delete
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["is_provisional", "gender"]
    search_fields = ["first_name", "last_name", "mrn", "phone", "national_id"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Patient.objects.none()
        return Patient.objects.filter(facility=self.request.user.facility, deleted_at__isnull=True)

    def perform_create(self, serializer):
        patient = register_patient(
            facility=self.request.user.facility,
            actor=self.request.user,
            ip_address=self.request.META.get("REMOTE_ADDR"),
            **serializer.validated_data,
        )
        serializer.instance = patient

    def perform_update(self, serializer):
        # Deliberately not serializer.save(actor=..., ip_address=...): DRF's
        # default Serializer.save() merges kwargs into validated_data and
        # setattr()s them onto the instance before calling instance.save()
        # with no arguments — that would silently set bogus `actor`/
        # `ip_address` attributes on the model and never reach
        # AuditableModel.save()'s actual actor/ip_address parameters,
        # losing the audit trail's actor on every update.
        instance = serializer.instance
        for attr, value in serializer.validated_data.items():
            setattr(instance, attr, value)
        instance.save(actor=self.request.user, ip_address=self.request.META.get("REMOTE_ADDR"))

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        patient = self.get_object()
        patient.soft_delete(actor=request.user, ip_address=request.META.get("REMOTE_ADDR"))
        return Response(status=status.HTTP_204_NO_CONTENT)
