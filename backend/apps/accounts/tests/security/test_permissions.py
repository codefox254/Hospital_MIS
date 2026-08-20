"""
HasModulePermission allow/deny matrix (TRD §4.3). Negative cases first per
CLAUDE.md §4.3 — every one of these proves a role WITHOUT the permission is
rejected before proving a role with it is allowed.
"""

import pytest
from django.core.exceptions import ImproperlyConfigured
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.accounts.factories import (
    PermissionFactory,
    RoleFactory,
    RolePermissionFactory,
    UserFactory,
    UserRoleFactory,
)
from apps.accounts.permissions import HasModulePermission
from apps.core.factories import FacilityFactory

pytestmark = pytest.mark.django_db

factory = APIRequestFactory()


class DummyView:
    permission_code = "lab.result.verify"


class DummyMultiMethodView:
    permission_codes_by_method = {"GET": "lab.result.view", "POST": "lab.result.enter"}


class DummyActionView:
    """Simulates a ViewSet with a custom action sharing an HTTP method with
    a standard one — `create` and `deactivate` are both POST."""

    permission_codes_by_action = {
        "create": "patients.patient.create",
        "deactivate": "patients.patient.deactivate",
    }

    def __init__(self, action):
        self.action = action


def _request_as(user, facility=None, department=None, method="GET"):
    django_request = getattr(factory, method.lower())("/dummy/")
    request = Request(django_request)
    request.user = user
    if facility is not None:
        request.permission_facility = facility
    if department is not None:
        request.permission_department = department
    return request


class TestHasModulePermissionDenies:
    def test_user_without_the_permission_is_denied(self):
        user = UserFactory()
        UserRoleFactory(user=user, role=RoleFactory())  # role, but no matching permission

        assert HasModulePermission().has_permission(_request_as(user), DummyView()) is False

    def test_user_with_no_roles_at_all_is_denied(self):
        user = UserFactory()
        assert HasModulePermission().has_permission(_request_as(user), DummyView()) is False

    def test_permission_scoped_to_another_facility_is_denied(self):
        user = UserFactory()
        granted_facility = FacilityFactory()
        request_facility = FacilityFactory()
        permission = PermissionFactory(code="lab.result.verify")
        role_permission = RolePermissionFactory(permission=permission)
        UserRoleFactory(user=user, role=role_permission.role, facility=granted_facility)

        request = _request_as(user, facility=request_facility)
        assert HasModulePermission().has_permission(request, DummyView()) is False

    def test_inactive_user_is_denied_even_with_the_permission(self):
        user = UserFactory(is_active=False)
        permission = PermissionFactory(code="lab.result.verify")
        role_permission = RolePermissionFactory(permission=permission)
        UserRoleFactory(user=user, role=role_permission.role)

        assert HasModulePermission().has_permission(_request_as(user), DummyView()) is False

    def test_unauthenticated_request_is_denied(self):
        from django.contrib.auth.models import AnonymousUser

        request = _request_as(AnonymousUser())
        assert HasModulePermission().has_permission(request, DummyView()) is False

    def test_view_without_a_declared_permission_code_raises_configuration_error(self):
        user = UserFactory()

        class MisconfiguredView:
            http_method_names = ["get"]

        with pytest.raises(ImproperlyConfigured):
            HasModulePermission().has_permission(_request_as(user), MisconfiguredView())

    def test_unsupported_http_method_defers_to_405_instead_of_crashing(self):
        """
        Regression test: a ViewSet that deliberately excludes DELETE (e.g.
        an audited model with hard delete disabled, TRD §8.4) has no action
        mapped for it. DRF runs permission checks before it checks whether
        the method is even implemented, so this used to raise
        ImproperlyConfigured as an uncaught 500 instead of a clean 405.
        """
        user = UserFactory()

        class NoDeleteView:
            http_method_names = ["get", "post", "head", "options"]
            action = None
            permission_codes_by_action = {"list": "lab.result.view"}

        request = _request_as(user, method="DELETE")
        assert HasModulePermission().has_permission(request, NoDeleteView()) is True


class TestHasModulePermissionAllows:
    @pytest.mark.smoke
    def test_user_with_the_permission_at_their_home_facility_is_allowed(self):
        user = UserFactory()
        permission = PermissionFactory(code="lab.result.verify")
        role_permission = RolePermissionFactory(permission=permission)
        UserRoleFactory(user=user, role=role_permission.role, facility=None)

        assert HasModulePermission().has_permission(_request_as(user), DummyView()) is True

    def test_per_method_permission_codes_are_resolved_by_request_method(self):
        user = UserFactory()
        view_permission = PermissionFactory(code="lab.result.enter")
        role_permission = RolePermissionFactory(permission=view_permission)
        UserRoleFactory(user=user, role=role_permission.role, facility=None)

        request = _request_as(user, method="POST")
        assert HasModulePermission().has_permission(request, DummyMultiMethodView()) is True

    def test_per_method_permission_denies_method_the_role_lacks(self):
        user = UserFactory()
        view_permission = PermissionFactory(code="lab.result.enter")
        role_permission = RolePermissionFactory(permission=view_permission)
        UserRoleFactory(user=user, role=role_permission.role, facility=None)

        request = _request_as(user, method="GET")  # role only has .enter, not .view
        assert HasModulePermission().has_permission(request, DummyMultiMethodView()) is False

    def test_action_based_codes_distinguish_same_method_different_actions(self):
        """A custom @action sharing POST with `create` must not be gated by
        `create`'s permission code — this is the whole reason
        permission_codes_by_action exists over permission_codes_by_method."""
        user = UserFactory()
        deactivate_permission = PermissionFactory(code="patients.patient.deactivate")
        role_permission = RolePermissionFactory(permission=deactivate_permission)
        UserRoleFactory(user=user, role=role_permission.role, facility=None)

        request = _request_as(user, method="POST")
        assert HasModulePermission().has_permission(request, DummyActionView("deactivate")) is True
        assert HasModulePermission().has_permission(request, DummyActionView("create")) is False
