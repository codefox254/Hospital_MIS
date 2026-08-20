from rest_framework.routers import DefaultRouter

from apps.pharmacy.views import (
    DispenseRecordViewSet,
    DrugViewSet,
    PrescriptionItemViewSet,
    PrescriptionViewSet,
    StockBatchViewSet,
)

app_name = "pharmacy"

router = DefaultRouter()
router.register("drugs", DrugViewSet, basename="drug")
router.register("stock-batches", StockBatchViewSet, basename="stock-batch")
router.register("prescriptions", PrescriptionViewSet, basename="prescription")
router.register("prescription-items", PrescriptionItemViewSet, basename="prescription-item")
router.register("dispense-records", DispenseRecordViewSet, basename="dispense-record")

urlpatterns = router.urls
