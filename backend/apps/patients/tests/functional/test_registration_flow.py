"""
Full registration journey (Solution Spec Flow 5.1): a receptionist searches
for an existing patient first (de-duplication check), finds none, registers
a new one, then confirms it's retrievable — walking every step of the BRD
journey, not just the happy first step (CLAUDE.md §6.2).
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


def _receptionist(facility):
    user = UserFactory(facility=facility)
    role = RoleFactory(name="Receptionist")
    for code in ("patients.patient.view", "patients.patient.create", "patients.patient.update"):
        permission = PermissionFactory(code=code)
        RolePermissionFactory(role=role, permission=permission)
    UserRoleFactory(user=user, role=role, facility=None)
    return user


@pytest.mark.smoke
def test_full_registration_journey():
    facility = FacilityFactory(code="NBI01")
    receptionist = _receptionist(facility)
    existing_patient = PatientFactory(
        facility=facility, first_name="John", last_name="Mwangi", phone="+254700111222"
    )

    client = APIClient()
    client.force_authenticate(user=receptionist)

    # 1. Search first — de-duplication check (BRD edge case) — the incoming
    # patient shares a surname but is a different person, phone confirms it.
    dedup_check = client.get(LIST_URL, {"search": "0700333444"})
    assert dedup_check.data["count"] == 0

    # 2. No match found — register the new patient. MRN is never client
    # supplied; the API generates it.
    registration = client.post(
        LIST_URL,
        {
            "first_name": "Grace",
            "last_name": "Mwangi",
            "phone": "+254700333444",
            "gender": "female",
            "date_of_birth": "1990-05-14",
        },
        format="json",
    )
    assert registration.status_code == 201
    new_mrn = registration.data["mrn"]
    assert new_mrn
    assert new_mrn != existing_patient.mrn

    # 3. The new patient is now retrievable by MRN search, distinct from the
    # existing same-surname patient found in step 1's search space.
    lookup = client.get(LIST_URL, {"search": new_mrn})
    assert lookup.data["count"] == 1
    assert lookup.data["results"][0]["first_name"] == "Grace"

    # 4. Demographics can be corrected post-registration (e.g. a typo caught
    # at the desk) — an update, not a re-registration.
    patient_id = registration.data["id"]
    update = client.patch(
        reverse("patients:patient-detail", args=[patient_id]),
        {"phone": "+254700333445"},
        format="json",
    )
    assert update.status_code == 200
    assert update.data["phone"] == "+254700333445"
    assert update.data["mrn"] == new_mrn  # MRN never changes on update
