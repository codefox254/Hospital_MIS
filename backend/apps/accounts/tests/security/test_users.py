"""
Staff-picker lookup API permission boundary (TRD §4.3). Negative cases
first per CLAUDE.md §4.3.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.core.factories import FacilityFactory

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


class TestUserPermissionBoundary:
    def test_unauthenticated_cannot_list(self, client):
        response = client.get(reverse("accounts:user-list"))
        assert response.status_code == 401

    def test_user_without_view_permission_is_denied(self, client):
        facility = FacilityFactory()
        user = UserFactory(facility=facility)
        client.force_authenticate(user=user)

        response = client.get(reverse("accounts:user-list"))
        assert response.status_code == 403

    def test_user_with_view_permission_sees_only_their_facility(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        own = UserFactory(facility=facility)
        UserFactory(facility=other_facility)

        viewer = _user_with_permissions(facility, "accounts.user.view")
        client.force_authenticate(user=viewer)
        response = client.get(reverse("accounts:user-list"))

        assert response.status_code == 200
        returned_ids = {row["id"] for row in response.data["results"]}
        assert str(own.pk) in returned_ids
        assert not any(row["id"] == str(other_facility.pk) for row in response.data["results"])

    def test_inactive_users_are_not_listed(self, client):
        facility = FacilityFactory()
        UserFactory(facility=facility, is_active=False)

        viewer = _user_with_permissions(facility, "accounts.user.view")
        client.force_authenticate(user=viewer)
        response = client.get(reverse("accounts:user-list"))

        # Only the viewer themself (active) should show up.
        returned_ids = {row["id"] for row in response.data["results"]}
        assert returned_ids == {str(viewer.pk)}
