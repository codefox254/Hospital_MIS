import pytest

from apps.audit.factories import AuditLogEntryFactory
from apps.audit.models import AuditLogEntry

pytestmark = pytest.mark.django_db


class TestAuditLogEntry:
    def test_actor_can_be_null_for_system_actor_writes(self):
        entry = AuditLogEntryFactory(actor=None)
        assert entry.actor is None

    def test_entry_has_uuid_primary_key(self):
        entry = AuditLogEntryFactory()
        assert len(str(entry.pk)) == 36

    def test_action_choices_match_data_dictionary(self):
        assert set(AuditLogEntry.Action.values) == {"create", "update", "soft_delete"}

    def test_str_includes_action_and_model(self):
        entry = AuditLogEntryFactory(
            action=AuditLogEntry.Action.UPDATE, model_name="core.Department"
        )
        assert "update" in str(entry)
        assert "core.Department" in str(entry)
