from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/core/", include("apps.core.urls")),
    path("api/v1/audit/", include("apps.audit.urls")),
    path("api/v1/patients/", include("apps.patients.urls")),
    path("api/v1/appointments/", include("apps.appointments.urls")),
    path("api/v1/opd/", include("apps.opd.urls")),
    path("api/v1/laboratory/", include("apps.laboratory.urls")),
    path("api/v1/pharmacy/", include("apps.pharmacy.urls")),
    path("api/v1/billing/", include("apps.billing.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
