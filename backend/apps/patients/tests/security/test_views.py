"""
Patient API permission boundary (TRD §4.3). Negative cases first per
CLAUDE.md §4.3: create/view/update/deactivate are four distinct permission
codes, and a role holding one must not get the others for free.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import (
    PermissionFactory,
    RoleFactory,
    RolePermissionFactory,
    UserFactory,
    UserRoleFactory,
)
from apps.core.factories import FacilityFactory
from apps.patients.factories import PatientFactory

pytestmark = pytest.mark.django_db

LIST_URL = reverse("patients:patient-list")


def _detail_url(pk):
    return reverse("patients:patient-detail", args=[pk])


def _deactivate_url(pk):
    return reverse("patients:patient-deactivate", args=[pk])


@pytest.fixture
def client():
    return APIClient()


def _user_with_permissions(facility, *codes):
    user = UserFactory(facility=facility)
    role = RoleFactory()
    for code in codes:
        permission = PermissionFactory(code=code)
        RolePermissionFactory(role=role, permission=permission)
    UserRoleFactory(user=user, role=role, facility=None)
    return user


class TestPermissionBoundary:
    def test_unauthenticated_request_is_denied(self, client):
        response = client.get(LIST_URL)
        assert response.status_code == 401

    def test_user_without_view_permission_cannot_list(self, client):
        user = UserFactory()
        client.force_authenticate(user=user)
        assert client.get(LIST_URL).status_code == 403

    def test_user_without_create_permission_cannot_register(self, client):
        facility = FacilityFactory()
        user = _user_with_permissions(facility, "patients.patient.view")
        client.force_authenticate(user=user)

        response = client.post(LIST_URL, {"first_name": "Jane", "last_name": "M"}, format="json")
        assert response.status_code == 403

    def test_view_permission_does_not_grant_deactivate(self, client):
        facility = FacilityFactory()
        user = _user_with_permissions(facility, "patients.patient.view")
        patient = PatientFactory(facility=facility)
        client.force_authenticate(user=user)

        response = client.post(_deactivate_url(patient.pk))
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_register_a_patient(self, client):
        facility = FacilityFactory()
        user = _user_with_permissions(facility, "patients.patient.create")
        client.force_authenticate(user=user)

        response = client.post(
            LIST_URL, {"first_name": "Jane", "last_name": "Mwangi"}, format="json"
        )
        assert response.status_code == 201
        assert response.data["mrn"]

    def test_user_with_deactivate_permission_can_deactivate(self, client):
        facility = FacilityFactory()
        user = _user_with_permissions(facility, "patients.patient.deactivate")
        patient = PatientFactory(facility=facility)
        client.force_authenticate(user=user)

        response = client.post(_deactivate_url(patient.pk))
        assert response.status_code == 204
        patient.refresh_from_db()
        assert patient.deleted_at is not None


class TestFacilityIsolation:
    def test_patients_from_other_facilities_are_not_listed(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        user = _user_with_permissions(facility, "patients.patient.view")
        own_patient = PatientFactory(facility=facility)
        PatientFactory(facility=other_facility)

        client.force_authenticate(user=user)
        response = client.get(LIST_URL)

        returned_ids = {row["id"] for row in response.data["results"]}
        assert returned_ids == {str(own_patient.pk)}

    def test_cannot_retrieve_a_patient_from_another_facility(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        user = _user_with_permissions(facility, "patients.patient.view")
        other_patient = PatientFactory(facility=other_facility)

        client.force_authenticate(user=user)
        response = client.get(_detail_url(other_patient.pk))
        assert response.status_code == 404


class TestServerSideMrn:
    def test_client_supplied_mrn_in_request_body_is_ignored(self, client):
        facility = FacilityFactory()
        user = _user_with_permissions(facility, "patients.patient.create")
        client.force_authenticate(user=user)

        response = client.post(
            LIST_URL,
            {"first_name": "Jane", "last_name": "M", "mrn": "HACKED-000000"},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["mrn"] != "HACKED-000000"

    def test_delete_verb_is_not_allowed(self, client):
        facility = FacilityFactory()
        user = _user_with_permissions(
            facility, "patients.patient.view", "patients.patient.deactivate"
        )
        patient = PatientFactory(facility=facility)
        client.force_authenticate(user=user)

        response = client.delete(_detail_url(patient.pk))
        assert response.status_code == 405


class TestSearch:
    def test_search_finds_a_patient_by_partial_name(self, client):
        facility = FacilityFactory()
        user = _user_with_permissions(facility, "patients.patient.view")
        PatientFactory(facility=facility, first_name="Jane", last_name="Mwangi")
        PatientFactory(facility=facility, first_name="John", last_name="Otieno")

        client.force_authenticate(user=user)
        response = client.get(LIST_URL, {"search": "Mwangi"})

        names = {row["last_name"] for row in response.data["results"]}
        assert names == {"Mwangi"}

    def test_search_finds_a_patient_by_mrn(self, client):
        facility = FacilityFactory()
        user = _user_with_permissions(facility, "patients.patient.view")
        target = PatientFactory(facility=facility, mrn="NBI01-2026-000042")
        PatientFactory(facility=facility)

        client.force_authenticate(user=user)
        response = client.get(LIST_URL, {"search": "000042"})

        returned_ids = {row["id"] for row in response.data["results"]}
        assert returned_ids == {str(target.pk)}


class TestDeletedPatientsAreHidden:
    def test_deactivated_patient_is_excluded_from_list(self, client):
        facility = FacilityFactory()
        user = _user_with_permissions(facility, "patients.patient.view")
        patient = PatientFactory(facility=facility)
        patient.soft_delete()

        client.force_authenticate(user=user)
        response = client.get(LIST_URL)

        returned_ids = {row["id"] for row in response.data["results"]}
        assert str(patient.pk) not in returned_ids
