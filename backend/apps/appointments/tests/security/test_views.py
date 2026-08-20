"""
Appointments & Queue API permission boundary (TRD §4.3). Negative cases
first per CLAUDE.md §4.3.
"""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.appointments.factories import AppointmentFactory, DoctorScheduleFactory, QueueEntryFactory
from apps.core.factories import DepartmentFactory, FacilityFactory
from apps.patients.factories import PatientFactory

pytestmark = pytest.mark.django_db


def _user_with_permissions(facility, *codes):
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


class TestAppointmentPermissionBoundary:
    def test_unauthenticated_cannot_list(self, client):
        response = client.get(reverse("appointments:appointment-list"))
        assert response.status_code == 401

    def test_user_without_create_permission_cannot_book(self, client):
        facility = FacilityFactory()
        department = DepartmentFactory(facility=facility)
        doctor = UserFactory(facility=facility)
        patient = PatientFactory(facility=facility)
        user = _user_with_permissions(facility, "appointments.appointment.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("appointments:appointment-list"),
            {
                "patient": str(patient.pk),
                "doctor": str(doctor.pk),
                "department": str(department.pk),
                "scheduled_at": (timezone.now() + datetime.timedelta(days=1)).isoformat(),
                "duration_minutes": 30,
                "booking_channel": "walk_in",
            },
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_book(self, client):
        facility = FacilityFactory()
        department = DepartmentFactory(facility=facility)
        doctor = UserFactory(facility=facility)
        patient = PatientFactory(facility=facility)
        user = _user_with_permissions(facility, "appointments.appointment.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("appointments:appointment-list"),
            {
                "patient": str(patient.pk),
                "doctor": str(doctor.pk),
                "department": str(department.pk),
                "scheduled_at": (timezone.now() + datetime.timedelta(days=1)).isoformat(),
                "duration_minutes": 30,
                "booking_channel": "walk_in",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["status"] == "scheduled"

    def test_double_booking_via_api_returns_400_not_500(self, client):
        facility = FacilityFactory()
        existing = AppointmentFactory(
            facility=facility, department=DepartmentFactory(facility=facility)
        )
        patient = PatientFactory(facility=facility)
        user = _user_with_permissions(facility, "appointments.appointment.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("appointments:appointment-list"),
            {
                "patient": str(patient.pk),
                "doctor": str(existing.doctor.pk),
                "department": str(existing.department.pk),
                "scheduled_at": existing.scheduled_at.isoformat(),
                "duration_minutes": 30,
                "booking_channel": "walk_in",
            },
            format="json",
        )
        assert response.status_code == 400

    def test_view_permission_does_not_grant_check_in(self, client):
        facility = FacilityFactory()
        appointment = AppointmentFactory(
            facility=facility, department=DepartmentFactory(facility=facility)
        )
        user = _user_with_permissions(facility, "appointments.appointment.view")
        client.force_authenticate(user=user)

        response = client.post(reverse("appointments:appointment-check-in", args=[appointment.pk]))
        assert response.status_code == 403

    def test_user_with_check_in_permission_can_check_in(self, client):
        facility = FacilityFactory()
        appointment = AppointmentFactory(
            facility=facility, department=DepartmentFactory(facility=facility)
        )
        user = _user_with_permissions(facility, "appointments.appointment.check_in")
        client.force_authenticate(user=user)

        response = client.post(reverse("appointments:appointment-check-in", args=[appointment.pk]))
        assert response.status_code == 200
        assert response.data["queue_number"] == 1


class TestAppointmentFacilityIsolation:
    def test_appointments_from_other_facilities_are_not_listed(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        own = AppointmentFactory(facility=facility, department=DepartmentFactory(facility=facility))
        AppointmentFactory(
            facility=other_facility, department=DepartmentFactory(facility=other_facility)
        )

        user = _user_with_permissions(facility, "appointments.appointment.view")
        client.force_authenticate(user=user)
        response = client.get(reverse("appointments:appointment-list"))

        returned_ids = {row["id"] for row in response.data["results"]}
        assert returned_ids == {str(own.pk)}


class TestQueuePermissionBoundary:
    def test_view_permission_does_not_grant_call(self, client):
        facility = FacilityFactory()
        appointment = AppointmentFactory(
            facility=facility, department=DepartmentFactory(facility=facility)
        )
        entry = QueueEntryFactory(appointment=appointment)
        user = _user_with_permissions(facility, "appointments.queue.view")
        client.force_authenticate(user=user)

        response = client.post(reverse("appointments:queue-entry-call", args=[entry.pk]))
        assert response.status_code == 403

    def test_user_with_call_permission_can_call_next(self, client):
        facility = FacilityFactory()
        appointment = AppointmentFactory(
            facility=facility, department=DepartmentFactory(facility=facility)
        )
        entry = QueueEntryFactory(appointment=appointment)
        user = _user_with_permissions(facility, "appointments.queue.call")
        client.force_authenticate(user=user)

        response = client.post(reverse("appointments:queue-entry-call", args=[entry.pk]))
        assert response.status_code == 200
        assert response.data["called_at"] is not None


class TestDoctorSchedulePermissionBoundary:
    def test_unauthenticated_cannot_create_a_schedule(self, client):
        response = client.post(reverse("appointments:doctor-schedule-list"), {}, format="json")
        assert response.status_code == 401

    def test_user_with_create_permission_can_create_a_schedule(self, client):
        facility = FacilityFactory()
        department = DepartmentFactory(facility=facility)
        doctor = UserFactory(facility=facility)
        user = _user_with_permissions(facility, "appointments.doctor_schedule.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("appointments:doctor-schedule-list"),
            {
                "doctor": str(doctor.pk),
                "department": str(department.pk),
                "day_of_week": 0,
                "start_time": "09:00:00",
                "end_time": "17:00:00",
                "slot_duration_minutes": 30,
            },
            format="json",
        )
        assert response.status_code == 201


class TestAvailabilityEndpoint:
    def test_unauthenticated_cannot_query_availability(self, client):
        response = client.get(reverse("appointments:availability"))
        assert response.status_code == 401

    def test_returns_slots_from_the_doctors_schedule(self, client):
        facility = FacilityFactory()
        department = DepartmentFactory(facility=facility)
        doctor = UserFactory(facility=facility)
        DoctorScheduleFactory(
            doctor=doctor,
            department=department,
            day_of_week=0,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(10, 0),
            slot_duration_minutes=30,
        )
        user = _user_with_permissions(facility, "appointments.appointment.view")
        client.force_authenticate(user=user)

        today = timezone.localdate()
        days_ahead = (0 - today.weekday()) % 7 or 7
        target_date = today + datetime.timedelta(days=days_ahead)

        response = client.get(
            reverse("appointments:availability"),
            {"doctor": str(doctor.pk), "department": str(department.pk), "date": str(target_date)},
        )
        assert response.status_code == 200
        assert len(response.data["slots"]) == 2

    def test_cannot_query_availability_for_a_doctor_in_another_facility(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        other_department = DepartmentFactory(facility=other_facility)
        other_doctor = UserFactory(facility=other_facility)
        user = _user_with_permissions(facility, "appointments.appointment.view")
        client.force_authenticate(user=user)

        response = client.get(
            reverse("appointments:availability"),
            {
                "doctor": str(other_doctor.pk),
                "department": str(other_department.pk),
                "date": str(timezone.localdate()),
            },
        )
        assert response.status_code == 404
