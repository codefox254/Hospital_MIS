"""
Audit log API permission boundary (TRD §4.3). Negative cases first per
CLAUDE.md §4.3.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import (
    PermissionFactory,
    RolePermissionFactory,
    UserFactory,
    UserRoleFactory,
)
from apps.audit.factories import AuditLogEntryFactory
from apps.audit.views import AuditLogEntryViewSet
from apps.core.factories import FacilityFactory

pytestmark = pytest.mark.django_db

LIST_URL = reverse("audit:log-entry-list")


@pytest.fixture
def client():
    return APIClient()


def _user_with_audit_view_permission(facility):
    user = UserFactory(facility=facility)
    permission = PermissionFactory(code="audit.log.view")
    role_permission = RolePermissionFactory(permission=permission)
    UserRoleFactory(user=user, role=role_permission.role, facility=None)
    return user


class TestAuditLogPermissionBoundary:
    def test_unauthenticated_request_is_denied(self, client):
        response = client.get(LIST_URL)
        assert response.status_code == 401

    def test_authenticated_user_without_permission_is_denied(self, client):
        user = UserFactory()
        client.force_authenticate(user=user)
        response = client.get(LIST_URL)
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_permission_is_allowed(self, client):
        facility = FacilityFactory()
        user = _user_with_audit_view_permission(facility)
        client.force_authenticate(user=user)
        response = client.get(LIST_URL)
        assert response.status_code == 200


class TestAuditLogFacilityScoping:
    def test_only_own_facility_entries_are_visible(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        user = _user_with_audit_view_permission(facility)

        own_entry = AuditLogEntryFactory(facility=facility)
        AuditLogEntryFactory(facility=other_facility)

        client.force_authenticate(user=user)
        response = client.get(LIST_URL)

        returned_ids = {row["id"] for row in response.data["results"]}
        assert returned_ids == {str(own_entry.pk)}

    def test_the_api_is_read_only(self, client):
        facility = FacilityFactory()
        user = _user_with_audit_view_permission(facility)
        client.force_authenticate(user=user)

        response = client.post(
            LIST_URL,
            {
                "facility": str(facility.id),
                "model_name": "core.Department",
                "record_id": "00000000-0000-0000-0000-000000000000",
                "action": "create",
            },
            format="json",
        )
        assert response.status_code == 405


class TestSchemaGenerationDoesNotCrash:
    def test_get_queryset_is_safe_without_a_real_authenticated_user(self):
        """
        Regression test: drf-spectacular introspects get_queryset() during
        schema generation using an unauthenticated request (AnonymousUser
        has no `.facility`), which previously raised AttributeError and
        broke `manage.py check --deploy` / /api/schema/.
        """
        view = AuditLogEntryViewSet()
        view.swagger_fake_view = True
        assert list(view.get_queryset()) == []
