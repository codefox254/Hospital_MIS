from rest_framework.routers import DefaultRouter

from apps.audit.views import AuditLogEntryViewSet

app_name = "audit"

router = DefaultRouter()
router.register("log-entries", AuditLogEntryViewSet, basename="log-entry")

urlpatterns = router.urls
