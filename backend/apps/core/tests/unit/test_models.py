import pytest
from django.db import IntegrityError, transaction

from apps.core.factories import DepartmentFactory, FacilityFactory
from apps.core.models import Department, Facility

pytestmark = pytest.mark.django_db


class TestFacility:
    def test_facility_code_must_be_unique(self):
        FacilityFactory(code="DUPCODE")
        with pytest.raises(IntegrityError), transaction.atomic():
            FacilityFactory(code="DUPCODE")

    def test_facility_has_uuid_primary_key(self):
        facility = FacilityFactory()
        assert isinstance(facility.pk, type(facility.id))
        assert len(str(facility.pk)) == 36  # UUID4 string form

    def test_facility_str(self):
        facility = FacilityFactory(name="Nairobi General", code="NBI01")
        assert str(facility) == "Nairobi General (NBI01)"

    def test_facility_is_active_defaults_true(self):
        facility = FacilityFactory()
        assert facility.is_active is True

    @pytest.mark.smoke
    def test_facility_create_and_retrieve(self):
        facility = FacilityFactory(name="Smoke Facility", code="SMOKE1")
        fetched = Facility.objects.get(code="SMOKE1")
        assert fetched.id == facility.id
        assert fetched.name == "Smoke Facility"


class TestDepartment:
    def test_department_code_unique_within_facility(self):
        facility = FacilityFactory()
        DepartmentFactory(facility=facility, code="OPD")
        with pytest.raises(IntegrityError), transaction.atomic():
            DepartmentFactory(facility=facility, code="OPD")

    def test_department_code_can_repeat_across_facilities(self):
        DepartmentFactory(code="OPD")
        # Should not raise — the unique constraint is scoped per facility.
        DepartmentFactory(code="OPD")
        assert Department.objects.filter(code="OPD").count() == 2

    def test_sub_department_supports_parent_link(self):
        parent = DepartmentFactory(name="Medicine")
        child = DepartmentFactory(
            facility=parent.facility, name="Cardiology", parent_department=parent
        )
        assert child.parent_department == parent
        assert parent.sub_departments.first() == child

    def test_deleting_parent_nulls_child_link_not_deletes_child(self):
        parent = DepartmentFactory(name="Medicine")
        child = DepartmentFactory(
            facility=parent.facility, name="Cardiology", parent_department=parent
        )
        parent.delete()
        child.refresh_from_db()
        assert child.parent_department is None


class TestFacilityScopedManager:
    def test_for_facility_excludes_other_facilities(self):
        facility_a = FacilityFactory()
        facility_b = FacilityFactory()
        dept_a = DepartmentFactory(facility=facility_a)
        DepartmentFactory(facility=facility_b)

        scoped = Department.objects.for_facility(facility_a)
        assert list(scoped) == [dept_a]

    def test_for_facility_returns_empty_for_facility_with_no_records(self):
        facility_a = FacilityFactory()
        facility_b = FacilityFactory()
        DepartmentFactory(facility=facility_a)

        assert list(Department.objects.for_facility(facility_b)) == []
