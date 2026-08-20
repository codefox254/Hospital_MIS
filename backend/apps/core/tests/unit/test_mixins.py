"""
AuditableModel (TRD §8.4) exercised against Department — the only concrete
FacilityScopedModel subclass so far. Every clinical/financial module built
on this base inherits the same guarantees these tests pin down.
"""

import pytest

from apps.accounts.factories import UserFactory
from apps.audit.models import AuditLogEntry
from apps.core.factories import DepartmentFactory, FacilityFactory
from apps.core.models import Department

pytestmark = pytest.mark.django_db


class TestAuditOnCreate:
    @pytest.mark.smoke
    def test_creating_a_record_writes_a_create_entry(self):
        facility = FacilityFactory()
        department = Department(facility=facility, name="OPD", code="OPD")
        department.save()

        entry = AuditLogEntry.objects.get(record_id=department.pk)
        assert entry.action == AuditLogEntry.Action.CREATE
        assert entry.model_name == "core.Department"
        assert entry.facility_id == facility.id

    def test_create_entry_captures_actor_and_ip(self):
        actor = UserFactory()
        department = Department(facility=FacilityFactory(), name="OPD", code="OPD")
        department.save(actor=actor, ip_address="10.0.0.5")

        entry = AuditLogEntry.objects.get(record_id=department.pk)
        assert entry.actor_id == actor.id
        assert entry.ip_address == "10.0.0.5"

    def test_create_entry_diff_has_new_values_and_no_old_values(self):
        department = Department(facility=FacilityFactory(), name="OPD", code="OPD")
        department.save()

        entry = AuditLogEntry.objects.get(record_id=department.pk)
        assert entry.field_diff["name"] == {"old": None, "new": "OPD"}
        assert entry.field_diff["code"] == {"old": None, "new": "OPD"}


class TestAuditOnUpdate:
    def test_updating_a_changed_field_writes_an_update_entry_with_diff(self):
        department = DepartmentFactory(name="Medicine")
        department.name = "Internal Medicine"
        department.save()

        entry = AuditLogEntry.objects.filter(
            record_id=department.pk, action=AuditLogEntry.Action.UPDATE
        ).latest("created_at")
        assert entry.field_diff["name"] == {"old": "Medicine", "new": "Internal Medicine"}

    def test_saving_with_no_field_changes_writes_no_entry(self):
        department = DepartmentFactory()
        entries_before = AuditLogEntry.objects.filter(record_id=department.pk).count()

        department.save()  # no field changed

        entries_after = AuditLogEntry.objects.filter(record_id=department.pk).count()
        assert entries_after == entries_before

    def test_unrelated_field_is_absent_from_the_diff(self):
        department = DepartmentFactory(name="Medicine", code="MED")
        department.name = "Internal Medicine"
        department.save()

        entry = AuditLogEntry.objects.filter(
            record_id=department.pk, action=AuditLogEntry.Action.UPDATE
        ).latest("created_at")
        assert "code" not in entry.field_diff


class TestSoftDelete:
    def test_soft_delete_sets_deleted_at_and_writes_an_entry(self):
        department = DepartmentFactory()
        assert department.deleted_at is None

        department.soft_delete()

        department.refresh_from_db()
        assert department.deleted_at is not None
        entry = AuditLogEntry.objects.filter(
            record_id=department.pk, action=AuditLogEntry.Action.SOFT_DELETE
        ).get()
        assert entry.field_diff["deleted_at"]["old"] is None

    def test_record_still_exists_after_soft_delete(self):
        department = DepartmentFactory()
        department.soft_delete()
        assert Department.objects.filter(pk=department.pk).exists()

    def test_soft_deleting_twice_is_a_no_op_second_time(self):
        department = DepartmentFactory()
        department.soft_delete()
        first_deleted_at = department.deleted_at

        department.soft_delete()

        assert department.deleted_at == first_deleted_at
        assert (
            AuditLogEntry.objects.filter(
                record_id=department.pk, action=AuditLogEntry.Action.SOFT_DELETE
            ).count()
            == 1
        )

    def test_hard_delete_always_raises_regardless_of_soft_delete_state(self):
        department = DepartmentFactory()
        department.soft_delete()
        with pytest.raises(NotImplementedError):
            department.delete()


class TestAuditLogIndependence:
    def test_audit_entries_are_queryable_without_the_source_model(self):
        """The audit trail must stand on its own (TRD §8.4) — queryable by
        facility/model_name alone, not through Department's own manager."""
        facility = FacilityFactory()
        DepartmentFactory(facility=facility)

        entries = AuditLogEntry.objects.filter(facility=facility, model_name="core.Department")
        assert entries.count() == 1
