"""
Department lookup API permission boundary (TRD §4.3). Negative cases
first per CLAUDE.md §4.3.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.core.factories import DepartmentFactory, FacilityFactory

pytestmark = pytest.mark.django_db


def _user_with_permissions(facility, *codes):
    user = UserFactory(facility=facility)
    role = RoleFactory()
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code)
        RolePermissionFactory(role=role, permission=permission)
    UserRoleFactory(user=user, role=role, facility=None)
    return user


@pytest.fixture
def client():
    return APIClient()


class TestDepartmentPermissionBoundary:
    def test_unauthenticated_cannot_list(self, client):
        response = client.get(reverse("core:department-list"))
        assert response.status_code == 401

    def test_user_without_view_permission_is_denied(self, client):
        facility = FacilityFactory()
        DepartmentFactory(facility=facility)
        user = UserFactory(facility=facility)
        client.force_authenticate(user=user)

        response = client.get(reverse("core:department-list"))
        assert response.status_code == 403

    def test_user_with_view_permission_sees_only_their_facility(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        own = DepartmentFactory(facility=facility)
        DepartmentFactory(facility=other_facility)

        user = _user_with_permissions(facility, "core.department.view")
        client.force_authenticate(user=user)
        response = client.get(reverse("core:department-list"))

        assert response.status_code == 200
        returned_ids = {row["id"] for row in response.data["results"]}
        assert returned_ids == {str(own.pk)}
