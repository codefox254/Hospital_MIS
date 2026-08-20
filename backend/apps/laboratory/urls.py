from rest_framework.routers import DefaultRouter

from apps.laboratory.views import (
    LabOrderItemViewSet,
    LabOrderViewSet,
    LabResultViewSet,
    LabSampleViewSet,
)

app_name = "laboratory"

router = DefaultRouter()
router.register("lab-orders", LabOrderViewSet, basename="lab-order")
router.register("lab-order-items", LabOrderItemViewSet, basename="lab-order-item")
router.register("samples", LabSampleViewSet, basename="sample")
router.register("results", LabResultViewSet, basename="result")

urlpatterns = router.urls
