"""
Patient CRUD + search/de-duplication (BRD §6.1, Solution Spec Flow 5.1), plus
the six related-entity endpoints (Guardian, EmergencyContact, Allergy,
ChronicCondition, Consent, PatientInsurance — Data Dictionary §3). Hard
delete is disabled at the model layer (AuditableModel) and at the API layer
here — `deactivate` (soft delete) is a distinct, separately permission-gated
action, not the DELETE verb, everywhere in this module.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from apps.patients.models import (
    Allergy,
    ChronicCondition,
    Consent,
    EmergencyContact,
    Guardian,
    Patient,
    PatientInsurance,
)
from apps.patients.serializers import (
    AllergySerializer,
    ChronicConditionSerializer,
    ConsentSerializer,
    EmergencyContactSerializer,
    GuardianSerializer,
    PatientInsuranceSerializer,
    PatientSerializer,
)
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


def _crud_permission_codes(resource):
    return {
        "list": f"patients.{resource}.view",
        "retrieve": f"patients.{resource}.view",
        "create": f"patients.{resource}.create",
        "update": f"patients.{resource}.update",
        "partial_update": f"patients.{resource}.update",
        "deactivate": f"patients.{resource}.deactivate",
    }


class PatientScopedModelViewSet(viewsets.ModelViewSet):
    """
    Shared plumbing for every Patient related-entity endpoint: scoped to the
    parent patient's facility (these child models carry no facility_id of
    their own — Data Dictionary §3), hard delete disabled, `deactivate`
    (soft delete) in its place, and the same actor/ip_address-preserving
    save() pattern as PatientViewSet — never DRF's default
    serializer.save(**kwargs), which would silently lose the audit actor.
    """

    permission_classes = [HasModulePermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["patient"]

    def get_queryset(self):
        model = self.serializer_class.Meta.model
        if getattr(self, "swagger_fake_view", False):
            return model.objects.none()
        return model.objects.filter(
            patient__facility=self.request.user.facility, deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        model = self.serializer_class.Meta.model
        instance = model(**serializer.validated_data)
        instance.save(actor=self.request.user, ip_address=self.request.META.get("REMOTE_ADDR"))
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = serializer.instance
        for attr, value in serializer.validated_data.items():
            setattr(instance, attr, value)
        instance.save(actor=self.request.user, ip_address=self.request.META.get("REMOTE_ADDR"))

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        instance = self.get_object()
        instance.soft_delete(actor=request.user, ip_address=request.META.get("REMOTE_ADDR"))
        return Response(status=status.HTTP_204_NO_CONTENT)


class GuardianViewSet(PatientScopedModelViewSet):
    serializer_class = GuardianSerializer
    queryset = Guardian.objects.none()
    permission_codes_by_action = _crud_permission_codes("guardian")


class EmergencyContactViewSet(PatientScopedModelViewSet):
    serializer_class = EmergencyContactSerializer
    queryset = EmergencyContact.objects.none()
    permission_codes_by_action = _crud_permission_codes("emergency_contact")


class AllergyViewSet(PatientScopedModelViewSet):
    serializer_class = AllergySerializer
    queryset = Allergy.objects.none()
    permission_codes_by_action = _crud_permission_codes("allergy")


class ChronicConditionViewSet(PatientScopedModelViewSet):
    serializer_class = ChronicConditionSerializer
    queryset = ChronicCondition.objects.none()
    permission_codes_by_action = _crud_permission_codes("chronic_condition")


class ConsentViewSet(PatientScopedModelViewSet):
    serializer_class = ConsentSerializer
    queryset = Consent.objects.none()
    permission_codes_by_action = _crud_permission_codes("consent")


class PatientInsuranceViewSet(PatientScopedModelViewSet):
    serializer_class = PatientInsuranceSerializer
    queryset = PatientInsurance.objects.none()
    permission_codes_by_action = _crud_permission_codes("insurance")
