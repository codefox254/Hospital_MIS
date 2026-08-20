"""
Shared factory_boy factories for core models, reused across every app's test
suite. Synthetic data only — no real facility/patient data ever, per
CLAUDE.md's Definition of Done.
"""

import factory

from apps.core.models import Department, Facility


class FacilityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Facility

    name = factory.Sequence(lambda n: f"Test Facility {n}")
    code = factory.Sequence(lambda n: f"FAC{n:03d}")
    type = Facility.FacilityType.HOSPITAL
    is_active = True


class DepartmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Department

    facility = factory.SubFactory(FacilityFactory)
    name = factory.Sequence(lambda n: f"Test Department {n}")
    code = factory.Sequence(lambda n: f"DEPT{n:03d}")
