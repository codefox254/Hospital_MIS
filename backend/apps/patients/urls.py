from rest_framework.routers import DefaultRouter

from apps.patients.views import PatientViewSet

app_name = "patients"

router = DefaultRouter()
router.register("patients", PatientViewSet, basename="patient")

urlpatterns = router.urls
