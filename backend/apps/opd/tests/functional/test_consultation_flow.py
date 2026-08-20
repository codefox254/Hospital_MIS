"""
Walks Solution Spec Flow 5.3 end-to-end via the real API: nurse records
vitals against a freshly started visit, doctor drafts the consultation,
adds a diagnosis, completes (locking) it, and — since further changes now
require an addendum, never an edit — adds a follow-up addendum instead.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.core.factories import DepartmentFactory, FacilityFactory
from apps.patients.factories import PatientFactory

pytestmark = pytest.mark.django_db


def _staff_user(facility, *codes):
    user = UserFactory(facility=facility)
    role = RoleFactory()
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code)
        RolePermissionFactory(role=role, permission=permission)
    UserRoleFactory(user=user, role=role, facility=None)
    return user


@pytest.mark.smoke
def test_full_opd_consultation_journey():
    client = APIClient()
    facility = FacilityFactory()
    department = DepartmentFactory(facility=facility)
    doctor = UserFactory(facility=facility)
    patient = PatientFactory(facility=facility)

    staff = _staff_user(
        facility,
        "opd.visit.create",
        "opd.visit.view",
        "opd.vitals.create",
        "opd.consultation.view",
        "opd.consultation.update",
        "opd.consultation.complete",
        "opd.diagnosis.create",
        "opd.addendum.create",
    )
    client.force_authenticate(user=staff)

    # 1. Start the visit (walk-in — no prior appointment).
    start_response = client.post(
        reverse("opd:visit-list"),
        {"patient": str(patient.pk), "doctor": str(doctor.pk), "department": str(department.pk)},
        format="json",
    )
    assert start_response.status_code == 201
    visit_id = start_response.data["id"]
    assert start_response.data["status"] == "in_progress"

    # 2. Nurse records vitals against the active visit.
    vitals_response = client.post(
        reverse("opd:vitals-list"),
        {
            "visit": visit_id,
            "bp_systolic": 118,
            "bp_diastolic": 76,
            "pulse": 70,
            "temperature_c": "36.7",
            "respiration_rate": 15,
            "spo2_percent": 99,
        },
        format="json",
    )
    assert vitals_response.status_code == 201

    # 3. Doctor opens the workspace — the consultation already exists.
    visit_detail = client.get(reverse("opd:visit-detail", args=[visit_id]))
    assert visit_detail.status_code == 200

    list_response = client.get(reverse("opd:consultation-list"), {"visit": visit_id})
    consultation_id = list_response.data["results"][0]["id"]

    # 4. Doctor drafts the consultation — auto-saved, never blocking.
    draft_response = client.patch(
        reverse("opd:consultation-detail", args=[consultation_id]),
        {
            "chief_complaint": "Headache for 3 days",
            "history_of_present_illness": "Gradual onset, worse in the mornings.",
            "examination_notes": "Alert, oriented, no focal deficits.",
        },
        format="json",
    )
    assert draft_response.status_code == 200
    assert draft_response.data["is_draft"] is True

    # 5. Doctor records the diagnosis.
    diagnosis_response = client.post(
        reverse("opd:diagnosis-list"),
        {
            "consultation": consultation_id,
            "icd_code": "R51",
            "description": "Headache",
            "type": "primary",
        },
        format="json",
    )
    assert diagnosis_response.status_code == 201

    # 6. Doctor completes and locks the consultation.
    complete_response = client.post(reverse("opd:consultation-complete", args=[consultation_id]))
    assert complete_response.status_code == 200
    assert complete_response.data["is_draft"] is False
    assert complete_response.data["locked_at"] is not None

    # The visit itself is now closed out too.
    visit_after = client.get(reverse("opd:visit-detail", args=[visit_id]))
    assert visit_after.data["status"] == "completed"

    # 7. Locked means locked — a direct edit is rejected...
    rejected_edit = client.patch(
        reverse("opd:consultation-detail", args=[consultation_id]),
        {"chief_complaint": "Trying to sneak an edit in"},
        format="json",
    )
    assert rejected_edit.status_code == 400

    # ...but an addendum is exactly how a correction gets recorded.
    addendum_response = client.post(
        reverse("opd:addendum-list"),
        {"consultation": consultation_id, "text": "Follow-up: symptoms resolved after rest."},
        format="json",
    )
    assert addendum_response.status_code == 201
