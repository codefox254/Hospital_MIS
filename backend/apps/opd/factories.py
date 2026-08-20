import factory
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.core.factories import DepartmentFactory
from apps.opd.models import Consultation, ConsultationAddendum, Diagnosis, Visit, Vitals
from apps.patients.factories import PatientFactory


class VisitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Visit

    department = factory.SubFactory(DepartmentFactory)
    facility = factory.SelfAttribute("department.facility")
    patient = factory.SubFactory(
        PatientFactory, facility=factory.SelfAttribute("..department.facility")
    )
    doctor = factory.SubFactory(
        UserFactory, facility=factory.SelfAttribute("..department.facility")
    )
    checked_in_at = factory.LazyFunction(timezone.now)


class VitalsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vitals

    visit = factory.SubFactory(VisitFactory)
    recorded_by = factory.SubFactory(
        UserFactory, facility=factory.SelfAttribute("..visit.facility")
    )
    bp_systolic = 120
    bp_diastolic = 80
    pulse = 72
    temperature_c = "36.8"
    respiration_rate = 16
    spo2_percent = 98
    weight_kg = "70.00"
    height_cm = "170.00"
    recorded_at = factory.LazyFunction(timezone.now)


class ConsultationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Consultation

    visit = factory.SubFactory(VisitFactory)


class DiagnosisFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Diagnosis

    consultation = factory.SubFactory(ConsultationFactory)
    icd_code = "I10"
    description = "Essential (primary) hypertension"
    type = Diagnosis.Type.PRIMARY


class ConsultationAddendumFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ConsultationAddendum

    consultation = factory.SubFactory(ConsultationFactory)
    author = factory.SubFactory(
        UserFactory, facility=factory.SelfAttribute("..consultation.visit.facility")
    )
    text = "Addendum note."
