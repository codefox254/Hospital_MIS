from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.factories import (
    BreakGlassGrantFactory,
    PermissionFactory,
    RolePermissionFactory,
    UserFactory,
    UserRoleFactory,
)
from apps.accounts.services import get_effective_permission_codes, user_has_permission
from apps.core.factories import DepartmentFactory, FacilityFactory

pytestmark = pytest.mark.django_db


class TestGetEffectivePermissionCodes:
    def test_unscoped_grant_applies_at_users_home_facility(self):
        user = UserFactory()
        permission = PermissionFactory(code="lab.result.enter")
        role_permission = RolePermissionFactory(permission=permission)
        UserRoleFactory(user=user, role=role_permission.role, facility=None, department=None)

        assert "lab.result.enter" in get_effective_permission_codes(user)

    def test_facility_scoped_grant_does_not_apply_elsewhere(self):
        user = UserFactory()
        granted_facility = FacilityFactory()
        other_facility = FacilityFactory()
        permission = PermissionFactory(code="lab.result.enter")
        role_permission = RolePermissionFactory(permission=permission)
        UserRoleFactory(
            user=user, role=role_permission.role, facility=granted_facility, department=None
        )

        assert user_has_permission(user, "lab.result.enter", facility=granted_facility)
        assert not user_has_permission(user, "lab.result.enter", facility=other_facility)

    def test_department_scoped_grant_requires_matching_department(self):
        user = UserFactory()
        facility = FacilityFactory()
        department = DepartmentFactory(facility=facility)
        other_department = DepartmentFactory(facility=facility)
        permission = PermissionFactory(code="lab.result.verify")
        role_permission = RolePermissionFactory(permission=permission)
        UserRoleFactory(
            user=user, role=role_permission.role, facility=facility, department=department
        )

        assert user_has_permission(
            user, "lab.result.verify", facility=facility, department=department
        )
        assert not user_has_permission(
            user, "lab.result.verify", facility=facility, department=other_department
        )
        assert not user_has_permission(user, "lab.result.verify", facility=facility)

    def test_facility_wide_grant_applies_to_any_department_in_that_facility(self):
        user = UserFactory()
        facility = FacilityFactory()
        department = DepartmentFactory(facility=facility)
        permission = PermissionFactory(code="lab.result.verify")
        role_permission = RolePermissionFactory(permission=permission)
        UserRoleFactory(user=user, role=role_permission.role, facility=facility, department=None)

        assert user_has_permission(
            user, "lab.result.verify", facility=facility, department=department
        )

    def test_inactive_user_has_no_permissions(self):
        user = UserFactory(is_active=False)
        permission = PermissionFactory(code="lab.result.enter")
        role_permission = RolePermissionFactory(permission=permission)
        UserRoleFactory(user=user, role=role_permission.role)

        assert get_effective_permission_codes(user) == set()

    def test_user_with_no_roles_has_no_permissions(self):
        user = UserFactory()
        assert get_effective_permission_codes(user) == set()


class TestBreakGlassIntegration:
    def test_active_break_glass_grant_adds_its_permission(self):
        user = UserFactory()
        facility = FacilityFactory()
        permission = PermissionFactory(code="billing.refund.approve")
        BreakGlassGrantFactory(user=user, facility=facility, permission=permission)

        assert user_has_permission(user, "billing.refund.approve", facility=facility)

    def test_expired_break_glass_grant_does_not_apply(self):
        user = UserFactory()
        facility = FacilityFactory()
        permission = PermissionFactory(code="billing.refund.approve")
        BreakGlassGrantFactory(
            user=user,
            facility=facility,
            permission=permission,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        assert not user_has_permission(user, "billing.refund.approve", facility=facility)

    def test_revoked_break_glass_grant_does_not_apply(self):
        user = UserFactory()
        facility = FacilityFactory()
        permission = PermissionFactory(code="billing.refund.approve")
        BreakGlassGrantFactory(
            user=user, facility=facility, permission=permission, revoked_at=timezone.now()
        )

        assert not user_has_permission(user, "billing.refund.approve", facility=facility)

    def test_break_glass_grant_does_not_apply_at_a_different_facility(self):
        user = UserFactory()
        granted_facility = FacilityFactory()
        other_facility = FacilityFactory()
        permission = PermissionFactory(code="billing.refund.approve")
        BreakGlassGrantFactory(user=user, facility=granted_facility, permission=permission)

        assert not user_has_permission(user, "billing.refund.approve", facility=other_facility)
