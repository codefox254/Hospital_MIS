from rest_framework.routers import DefaultRouter

from apps.core.views import DepartmentViewSet

app_name = "core"

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")

urlpatterns = router.urls
