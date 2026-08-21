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


class TestFacilityPermissionBoundary:
    """Facility is the tenant record — its ViewSet is deliberately the one
    unscoped queryset in the codebase, restricted to Super Admin via
    core.facility.* rather than via facility-filtering. Negative cases
    first."""

    def test_unauthenticated_cannot_list(self, client):
        response = client.get(reverse("core:facility-list"))
        assert response.status_code == 401

    def test_facility_scoped_admin_without_platform_permission_is_denied(self, client):
        facility = FacilityFactory()
        # Holds ordinary facility-scoped permissions but not core.facility.*
        user = _user_with_permissions(facility, "core.department.view")
        client.force_authenticate(user=user)

        response = client.get(reverse("core:facility-list"))
        assert response.status_code == 403

    def test_super_admin_sees_every_facility_not_just_their_own(self, client):
        home_facility = FacilityFactory()
        other_facility = FacilityFactory()
        super_admin = _user_with_permissions(home_facility, "core.facility.view")
        client.force_authenticate(user=super_admin)

        response = client.get(reverse("core:facility-list"))

        assert response.status_code == 200
        returned_ids = {row["id"] for row in response.data["results"]}
        assert str(home_facility.pk) in returned_ids
        assert str(other_facility.pk) in returned_ids

    def test_super_admin_can_create_a_facility(self, client):
        facility = FacilityFactory()
        super_admin = _user_with_permissions(facility, "core.facility.create")
        client.force_authenticate(user=super_admin)

        response = client.post(
            reverse("core:facility-list"),
            {"name": "New Hospital", "code": "NEWHOSP", "type": "hospital"},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["is_active"] is True

    def test_deactivate_requires_its_own_permission(self, client):
        facility = FacilityFactory()
        target = FacilityFactory()
        # Holds view+create but not deactivate specifically.
        user = _user_with_permissions(facility, "core.facility.view", "core.facility.create")
        client.force_authenticate(user=user)

        response = client.post(reverse("core:facility-deactivate", args=[target.pk]))
        assert response.status_code == 403

    def test_deactivate_flips_is_active_false(self, client):
        facility = FacilityFactory()
        target = FacilityFactory(is_active=True)
        super_admin = _user_with_permissions(facility, "core.facility.deactivate")
        client.force_authenticate(user=super_admin)

        response = client.post(reverse("core:facility-deactivate", args=[target.pk]))

        assert response.status_code == 200
        target.refresh_from_db()
        assert target.is_active is False


class TestPlatformStatsPermissionBoundary:
    def test_unauthenticated_cannot_view(self, client):
        response = client.get(reverse("core:platform-stats"))
        assert response.status_code == 401

    def test_facility_scoped_user_is_denied(self, client):
        facility = FacilityFactory()
        user = _user_with_permissions(facility, "core.department.view")
        client.force_authenticate(user=user)

        response = client.get(reverse("core:platform-stats"))
        assert response.status_code == 403

    def test_super_admin_sees_stats_for_every_facility(self, client):
        facility_a = FacilityFactory()
        facility_b = FacilityFactory()
        super_admin = _user_with_permissions(facility_a, "core.facility.view")
        client.force_authenticate(user=super_admin)

        response = client.get(reverse("core:platform-stats"))

        assert response.status_code == 200
        returned_ids = {row["id"] for row in response.data}
        assert str(facility_a.pk) in returned_ids
        assert str(facility_b.pk) in returned_ids
