import factory

from apps.core.factories import FacilityFactory
from apps.patients.models import Patient


class PatientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Patient

    facility = factory.SubFactory(FacilityFactory)
    mrn = factory.Sequence(lambda n: f"TST-2026-{n:06d}")
    first_name = factory.Sequence(lambda n: f"TestFirst{n}")
    last_name = factory.Sequence(lambda n: f"TestLast{n}")
    gender = Patient.Gender.UNSPECIFIED
