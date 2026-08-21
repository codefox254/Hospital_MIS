from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.core.views import DepartmentViewSet, FacilityViewSet, PlatformStatsView

app_name = "core"

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("facilities", FacilityViewSet, basename="facility")

urlpatterns = [
    path("platform-stats/", PlatformStatsView.as_view(), name="platform-stats"),
] + router.urls
