"""
Walks Solution Spec Flow 5.7 end-to-end via the real API: an invoice
accrues line items from other modules, the cashier initiates an M-Pesa
STK push, the Daraja callback confirms it, and the invoice settles —
with a real accountant-approved refund afterward.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.billing.services import add_line_item
from apps.core.factories import FacilityFactory
from apps.patients.factories import PatientFactory

pytestmark = pytest.mark.django_db


def _staff_user(facility, *codes):
    user = UserFactory(facility=facility)
    role = RoleFactory()
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code)
        RolePermissionFactory(role=role, permission=permission)
    UserRoleFactory(user=user, role=role, facility=None)
    return user


@pytest.mark.smoke
def test_full_billing_and_mpesa_journey():
    client = APIClient()
    facility = FacilityFactory()
    patient = PatientFactory(facility=facility)

    cashier = _staff_user(
        facility,
        "billing.invoice.create",
        "billing.invoice.view",
        "billing.payment.create",
        "billing.payment.view",
    )
    client.force_authenticate(user=cashier)

    # 1. Cashier starts an invoice for the patient.
    invoice_response = client.post(
        reverse("billing:invoice-list"), {"patient": str(patient.pk)}, format="json"
    )
    assert invoice_response.status_code == 201
    invoice_id = invoice_response.data["id"]

    # Other modules generate line items (simulated directly — the real
    # cross-module wiring is Pharmacy's dispense_medication(), per the
    # CHANGELOG's note on what's actually wired vs. flagged deferred).
    from apps.billing.models import Invoice

    invoice = Invoice.objects.get(pk=invoice_id)
    add_line_item(
        invoice,
        source_module="opd",
        source_reference_id="00000000-0000-0000-0000-000000000001",
        description="Consultation fee",
        unit_price="500.00",
    )

    # 2. Cashier selects M-Pesa and initiates collection.
    stk_response = client.post(
        reverse("billing:payment-mpesa-stk-push"),
        {"invoice": invoice_id, "phone_number": "254712345678", "amount": "500.00"},
        format="json",
    )
    assert stk_response.status_code == 201
    checkout_request_id = stk_response.data["checkout_request_id"]

    held_invoice = client.get(reverse("billing:invoice-detail", args=[invoice_id]))
    assert held_invoice.data["status"] == "pending_confirmation"

    # 3-4. Safaricom's webhook confirms the payment (unauthenticated caller).
    unauthenticated_client = APIClient()
    callback_response = unauthenticated_client.post(
        reverse("billing:mpesa-transaction-callback"),
        {
            "checkout_request_id": checkout_request_id,
            "success": True,
            "mpesa_receipt_number": "QGH7XYZ123",
        },
        format="json",
    )
    assert callback_response.status_code == 200
    assert callback_response.data["status"] == "confirmed"

    # 6. Invoice is paid across every channel.
    final_invoice = client.get(reverse("billing:invoice-detail", args=[invoice_id]))
    assert final_invoice.data["status"] == "paid"
    assert final_invoice.data["balance"] == "0.00"

    # A refund now requires an accountant who wasn't the cashier.
    payment_id = client.get(reverse("billing:payment-list"), {"invoice": invoice_id}).data[
        "results"
    ][0]["id"]
    accountant = _staff_user(facility, "billing.refund.create")
    client.force_authenticate(user=accountant)

    refund_response = client.post(
        reverse("billing:refund-list"),
        {"invoice": invoice_id, "payment": payment_id, "amount": "100.00", "reason": "Overcharged"},
        format="json",
    )
    assert refund_response.status_code == 201
