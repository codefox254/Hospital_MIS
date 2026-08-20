from rest_framework.routers import DefaultRouter

from apps.opd.views import (
    ConsultationAddendumViewSet,
    ConsultationViewSet,
    DiagnosisViewSet,
    VisitViewSet,
    VitalsViewSet,
)

app_name = "opd"

router = DefaultRouter()
router.register("visits", VisitViewSet, basename="visit")
router.register("vitals", VitalsViewSet, basename="vitals")
router.register("consultations", ConsultationViewSet, basename="consultation")
router.register("diagnoses", DiagnosisViewSet, basename="diagnosis")
router.register("addenda", ConsultationAddendumViewSet, basename="addendum")

urlpatterns = router.urls
