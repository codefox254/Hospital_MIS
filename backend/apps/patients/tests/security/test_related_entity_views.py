"""
Permission boundary + facility isolation for the six patient related-entity
endpoints (Guardian, EmergencyContact, Allergy, ChronicCondition, Consent,
PatientInsurance). Parametrized across all six rather than duplicated six
times — same shared PatientScopedModelViewSet plumbing, same contract to
prove for each. Negative cases first per CLAUDE.md §4.3.
"""

from datetime import date

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.core.factories import FacilityFactory
from apps.patients.factories import PatientFactory

pytestmark = pytest.mark.django_db

RESOURCES = [
    {
        "basename": "guardian",
        "permission_resource": "guardian",
        "create_payload": lambda patient: {
            "patient": str(patient.pk),
            "name": "Mary Wanjiru",
            "relationship": "Mother",
            "phone": "+254700000000",
        },
    },
    {
        "basename": "emergency-contact",
        "permission_resource": "emergency_contact",
        "create_payload": lambda patient: {
            "patient": str(patient.pk),
            "name": "John Doe",
            "phone": "+254700000001",
        },
    },
    {
        "basename": "allergy",
        "permission_resource": "allergy",
        "create_payload": lambda patient: {
            "patient": str(patient.pk),
            "substance": "Penicillin",
            "severity": "severe",
        },
    },
    {
        "basename": "chronic-condition",
        "permission_resource": "chronic_condition",
        "create_payload": lambda patient: {
            "patient": str(patient.pk),
            "condition": "Hypertension",
            "diagnosed_date": str(date(2020, 1, 1)),
        },
    },
    {
        "basename": "consent",
        "permission_resource": "consent",
        "create_payload": lambda patient: {
            "patient": str(patient.pk),
            "type": "treatment",
            "granted_at": timezone.now().isoformat(),
        },
    },
    {
        "basename": "insurance-policy",
        "permission_resource": "insurance",
        "create_payload": lambda patient: {
            "patient": str(patient.pk),
            "insurer_name": "NHIF",
            "policy_number": "POL123",
            "is_primary": True,
        },
    },
]


def _list_url(basename):
    return reverse(f"patients:{basename}-list")


def _detail_url(basename, pk):
    return reverse(f"patients:{basename}-detail", args=[pk])


def _deactivate_url(basename, pk):
    return reverse(f"patients:{basename}-deactivate", args=[pk])


def _user_with_permissions(facility, *codes):
    """
    get_or_create, not PermissionFactory(code=code): several tests below
    need the *same* permission code granted to two different users (e.g.
    one per facility for isolation checks) — Permission.code is a global
    unique catalogue entry, not a per-call fixture, so a second .create()
    with the same code would violate the DB's own uniqueness constraint.
    """
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


@pytest.mark.parametrize("resource", RESOURCES, ids=lambda r: r["basename"])
class TestRelatedEntityPermissionBoundary:
    def test_unauthenticated_request_is_denied(self, client, resource):
        response = client.get(_list_url(resource["basename"]))
        assert response.status_code == 401

    def test_user_without_view_permission_cannot_list(self, client, resource):
        user = UserFactory()
        client.force_authenticate(user=user)
        response = client.get(_list_url(resource["basename"]))
        assert response.status_code == 403

    def test_user_without_create_permission_cannot_create(self, client, resource):
        facility = FacilityFactory()
        patient = PatientFactory(facility=facility)
        user = _user_with_permissions(facility, f"patients.{resource['permission_resource']}.view")
        client.force_authenticate(user=user)

        response = client.post(
            _list_url(resource["basename"]),
            resource["create_payload"](patient),
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_create(self, client, resource):
        facility = FacilityFactory()
        patient = PatientFactory(facility=facility)
        user = _user_with_permissions(
            facility, f"patients.{resource['permission_resource']}.create"
        )
        client.force_authenticate(user=user)

        response = client.post(
            _list_url(resource["basename"]),
            resource["create_payload"](patient),
            format="json",
        )
        assert response.status_code == 201

    def test_delete_verb_is_not_allowed(self, client, resource):
        facility = FacilityFactory()
        patient = PatientFactory(facility=facility)
        user = _user_with_permissions(
            facility,
            f"patients.{resource['permission_resource']}.view",
            f"patients.{resource['permission_resource']}.create",
        )
        client.force_authenticate(user=user)
        created = client.post(
            _list_url(resource["basename"]),
            resource["create_payload"](patient),
            format="json",
        )
        response = client.delete(_detail_url(resource["basename"], created.data["id"]))
        assert response.status_code == 405


@pytest.mark.parametrize("resource", RESOURCES, ids=lambda r: r["basename"])
class TestRelatedEntityFacilityIsolation:
    def test_records_from_another_facility_are_not_listed(self, client, resource):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        own_patient = PatientFactory(facility=facility)
        other_patient = PatientFactory(facility=other_facility)

        creator = _user_with_permissions(
            facility, f"patients.{resource['permission_resource']}.create"
        )
        client.force_authenticate(user=creator)
        own_record = client.post(
            _list_url(resource["basename"]),
            resource["create_payload"](own_patient),
            format="json",
        )

        other_creator = _user_with_permissions(
            other_facility, f"patients.{resource['permission_resource']}.create"
        )
        client.force_authenticate(user=other_creator)
        client.post(
            _list_url(resource["basename"]),
            resource["create_payload"](other_patient),
            format="json",
        )

        viewer = _user_with_permissions(
            facility, f"patients.{resource['permission_resource']}.view"
        )
        client.force_authenticate(user=viewer)
        response = client.get(_list_url(resource["basename"]))

        returned_ids = {row["id"] for row in response.data["results"]}
        assert returned_ids == {own_record.data["id"]}

    def test_cannot_create_a_record_against_a_patient_in_another_facility(self, client, resource):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        other_patient = PatientFactory(facility=other_facility)

        creator = _user_with_permissions(
            facility, f"patients.{resource['permission_resource']}.create"
        )
        client.force_authenticate(user=creator)
        response = client.post(
            _list_url(resource["basename"]),
            resource["create_payload"](other_patient),
            format="json",
        )

        assert response.status_code == 400


@pytest.mark.parametrize("resource", RESOURCES, ids=lambda r: r["basename"])
class TestRelatedEntityDeactivate:
    def test_view_permission_does_not_grant_deactivate(self, client, resource):
        facility = FacilityFactory()
        patient = PatientFactory(facility=facility)
        creator = _user_with_permissions(
            facility, f"patients.{resource['permission_resource']}.create"
        )
        client.force_authenticate(user=creator)
        created = client.post(
            _list_url(resource["basename"]),
            resource["create_payload"](patient),
            format="json",
        )

        viewer = _user_with_permissions(
            facility, f"patients.{resource['permission_resource']}.view"
        )
        client.force_authenticate(user=viewer)
        response = client.post(_deactivate_url(resource["basename"], created.data["id"]))
        assert response.status_code == 403

    def test_deactivate_soft_deletes_and_excludes_from_list(self, client, resource):
        facility = FacilityFactory()
        patient = PatientFactory(facility=facility)
        user = _user_with_permissions(
            facility,
            f"patients.{resource['permission_resource']}.create",
            f"patients.{resource['permission_resource']}.view",
            f"patients.{resource['permission_resource']}.deactivate",
        )
        client.force_authenticate(user=user)
        created = client.post(
            _list_url(resource["basename"]),
            resource["create_payload"](patient),
            format="json",
        )

        deactivate_response = client.post(_deactivate_url(resource["basename"], created.data["id"]))
        assert deactivate_response.status_code == 204

        list_response = client.get(_list_url(resource["basename"]))
        returned_ids = {row["id"] for row in list_response.data["results"]}
        assert created.data["id"] not in returned_ids
