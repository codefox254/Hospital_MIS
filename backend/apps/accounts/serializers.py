"""
JWT issuance (TRD §4.3): 15 min access token (from SIMPLE_JWT settings),
refresh lifetime chosen per `client_type` (web=7d, mobile=30d). MFA is
enforced here too, before any token is ever issued — verifying a TOTP code
is not something the frontend can be trusted to gate.
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts import mfa
from apps.accounts.constants import PRIVILEGED_ROLE_NAMES
from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Read-only, minimal fields — this backs staff pickers (the doctor
    select on scheduling/booking forms), not a user-management screen.
    No email/phone beyond what's already visible facility-wide, no role/
    permission data (that's `/auth/me/`'s job for the requester's own
    account, and admin-only for anyone else's — not built yet).
    """

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]
        read_only_fields = fields


REFRESH_LIFETIME_BY_CLIENT = {
    "web": timedelta(days=7),
    "mobile": timedelta(days=30),
}


def user_holds_privileged_role(user):
    return user.user_roles.filter(role__name__in=PRIVILEGED_ROLE_NAMES).exists()


class ClientAwareTokenObtainPairSerializer(TokenObtainPairSerializer):
    client_type = serializers.ChoiceField(
        choices=list(REFRESH_LIFETIME_BY_CLIENT), default="web", required=False
    )
    mfa_code = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        client_type = attrs.pop("client_type", "web")
        mfa_code = attrs.pop("mfa_code", "")

        data = super().validate(attrs)  # authenticates; raises on bad credentials / inactive user
        user = self.user

        if user.mfa_enabled:
            if not mfa.decrypt_secret_and_verify(user.mfa_secret_encrypted, mfa_code):
                raise AuthenticationFailed("A valid MFA code is required.", code="mfa_invalid")
        elif user_holds_privileged_role(user):
            raise AuthenticationFailed(
                "This role requires MFA. Complete MFA setup before logging in.",
                code="mfa_setup_required",
            )

        refresh = self.get_token(user)
        refresh.set_exp(lifetime=REFRESH_LIFETIME_BY_CLIENT[client_type])
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at"])

        return data
