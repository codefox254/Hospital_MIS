import factory
from django.utils import timezone

from apps.core.factories import FacilityFactory
from apps.patients.models import (
    Allergy,
    ChronicCondition,
    Consent,
    EmergencyContact,
    Guardian,
    Patient,
    PatientInsurance,
)


class PatientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Patient

    facility = factory.SubFactory(FacilityFactory)
    mrn = factory.Sequence(lambda n: f"TST-2026-{n:06d}")
    first_name = factory.Sequence(lambda n: f"TestFirst{n}")
    last_name = factory.Sequence(lambda n: f"TestLast{n}")
    gender = Patient.Gender.UNSPECIFIED


class GuardianFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Guardian

    patient = factory.SubFactory(PatientFactory)
    name = factory.Sequence(lambda n: f"Guardian{n}")
    relationship = "Parent"
    phone = "+254700000000"


class EmergencyContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmergencyContact

    patient = factory.SubFactory(PatientFactory)
    name = factory.Sequence(lambda n: f"Contact{n}")
    relationship = "Sibling"
    phone = "+254700000001"


class AllergyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Allergy

    patient = factory.SubFactory(PatientFactory)
    substance = "Penicillin"
    severity = Allergy.Severity.MODERATE


class ChronicConditionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChronicCondition

    patient = factory.SubFactory(PatientFactory)
    condition = "Hypertension"


class ConsentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Consent

    patient = factory.SubFactory(PatientFactory)
    type = Consent.ConsentType.TREATMENT
    granted_at = factory.LazyFunction(timezone.now)


class PatientInsuranceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PatientInsurance

    patient = factory.SubFactory(PatientFactory)
    insurer_name = factory.Sequence(lambda n: f"Insurer{n}")
    policy_number = factory.Sequence(lambda n: f"POL{n:06d}")
    is_primary = True
