"""
OPD API permission boundary (TRD §4.3). Negative cases first per
CLAUDE.md §4.3.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.appointments.factories import AppointmentFactory
from apps.appointments.models import Appointment
from apps.core.factories import DepartmentFactory, FacilityFactory
from apps.opd.factories import ConsultationFactory, VisitFactory
from apps.opd.services import complete_consultation
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


class TestVisitPermissionBoundary:
    def test_unauthenticated_cannot_list(self, client):
        response = client.get(reverse("opd:visit-list"))
        assert response.status_code == 401

    def test_user_without_create_permission_cannot_start_a_visit(self, client):
        facility = FacilityFactory()
        department = DepartmentFactory(facility=facility)
        doctor = UserFactory(facility=facility)
        patient = PatientFactory(facility=facility)
        user = _user_with_permissions(facility, "opd.visit.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("opd:visit-list"),
            {
                "patient": str(patient.pk),
                "doctor": str(doctor.pk),
                "department": str(department.pk),
            },
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_start_a_visit(self, client):
        facility = FacilityFactory()
        department = DepartmentFactory(facility=facility)
        doctor = UserFactory(facility=facility)
        patient = PatientFactory(facility=facility)
        user = _user_with_permissions(facility, "opd.visit.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("opd:visit-list"),
            {
                "patient": str(patient.pk),
                "doctor": str(doctor.pk),
                "department": str(department.pk),
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["status"] == "in_progress"

    def test_can_start_a_visit_from_a_checked_in_appointment(self, client):
        facility = FacilityFactory()
        appointment = AppointmentFactory(
            department=DepartmentFactory(facility=facility),
            facility=facility,
            status=Appointment.Status.CHECKED_IN,
        )
        user = _user_with_permissions(facility, "opd.visit.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("opd:visit-list"),
            {
                "patient": str(appointment.patient.pk),
                "doctor": str(appointment.doctor.pk),
                "department": str(appointment.department.pk),
                "appointment": str(appointment.pk),
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["appointment"] == appointment.pk
        appointment.refresh_from_db()
        assert appointment.status == Appointment.Status.IN_CONSULTATION

    def test_visits_from_other_facilities_are_not_listed(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        own = VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        VisitFactory(department=DepartmentFactory(facility=other_facility), facility=other_facility)

        user = _user_with_permissions(facility, "opd.visit.view")
        client.force_authenticate(user=user)
        response = client.get(reverse("opd:visit-list"))

        returned_ids = {row["id"] for row in response.data["results"]}
        assert returned_ids == {str(own.pk)}


class TestVitalsPermissionBoundary:
    def test_view_permission_does_not_grant_create(self, client):
        facility = FacilityFactory()
        visit = VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        user = _user_with_permissions(facility, "opd.vitals.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("opd:vitals-list"),
            {"visit": str(visit.pk), "bp_systolic": 120, "bp_diastolic": 80, "pulse": 72},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_record_vitals(self, client):
        facility = FacilityFactory()
        visit = VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        user = _user_with_permissions(facility, "opd.vitals.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("opd:vitals-list"),
            {"visit": str(visit.pk), "bp_systolic": 120, "bp_diastolic": 80, "pulse": 72},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["recorded_by"] == user.pk


class TestConsultationPermissionBoundary:
    def test_view_permission_does_not_grant_update(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        user = _user_with_permissions(facility, "opd.consultation.view")
        client.force_authenticate(user=user)

        response = client.patch(
            reverse("opd:consultation-detail", args=[consultation.pk]),
            {"chief_complaint": "Headache"},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_update_permission_can_edit_the_draft(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        user = _user_with_permissions(facility, "opd.consultation.update")
        client.force_authenticate(user=user)

        response = client.patch(
            reverse("opd:consultation-detail", args=[consultation.pk]),
            {"chief_complaint": "Headache for 3 days"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["chief_complaint"] == "Headache for 3 days"

    def test_update_permission_does_not_grant_complete(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        user = _user_with_permissions(facility, "opd.consultation.update")
        client.force_authenticate(user=user)

        response = client.post(reverse("opd:consultation-complete", args=[consultation.pk]))
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_complete_permission_can_complete_the_consultation(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        user = _user_with_permissions(facility, "opd.consultation.complete")
        client.force_authenticate(user=user)

        response = client.post(reverse("opd:consultation-complete", args=[consultation.pk]))
        assert response.status_code == 200
        assert response.data["locked_at"] is not None

    def test_cannot_complete_an_already_locked_consultation_via_the_api(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        complete_consultation(consultation, actor=consultation.visit.doctor)
        user = _user_with_permissions(facility, "opd.consultation.complete")
        client.force_authenticate(user=user)

        response = client.post(reverse("opd:consultation-complete", args=[consultation.pk]))
        assert response.status_code == 400

    def test_cannot_edit_a_locked_consultation_via_the_api(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        complete_consultation(consultation, actor=consultation.visit.doctor)
        user = _user_with_permissions(facility, "opd.consultation.update")
        client.force_authenticate(user=user)

        response = client.patch(
            reverse("opd:consultation-detail", args=[consultation.pk]),
            {"chief_complaint": "Edited after signing"},
            format="json",
        )
        assert response.status_code == 400


class TestDiagnosisPermissionBoundary:
    def test_view_permission_does_not_grant_create(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        user = _user_with_permissions(facility, "opd.diagnosis.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("opd:diagnosis-list"),
            {"consultation": str(consultation.pk), "description": "Flu", "type": "primary"},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_add_a_diagnosis(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        user = _user_with_permissions(facility, "opd.diagnosis.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("opd:diagnosis-list"),
            {
                "consultation": str(consultation.pk),
                "icd_code": "I10",
                "description": "Essential hypertension",
                "type": "primary",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_cannot_add_a_diagnosis_to_a_locked_consultation_via_the_api(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        complete_consultation(consultation, actor=consultation.visit.doctor)
        user = _user_with_permissions(facility, "opd.diagnosis.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("opd:diagnosis-list"),
            {"consultation": str(consultation.pk), "description": "Late", "type": "primary"},
            format="json",
        )
        assert response.status_code == 400


class TestAddendumPermissionBoundary:
    def test_view_permission_does_not_grant_create(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        complete_consultation(consultation, actor=consultation.visit.doctor)
        user = _user_with_permissions(facility, "opd.addendum.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("opd:addendum-list"),
            {"consultation": str(consultation.pk), "text": "Follow-up"},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_add_an_addendum(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        complete_consultation(consultation, actor=consultation.visit.doctor)
        user = _user_with_permissions(facility, "opd.addendum.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("opd:addendum-list"),
            {"consultation": str(consultation.pk), "text": "Follow-up note"},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["author"] == user.pk

    def test_cannot_add_an_addendum_to_an_unlocked_consultation_via_the_api(self, client):
        facility = FacilityFactory()
        consultation = ConsultationFactory(
            visit=VisitFactory(department=DepartmentFactory(facility=facility), facility=facility)
        )
        user = _user_with_permissions(facility, "opd.addendum.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("opd:addendum-list"),
            {"consultation": str(consultation.pk), "text": "Too early"},
            format="json",
        )
        assert response.status_code == 400
