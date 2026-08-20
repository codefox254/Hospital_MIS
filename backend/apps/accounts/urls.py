from django.urls import path

from apps.accounts.views import (
    MeView,
    MFAActivateView,
    MFASetupView,
    TokenObtainPairView,
    TokenRefreshView,
)

app_name = "accounts"

urlpatterns = [
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("mfa/setup/", MFASetupView.as_view(), name="mfa_setup"),
    path("mfa/activate/", MFAActivateView.as_view(), name="mfa_activate"),
    path("me/", MeView.as_view(), name="me"),
]
