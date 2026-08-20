"""
Auth endpoints (TRD §4.3). MFA setup/activate deliberately authenticate via
email+password rather than requiring an existing JWT — a privileged user
whose role requires MFA has no other way to ever obtain a session, since
`ClientAwareTokenObtainPairSerializer` refuses to issue tokens to a
privileged, not-yet-MFA-enabled account (see serializers.py).
"""

from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from apps.accounts import mfa
from apps.accounts.serializers import ClientAwareTokenObtainPairSerializer
from apps.accounts.services import get_effective_permission_codes


class TokenObtainPairView(BaseTokenObtainPairView):
    serializer_class = ClientAwareTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class TokenRefreshView(BaseTokenRefreshView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class CredentialVerifyingSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        request = self.context.get("request")
        user = authenticate(request=request, email=attrs["email"], password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("Invalid credentials.", code="invalid_credentials")
        attrs["user"] = user
        return attrs


class MFASetupResponseSerializer(serializers.Serializer):
    secret = serializers.CharField()
    provisioning_uri = serializers.CharField()


class MFAActivateResponseSerializer(serializers.Serializer):
    mfa_enabled = serializers.BooleanField()


class MFASetupView(APIView):
    """Issues a new (not-yet-active) TOTP secret. Calling this again before
    activation replaces the pending secret — only one can be pending."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=CredentialVerifyingSerializer, responses=MFASetupResponseSerializer)
    def post(self, request):
        serializer = CredentialVerifyingSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        secret = mfa.generate_secret()
        user.mfa_secret_encrypted = mfa.encrypt_secret(secret)
        user.save(update_fields=["mfa_secret_encrypted"])

        return Response(
            {
                "secret": secret,
                "provisioning_uri": mfa.provisioning_uri(secret, user.email),
            },
            status=status.HTTP_200_OK,
        )


class MFAActivateSerializer(CredentialVerifyingSerializer):
    code = serializers.CharField()


class MFAActivateView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=MFAActivateSerializer, responses=MFAActivateResponseSerializer)
    def post(self, request):
        serializer = MFAActivateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        code = serializer.validated_data["code"]

        if not user.mfa_secret_encrypted:
            raise serializers.ValidationError(
                "Call MFA setup before activating.", code="mfa_not_set_up"
            )
        if not mfa.decrypt_secret_and_verify(user.mfa_secret_encrypted, code):
            raise serializers.ValidationError("Invalid MFA code.", code="mfa_invalid")

        user.mfa_enabled = True
        user.save(update_fields=["mfa_enabled"])
        return Response({"mfa_enabled": True}, status=status.HTTP_200_OK)


class MeView(APIView):
    """
    GET /api/v1/auth/me/ — not in the original TRD/Data Dictionary
    endpoint list, but the web console (TRD §5.1) needs it: route guards
    have to check permissions *before* rendering, which means the
    frontend needs to know its own effective permission set on load.
    Nothing here is a new authorization decision — it just exposes what
    apps.accounts.services.get_effective_permission_codes() (the same
    function HasModulePermission itself calls on every request) already
    computes server-side, so the client's route-gating and the server's
    actual enforcement can never drift out of sync.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "facility": {
                    "id": str(user.facility_id),
                    "name": user.facility.name,
                    "code": user.facility.code,
                },
                "mfa_enabled": user.mfa_enabled,
                "permissions": sorted(get_effective_permission_codes(user)),
            }
        )
