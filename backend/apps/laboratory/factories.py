import factory
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.laboratory.models import LabOrder, LabOrderItem, LabResult, LabResultValue, LabSample
from apps.opd.factories import VisitFactory


class LabOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LabOrder

    visit = factory.SubFactory(VisitFactory)
    facility = factory.SelfAttribute("visit.facility")
    ordered_by = factory.SubFactory(UserFactory, facility=factory.SelfAttribute("..visit.facility"))
    ordered_at = factory.LazyFunction(timezone.now)


class LabOrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LabOrderItem

    lab_order = factory.SubFactory(LabOrderFactory)
    test_code = "CBC"
    test_name = "Complete Blood Count"


class LabSampleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LabSample

    lab_order_item = factory.SubFactory(LabOrderItemFactory)
    barcode = factory.Sequence(lambda n: f"BARCODE{n:06d}")
    collected_by = factory.SubFactory(
        UserFactory, facility=factory.SelfAttribute("..lab_order_item.lab_order.facility")
    )
    collected_at = factory.LazyFunction(timezone.now)


class LabResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LabResult

    lab_order_item = factory.SubFactory(LabOrderItemFactory)
    entered_by = factory.SubFactory(
        UserFactory, facility=factory.SelfAttribute("..lab_order_item.lab_order.facility")
    )
    entered_at = factory.LazyFunction(timezone.now)


class LabResultValueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LabResultValue

    lab_result = factory.SubFactory(LabResultFactory)
    parameter = "WBC"
    value = "7.2"
    unit = "x10^9/L"
    reference_range = "4.0-11.0"
    flag = LabResultValue.Flag.NORMAL
