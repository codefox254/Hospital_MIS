import factory
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.billing.models import Invoice, InvoiceLineItem, MpesaTransaction, Payment, Refund
from apps.patients.factories import PatientFactory


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    facility = factory.SubFactory("apps.core.factories.FacilityFactory")
    patient = factory.SubFactory(PatientFactory, facility=factory.SelfAttribute("..facility"))
    invoice_number = factory.Sequence(lambda n: f"INV-TEST-{n:06d}")
    created_by = factory.SubFactory(UserFactory, facility=factory.SelfAttribute("..facility"))


class InvoiceLineItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InvoiceLineItem

    invoice = factory.SubFactory(InvoiceFactory)
    source_module = "opd"
    source_reference_id = factory.Faker("uuid4")
    description = "Consultation fee"
    quantity = 1
    unit_price = "500.00"
    amount = "500.00"


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    invoice = factory.SubFactory(InvoiceFactory)
    method = Payment.Method.CASH
    amount = "500.00"
    status = Payment.Status.CONFIRMED
    received_by = factory.SubFactory(
        UserFactory, facility=factory.SelfAttribute("..invoice.facility")
    )
    received_at = factory.LazyFunction(timezone.now)


class MpesaTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MpesaTransaction

    payment = factory.SubFactory(PaymentFactory, method=Payment.Method.MPESA)
    checkout_request_id = factory.Sequence(lambda n: f"ws_CO_test{n:06d}")
    phone_number = "254712345678"


class RefundFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Refund

    invoice = factory.SubFactory(InvoiceFactory)
    payment = factory.SubFactory(PaymentFactory, invoice=factory.SelfAttribute("..invoice"))
    amount = "100.00"
    reason = "Overcharged"
    approved_by = factory.SubFactory(
        UserFactory, facility=factory.SelfAttribute("..invoice.facility")
    )
    approved_at = factory.LazyFunction(timezone.now)
