import datetime

import factory
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.opd.factories import ConsultationFactory
from apps.pharmacy.models import DispenseRecord, Drug, Prescription, PrescriptionItem, StockBatch


class DrugFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Drug

    name = factory.Sequence(lambda n: f"Test Drug {n}")
    generic_name = factory.Sequence(lambda n: f"testdrugum{n}")
    form = "tablet"
    strength = "500mg"
    is_controlled = False


class StockBatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StockBatch

    facility = factory.SubFactory("apps.core.factories.FacilityFactory")
    drug = factory.SubFactory(DrugFactory)
    batch_number = factory.Sequence(lambda n: f"BATCH{n:05d}")
    expiry_date = factory.LazyFunction(lambda: timezone.localdate() + datetime.timedelta(days=365))
    quantity_on_hand = 100
    unit_cost = "10.00"


class PrescriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Prescription

    consultation = factory.SubFactory(ConsultationFactory)
    patient = factory.SelfAttribute("consultation.visit.patient")
    prescribed_by = factory.SelfAttribute("consultation.visit.doctor")


class PrescriptionItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PrescriptionItem

    prescription = factory.SubFactory(PrescriptionFactory)
    drug = factory.SubFactory(DrugFactory)
    dosage = "1 tablet"
    frequency = "twice daily"
    duration_days = 7
    qty_prescribed = 14


class DispenseRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DispenseRecord

    prescription_item = factory.SubFactory(PrescriptionItemFactory)
    batch = factory.SubFactory(
        StockBatchFactory,
        drug=factory.SelfAttribute("..prescription_item.drug"),
        facility=factory.SelfAttribute(
            "..prescription_item.prescription.consultation.visit.facility"
        ),
    )
    dispensed_by = factory.SubFactory(
        UserFactory,
        facility=factory.SelfAttribute(
            "..prescription_item.prescription.consultation.visit.facility"
        ),
    )
    qty_dispensed = 14
    dispensed_at = factory.LazyFunction(timezone.now)
