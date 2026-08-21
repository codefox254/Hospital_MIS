"""
Read-only lookups the frontend needs for pickers (department/doctor
selects on the scheduling and booking forms) that no module actually
owns as a create/update resource of its own. Department already exists
as a model (§2) — this just exposes it for browsing, same reasoning as
apps.accounts's UserViewSet.

FacilityViewSet and PlatformStatsView are different in kind: Facility
*is* the tenant record in this system's SaaS model (one hospital = one
Facility row), so managing it and viewing cross-tenant stats are
deliberately NOT facility-scoped — the one legitimate place a query
spans every facility. Restricted to Super Admin via core.facility.*
permission codes (seed_rbac.py).
"""

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasModulePermission
from apps.core.models import Department, Facility
from apps.core.serializers import DepartmentSerializer, FacilitySerializer


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [HasModulePermission]
    permission_code = "core.department.view"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["parent_department"]
    queryset = Department.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Department.objects.none()
        return Department.objects.filter(
            facility=self.request.user.facility, deleted_at__isnull=True
        )


class FacilityViewSet(viewsets.ModelViewSet):
    serializer_class = FacilitySerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "core.facility.view",
        "retrieve": "core.facility.view",
        "create": "core.facility.create",
        "update": "core.facility.update",
        "partial_update": "core.facility.update",
        "deactivate": "core.facility.deactivate",
    }
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    queryset = Facility.objects.all()

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        facility = self.get_object()
        facility.is_active = False
        facility.save()
        return Response(FacilitySerializer(facility).data)


class PlatformStatsView(APIView):
    """Super Admin's cross-facility dashboard — aggregate counts only,
    never patient-level or clinical data, matching the SaaS admin model's
    boundary (Super Admin manages tenants, not their clinical records)."""

    permission_classes = [HasModulePermission]
    permission_code = "core.facility.view"

    def get(self, request):
        from apps.accounts.models import User
        from apps.appointments.models import Appointment
        from apps.patients.models import Patient

        today = timezone.now().date()
        stats = []
        for facility in Facility.objects.all():
            stats.append(
                {
                    "id": str(facility.id),
                    "name": facility.name,
                    "code": facility.code,
                    "type": facility.type,
                    "is_active": facility.is_active,
                    "patient_count": Patient.objects.filter(
                        facility=facility, deleted_at__isnull=True
                    ).count(),
                    "active_user_count": User.objects.filter(
                        facility=facility, is_active=True
                    ).count(),
                    "appointments_today": Appointment.objects.filter(
                        facility=facility,
                        scheduled_at__date=today,
                        deleted_at__isnull=True,
                    ).count(),
                }
            )
        return Response(stats)
