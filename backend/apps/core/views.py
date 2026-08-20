"""
Read-only lookups the frontend needs for pickers (department/doctor
selects on the scheduling and booking forms) that no module actually
owns as a create/update resource of its own. Department already exists
as a model (§2) — this just exposes it for browsing, same reasoning as
apps.accounts's UserViewSet.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from apps.accounts.permissions import HasModulePermission
from apps.core.models import Department
from apps.core.serializers import DepartmentSerializer


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
