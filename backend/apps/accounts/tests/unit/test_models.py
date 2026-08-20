import pytest
from django.db import IntegrityError, transaction

from apps.accounts.factories import (
    PermissionFactory,
    RoleFactory,
    RolePermissionFactory,
    UserFactory,
    UserRoleFactory,
)
from apps.accounts.models import User
from apps.core.factories import DepartmentFactory, FacilityFactory

pytestmark = pytest.mark.django_db


class TestUser:
    def test_email_must_be_unique(self):
        UserFactory(email="dup@fdo-hospital.test")
        with pytest.raises(IntegrityError), transaction.atomic():
            UserFactory(email="dup@fdo-hospital.test")

    def test_phone_must_be_unique_when_set(self):
        UserFactory(phone="+254700000001")
        with pytest.raises(IntegrityError), transaction.atomic():
            UserFactory(phone="+254700000001")

    def test_password_is_hashed_never_plaintext(self):
        user = UserFactory(password="MyActualSecret123!")
        assert user.password != "MyActualSecret123!"
        assert user.password.startswith("argon2$")
        assert user.check_password("MyActualSecret123!")

    def test_is_active_defaults_true(self):
        user = UserFactory()
        assert user.is_active is True

    @pytest.mark.smoke
    def test_termination_sets_is_active_false(self):
        """
        BRD edge case (cited in the Data Dictionary's User table): terminating
        a staff member must revoke access immediately. Full enforcement (JWT
        auth rejecting an inactive user) is exercised in the auth-engine
        milestone's tests; this proves the model-level state change works.
        """
        user = UserFactory()
        user.is_active = False
        user.save(update_fields=["is_active"])
        user.refresh_from_db()
        assert user.is_active is False

    def test_user_scoped_to_home_facility(self):
        facility = FacilityFactory()
        user = UserFactory(facility=facility)
        assert user.facility_id == facility.id

    def test_get_full_name_falls_back_to_email(self):
        user = UserFactory(first_name="", last_name="", email="noname@fdo-hospital.test")
        assert user.get_full_name() == "noname@fdo-hospital.test"

    def test_non_superuser_has_no_django_admin_perms(self):
        user = UserFactory()
        assert user.has_perm("any.permission") is False
        assert user.has_module_perms("any_app") is False


class TestRolePermissionEngine:
    def test_role_permission_pair_must_be_unique(self):
        role = RoleFactory()
        permission = PermissionFactory()
        RolePermissionFactory(role=role, permission=permission)
        with pytest.raises(IntegrityError), transaction.atomic():
            RolePermissionFactory(role=role, permission=permission)

    def test_permission_code_must_be_unique(self):
        PermissionFactory(code="lab.result.verify")
        with pytest.raises(IntegrityError), transaction.atomic():
            PermissionFactory(code="lab.result.verify")

    def test_role_exposes_its_permissions_via_m2m(self):
        role = RoleFactory()
        permission = PermissionFactory(code="lab.result.verify")
        RolePermissionFactory(role=role, permission=permission)
        assert permission in role.permissions.all()

    def test_user_role_can_be_scoped_to_facility_and_department(self):
        facility = FacilityFactory()
        department = DepartmentFactory(facility=facility)
        user_role = UserRoleFactory(facility=facility, department=department)
        assert user_role.facility == facility
        assert user_role.department == department

    def test_user_role_unscoped_grant_allows_null_facility_and_department(self):
        user_role = UserRoleFactory(facility=None, department=None)
        assert user_role.facility is None
        assert user_role.department is None

    def test_duplicate_identical_scope_grant_is_rejected(self):
        user = UserFactory()
        role = RoleFactory()
        facility = FacilityFactory()
        UserRoleFactory(user=user, role=role, facility=facility, department=None)
        with pytest.raises(IntegrityError), transaction.atomic():
            UserRoleFactory(user=user, role=role, facility=facility, department=None)

    def test_user_can_hold_multiple_roles(self):
        user = UserFactory()
        role_a = RoleFactory()
        role_b = RoleFactory()
        UserRoleFactory(user=user, role=role_a)
        UserRoleFactory(user=user, role=role_b)
        assert User.objects.get(pk=user.pk).user_roles.count() == 2
