from rest_framework.routers import DefaultRouter

from apps.patients.views import (
    AllergyViewSet,
    ChronicConditionViewSet,
    ConsentViewSet,
    EmergencyContactViewSet,
    GuardianViewSet,
    PatientInsuranceViewSet,
    PatientViewSet,
)

app_name = "patients"

router = DefaultRouter()
router.register("patients", PatientViewSet, basename="patient")
router.register("guardians", GuardianViewSet, basename="guardian")
router.register("emergency-contacts", EmergencyContactViewSet, basename="emergency-contact")
router.register("allergies", AllergyViewSet, basename="allergy")
router.register("chronic-conditions", ChronicConditionViewSet, basename="chronic-condition")
router.register("consents", ConsentViewSet, basename="consent")
router.register("insurance-policies", PatientInsuranceViewSet, basename="insurance-policy")

urlpatterns = router.urls
