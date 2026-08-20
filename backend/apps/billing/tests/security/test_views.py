"""
Billing API permission boundary (TRD §4.3). Negative cases first per
CLAUDE.md §4.3.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.billing.factories import InvoiceFactory, PaymentFactory
from apps.billing.services import add_line_item, initiate_mpesa_stk_push
from apps.core.factories import FacilityFactory
from apps.patients.factories import PatientFactory

pytestmark = pytest.mark.django_db


def _user_with_permissions(facility, *codes):
    user = UserFactory(facility=facility)
    role = RoleFactory()
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code)
        RolePermissionFactory(role=role, permission=permission)
    UserRoleFactory(user=user, role=role, facility=None)
    return user


@pytest.fixture
def client():
    return APIClient()


class TestInvoicePermissionBoundary:
    def test_unauthenticated_cannot_list(self, client):
        response = client.get(reverse("billing:invoice-list"))
        assert response.status_code == 401

    def test_user_without_create_permission_cannot_start_an_invoice(self, client):
        facility = FacilityFactory()
        patient = PatientFactory(facility=facility)
        user = _user_with_permissions(facility, "billing.invoice.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:invoice-list"), {"patient": str(patient.pk)}, format="json"
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_start_an_invoice(self, client):
        facility = FacilityFactory()
        patient = PatientFactory(facility=facility)
        user = _user_with_permissions(facility, "billing.invoice.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:invoice-list"), {"patient": str(patient.pk)}, format="json"
        )
        assert response.status_code == 201
        assert response.data["invoice_number"].startswith(f"INV-{facility.code}-")

    def test_cannot_start_an_invoice_against_a_patient_in_another_facility(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        other_patient = PatientFactory(facility=other_facility)
        user = _user_with_permissions(facility, "billing.invoice.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:invoice-list"), {"patient": str(other_patient.pk)}, format="json"
        )
        assert response.status_code == 404

    def test_invoices_from_other_facilities_are_not_listed(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        own = InvoiceFactory(facility=facility)
        InvoiceFactory(facility=other_facility)

        user = _user_with_permissions(facility, "billing.invoice.view")
        client.force_authenticate(user=user)
        response = client.get(reverse("billing:invoice-list"))

        returned_ids = {row["id"] for row in response.data["results"]}
        assert returned_ids == {str(own.pk)}

    def test_view_permission_does_not_grant_discount(self, client):
        facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        user = _user_with_permissions(facility, "billing.invoice.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:invoice-discount", args=[invoice.pk]),
            {"amount": "50.00"},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_discount_permission_can_apply_a_small_discount(self, client):
        facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
        )
        user = _user_with_permissions(facility, "billing.invoice.discount")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:invoice-discount", args=[invoice.pk]),
            {"amount": "50.00"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["discount"] == "50.00"

    def test_a_large_discount_without_the_elevated_permission_is_rejected(self, client):
        facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        user = _user_with_permissions(facility, "billing.invoice.discount")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:invoice-discount", args=[invoice.pk]),
            {"amount": "5000.00"},
            format="json",
        )
        assert response.status_code == 400

    @pytest.mark.smoke
    def test_a_large_discount_succeeds_with_the_elevated_permission(self, client):
        facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Major procedure",
            unit_price="10000.00",
        )
        user = _user_with_permissions(
            facility, "billing.invoice.discount", "billing.invoice.discount_approve"
        )
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:invoice-discount", args=[invoice.pk]),
            {"amount": "5000.00"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["discount"] == "5000.00"


class TestPaymentPermissionBoundary:
    def test_view_permission_does_not_grant_create(self, client):
        facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
        )
        user = _user_with_permissions(facility, "billing.payment.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:payment-list"),
            {"invoice": str(invoice.pk), "method": "cash", "amount": "500.00"},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_record_a_cash_payment(self, client):
        facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        add_line_item(
            invoice,
            source_module="opd",
            source_reference_id="00000000-0000-0000-0000-000000000001",
            description="Consultation fee",
            unit_price="500.00",
        )
        user = _user_with_permissions(facility, "billing.payment.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:payment-list"),
            {"invoice": str(invoice.pk), "method": "cash", "amount": "500.00"},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["received_by"] == user.pk

    def test_cannot_record_a_payment_against_an_invoice_in_another_facility(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        other_invoice = InvoiceFactory(facility=other_facility)
        user = _user_with_permissions(facility, "billing.payment.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:payment-list"),
            {"invoice": str(other_invoice.pk), "method": "cash", "amount": "500.00"},
            format="json",
        )
        assert response.status_code == 404

    def test_mpesa_is_not_a_valid_method_for_the_plain_payment_endpoint(self, client):
        facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        user = _user_with_permissions(facility, "billing.payment.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:payment-list"),
            {"invoice": str(invoice.pk), "method": "mpesa", "amount": "500.00"},
            format="json",
        )
        assert response.status_code == 400

    @pytest.mark.smoke
    def test_user_with_create_permission_can_initiate_an_stk_push(self, client):
        facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        user = _user_with_permissions(facility, "billing.payment.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:payment-mpesa-stk-push"),
            {"invoice": str(invoice.pk), "phone_number": "254712345678", "amount": "500.00"},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["status"] == "requested"


class TestMpesaCallback:
    @pytest.mark.smoke
    def test_the_callback_endpoint_does_not_require_authentication(self, client):
        facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        mpesa_transaction = initiate_mpesa_stk_push(
            invoice, phone_number="254712345678", amount="500.00"
        )

        response = client.post(
            reverse("billing:mpesa-transaction-callback"),
            {
                "checkout_request_id": mpesa_transaction.checkout_request_id,
                "success": True,
                "mpesa_receipt_number": "QGH7XYZ123",
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "confirmed"

    def test_the_callback_endpoint_404s_for_an_unknown_checkout_request_id(self, client):
        response = client.post(
            reverse("billing:mpesa-transaction-callback"),
            {"checkout_request_id": "does-not-exist", "success": True},
            format="json",
        )
        assert response.status_code == 404


class TestRefundPermissionBoundary:
    def test_view_permission_does_not_grant_create(self, client):
        facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        payment = PaymentFactory(invoice=invoice)
        user = _user_with_permissions(facility, "billing.refund.view")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:refund-list"),
            {
                "invoice": str(invoice.pk),
                "payment": str(payment.pk),
                "amount": "50.00",
                "reason": "x",
            },
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.smoke
    def test_user_with_create_permission_can_approve_a_refund_for_someone_elses_payment(
        self, client
    ):
        facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        cashier = UserFactory(facility=facility)
        payment = PaymentFactory(invoice=invoice, received_by=cashier, amount="100.00")
        accountant = _user_with_permissions(facility, "billing.refund.create")
        client.force_authenticate(user=accountant)

        response = client.post(
            reverse("billing:refund-list"),
            {
                "invoice": str(invoice.pk),
                "payment": str(payment.pk),
                "amount": "50.00",
                "reason": "Overcharged",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_the_cashier_cannot_approve_their_own_refund_via_the_api(self, client):
        facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        cashier = _user_with_permissions(facility, "billing.refund.create")
        payment = PaymentFactory(invoice=invoice, received_by=cashier, amount="100.00")
        client.force_authenticate(user=cashier)

        response = client.post(
            reverse("billing:refund-list"),
            {
                "invoice": str(invoice.pk),
                "payment": str(payment.pk),
                "amount": "50.00",
                "reason": "Self-approved",
            },
            format="json",
        )
        assert response.status_code == 400

    def test_cannot_refund_against_a_payment_in_another_facility(self, client):
        facility = FacilityFactory()
        other_facility = FacilityFactory()
        invoice = InvoiceFactory(facility=facility)
        other_invoice = InvoiceFactory(facility=other_facility)
        other_payment = PaymentFactory(invoice=other_invoice)
        user = _user_with_permissions(facility, "billing.refund.create")
        client.force_authenticate(user=user)

        response = client.post(
            reverse("billing:refund-list"),
            {
                "invoice": str(invoice.pk),
                "payment": str(other_payment.pk),
                "amount": "50.00",
                "reason": "x",
            },
            format="json",
        )
        assert response.status_code == 404
