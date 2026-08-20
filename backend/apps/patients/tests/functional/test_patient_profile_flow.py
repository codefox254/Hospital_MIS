"""
Full patient profile build-out (Solution Spec §7.1's tabbed record view:
Overview, Visits, Admissions, Labs, ... — one entity, many related facets).
Walks registration through attaching every related facet a receptionist/
nurse would capture at intake, not just the happy first step.
"""

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.factories import (
    PermissionFactory,
    RoleFactory,
    RolePermissionFactory,
    UserFactory,
    UserRoleFactory,
)
from apps.core.factories import FacilityFactory

pytestmark = pytest.mark.django_db

ALL_PATIENT_MODULE_PERMISSIONS = [
    "patients.patient.view",
    "patients.patient.create",
    "patients.guardian.create",
    "patients.guardian.view",
    "patients.allergy.create",
    "patients.allergy.view",
    "patients.chronic_condition.create",
    "patients.chronic_condition.view",
    "patients.consent.create",
    "patients.consent.view",
    "patients.insurance.create",
    "patients.insurance.view",
]


def _intake_officer(facility):
    user = UserFactory(facility=facility)
    role = RoleFactory(name="Registration Officer")
    for code in ALL_PATIENT_MODULE_PERMISSIONS:
        permission = PermissionFactory(code=code)
        RolePermissionFactory(role=role, permission=permission)
    UserRoleFactory(user=user, role=role, facility=None)
    return user


@pytest.mark.smoke
def test_full_intake_journey_attaches_every_related_facet():
    facility = FacilityFactory(code="NBI01")
    officer = _intake_officer(facility)

    client = APIClient()
    client.force_authenticate(user=officer)

    # 1. Register the patient.
    registration = client.post(
        reverse("patients:patient-list"),
        {"first_name": "Amina", "last_name": "Hassan", "gender": "female"},
        format="json",
    )
    assert registration.status_code == 201
    patient_id = registration.data["id"]

    # 2. Record a known drug allergy — read by Pharmacy at dispensing time
    # for the hard-stop interaction check (BRD §6.8 edge case; Pharmacy
    # itself is a later milestone, but the data must exist here first).
    allergy = client.post(
        reverse("patients:allergy-list"),
        {"patient": patient_id, "substance": "Penicillin", "severity": "severe"},
        format="json",
    )
    assert allergy.status_code == 201

    # 3. Capture a guardian (the patient is a minor / needs one on file).
    guardian = client.post(
        reverse("patients:guardian-list"),
        {
            "patient": patient_id,
            "name": "Fatuma Hassan",
            "relationship": "Mother",
            "phone": "+254700222333",
        },
        format="json",
    )
    assert guardian.status_code == 201

    # 4. Record treatment consent.
    consent = client.post(
        reverse("patients:consent-list"),
        {"patient": patient_id, "type": "treatment", "granted_at": timezone.now().isoformat()},
        format="json",
    )
    assert consent.status_code == 201
    assert consent.data["is_active"] is True

    # 5. Attach an insurance policy.
    insurance = client.post(
        reverse("patients:insurance-policy-list"),
        {
            "patient": patient_id,
            "insurer_name": "NHIF",
            "policy_number": "NHIF-998877",
            "is_primary": True,
        },
        format="json",
    )
    assert insurance.status_code == 201

    # 6. Everything just attached is independently retrievable, scoped to
    # this one patient — proving the FK wiring, not just that each POST
    # returned 201 in isolation.
    allergies = client.get(reverse("patients:allergy-list"), {"patient": patient_id})
    assert allergies.data["count"] == 1
    assert allergies.data["results"][0]["substance"] == "Penicillin"

    guardians = client.get(reverse("patients:guardian-list"), {"patient": patient_id})
    assert guardians.data["count"] == 1

    insurance_policies = client.get(
        reverse("patients:insurance-policy-list"), {"patient": patient_id}
    )
    assert insurance_policies.data["count"] == 1
    assert insurance_policies.data["results"][0]["is_primary"] is True
