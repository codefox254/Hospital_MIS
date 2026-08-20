from rest_framework.routers import DefaultRouter

from apps.billing.views import (
    InvoiceLineItemViewSet,
    InvoiceViewSet,
    MpesaTransactionViewSet,
    PaymentViewSet,
    RefundViewSet,
)

app_name = "billing"

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("line-items", InvoiceLineItemViewSet, basename="line-item")
router.register("payments", PaymentViewSet, basename="payment")
router.register("mpesa-transactions", MpesaTransactionViewSet, basename="mpesa-transaction")
router.register("refunds", RefundViewSet, basename="refund")

urlpatterns = router.urls
