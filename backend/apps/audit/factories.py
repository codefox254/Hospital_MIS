import factory

from apps.accounts.factories import UserFactory
from apps.audit.models import AuditLogEntry
from apps.core.factories import FacilityFactory


class AuditLogEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuditLogEntry

    actor = factory.SubFactory(UserFactory)
    facility = factory.SubFactory(FacilityFactory)
    model_name = "core.Department"
    record_id = factory.Faker("uuid4")
    action = AuditLogEntry.Action.CREATE
    field_diff = factory.LazyFunction(lambda: {"name": {"old": None, "new": "OPD"}})
