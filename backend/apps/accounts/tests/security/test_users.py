"""
Staff-picker lookup API permission boundary (TRD §4.3). Negative cases
first per CLAUDE.md §4.3.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission, Role, User, UserRole
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


class TestUserCreate:
    """Admin-onboarding path (Facility Admin adding staff, or Super Admin
    onboarding a new facility's first admin). Negative cases first."""

    def test_unauthenticated_cannot_create(self, client):
        response = client.post(
            reverse("accounts:user-list"),
            {"email": "new@example.com", "password": "a-strong-password-123", "first_name": "A"},
        )
        assert response.status_code == 401

    def test_user_without_create_permission_is_denied(self, client):
        facility = FacilityFactory()
        user = UserFactory(facility=facility)
        client.force_authenticate(user=user)

        response = client.post(
            reverse("accounts:user-list"),
            {"email": "new@example.com", "password": "a-strong-password-123", "first_name": "A"},
        )
        assert response.status_code == 403

    def test_facility_admin_cannot_place_new_user_in_another_facility(self, client):
        """The core scoping guarantee: a non-platform-admin's `facility`
        field in the payload must be silently overridden, never trusted —
        otherwise any Facility Admin could plant a user in a facility they
        don't manage."""
        own_facility = FacilityFactory()
        other_facility = FacilityFactory()
        creator = _user_with_permissions(own_facility, "accounts.user.create")
        client.force_authenticate(user=creator)

        response = client.post(
            reverse("accounts:user-list"),
            {
                "email": "new-staff@example.com",
                "password": "a-strong-password-123",
                "first_name": "New",
                "last_name": "Staff",
                "facility": str(other_facility.pk),
            },
        )

        assert response.status_code == 201
        created = User.objects.get(email="new-staff@example.com")
        assert created.facility_id == own_facility.pk

    def test_super_admin_must_supply_a_facility(self, client):
        facility = FacilityFactory()
        super_admin = _user_with_permissions(
            facility, "accounts.user.create", "core.facility.create"
        )
        client.force_authenticate(user=super_admin)

        response = client.post(
            reverse("accounts:user-list"),
            {
                "email": "no-facility@example.com",
                "password": "a-strong-password-123",
                "first_name": "No",
                "last_name": "Facility",
            },
        )

        assert response.status_code == 400
        assert "facility" in response.data["error"]["fields"]

    def test_super_admin_can_place_a_new_facility_admin_in_any_facility(self, client):
        home_facility = FacilityFactory()
        new_hospital = FacilityFactory()
        super_admin = _user_with_permissions(
            home_facility, "accounts.user.create", "core.facility.create"
        )
        admin_role, _ = Role.objects.get_or_create(name="Administrator")
        client.force_authenticate(user=super_admin)

        response = client.post(
            reverse("accounts:user-list"),
            {
                "email": "hospital-admin@example.com",
                "password": "a-strong-password-123",
                "first_name": "Hospital",
                "last_name": "Admin",
                "facility": str(new_hospital.pk),
                "role": admin_role.name,
            },
        )

        assert response.status_code == 201
        created = User.objects.get(email="hospital-admin@example.com")
        assert created.facility_id == new_hospital.pk
        grant = UserRole.objects.get(user=created, role=admin_role)
        assert grant.facility_id == new_hospital.pk

    def test_granting_the_super_admin_role_is_always_unscoped(self):
        """A Super Admin's own permission grant must be platform-wide
        regardless of the account's home facility — otherwise it silently
        degrades into an ordinary facility-scoped admin the moment
        get_effective_permission_codes checks a different facility."""
        from apps.accounts.services import create_user_with_role

        facility = FacilityFactory()
        super_admin_role, _ = Role.objects.get_or_create(name="Super Admin")

        user = create_user_with_role(
            email="platform-owner@example.com",
            password="a-strong-password-123",
            first_name="Platform",
            last_name="Owner",
            facility=facility,
            role=super_admin_role,
        )

        grant = UserRole.objects.get(user=user, role=super_admin_role)
        assert grant.facility_id is None

    def test_weak_password_is_rejected(self, client):
        facility = FacilityFactory()
        creator = _user_with_permissions(facility, "accounts.user.create")
        client.force_authenticate(user=creator)

        response = client.post(
            reverse("accounts:user-list"),
            {"email": "weak@example.com", "password": "short", "first_name": "Weak"},
        )

        assert response.status_code == 400
        assert "password" in response.data["error"]["fields"]
