from django.contrib import admin

from apps.billing.models import Invoice, InvoiceLineItem, MpesaTransaction, Payment, Refund


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "patient", "status", "total", "balance")
    list_filter = ("facility", "status")
    search_fields = ("invoice_number",)


@admin.register(InvoiceLineItem)
class InvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "source_module", "description", "quantity", "amount")
    list_filter = ("source_module",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "method", "amount", "status", "received_at")
    list_filter = ("method", "status")


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ("checkout_request_id", "payment", "phone_number", "status")
    list_filter = ("status",)


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("invoice", "payment", "amount", "approved_by", "approved_at")
