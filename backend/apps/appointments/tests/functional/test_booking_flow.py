"""
Full booking → queue journey (Solution Spec Flow 5.2): check availability,
book, confirm the doctor's schedule can no longer offer that slot, check the
patient in, and confirm they land in the live queue at position 1 — walking
every step of the BRD journey, not just the happy first step.
"""

import datetime

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
from apps.appointments.factories import DoctorScheduleFactory
from apps.core.factories import DepartmentFactory, FacilityFactory
from apps.patients.factories import PatientFactory

pytestmark = pytest.mark.django_db


def _receptionist(facility):
    user = UserFactory(facility=facility)
    role = RoleFactory(name="Receptionist")
    for code in [
        "patients.patient.create",
        "appointments.appointment.view",
        "appointments.appointment.create",
        "appointments.appointment.check_in",
    ]:
        permission = PermissionFactory(code=code)
        RolePermissionFactory(role=role, permission=permission)
    UserRoleFactory(user=user, role=role, facility=None)
    return user


def _next_monday():
    today = timezone.localdate()
    days_ahead = (0 - today.weekday()) % 7 or 7
    return today + datetime.timedelta(days=days_ahead)


@pytest.mark.smoke
def test_full_booking_to_queue_journey():
    facility = FacilityFactory(code="NBI01")
    department = DepartmentFactory(facility=facility, name="OPD")
    doctor = UserFactory(facility=facility)
    DoctorScheduleFactory(
        doctor=doctor,
        department=department,
        day_of_week=0,
        start_time=datetime.time(9, 0),
        end_time=datetime.time(11, 0),
        slot_duration_minutes=30,
    )
    receptionist = _receptionist(facility)
    patient = PatientFactory(facility=facility, first_name="Grace", last_name="Wanjiru")

    client = APIClient()
    client.force_authenticate(user=receptionist)

    # 1. Check availability first — this is what both the web reception
    # view and the mobile app query against (shared API, Flow 5.2).
    target_date = _next_monday()
    availability = client.get(
        reverse("appointments:availability"),
        {"doctor": str(doctor.pk), "department": str(department.pk), "date": str(target_date)},
    )
    assert availability.status_code == 200
    assert len(availability.data["slots"]) == 4  # 9:00-11:00 in 30-min slots
    first_slot = availability.data["slots"][0]

    # 2. Book the first available slot.
    booking = client.post(
        reverse("appointments:appointment-list"),
        {
            "patient": str(patient.pk),
            "doctor": str(doctor.pk),
            "department": str(department.pk),
            "scheduled_at": first_slot,
            "duration_minutes": 30,
            "booking_channel": "web",
        },
        format="json",
    )
    assert booking.status_code == 201
    assert booking.data["status"] == "scheduled"
    appointment_id = booking.data["id"]

    # 3. That slot no longer shows up in availability — proving the booking
    # actually constrains future queries, not just that the POST succeeded.
    availability_after = client.get(
        reverse("appointments:availability"),
        {"doctor": str(doctor.pk), "department": str(department.pk), "date": str(target_date)},
    )
    assert first_slot not in availability_after.data["slots"]
    assert len(availability_after.data["slots"]) == 3

    # 4. Patient arrives — check in. Status flips and a queue position is
    # assigned in the same call (Flow 5.2 steps 5-6).
    check_in = client.post(reverse("appointments:appointment-check-in", args=[appointment_id]))
    assert check_in.status_code == 200
    assert check_in.data["queue_number"] == 1

    # 5. The appointment record itself reflects the new status.
    detail = client.get(reverse("appointments:appointment-detail", args=[appointment_id]))
    assert detail.data["status"] == "checked_in"
