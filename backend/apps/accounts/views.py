"""
Auth endpoints (TRD §4.3). MFA setup/activate deliberately authenticate via
email+password rather than requiring an existing JWT — a privileged user
whose role requires MFA has no other way to ever obtain a session, since
`ClientAwareTokenObtainPairSerializer` refuses to issue tokens to a
privileged, not-yet-MFA-enabled account (see serializers.py).
"""

from django.contrib.auth import authenticate
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from apps.accounts import mfa
from apps.accounts.models import User
from apps.accounts.permissions import HasModulePermission
from apps.accounts.serializers import (
    ClientAwareTokenObtainPairSerializer,
    CreateUserSerializer,
    UserSerializer,
)
from apps.accounts.services import create_user_with_role, get_effective_permission_codes


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


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """`list`/`retrieve` back staff pickers (the doctor select on
    scheduling/booking forms) — see UserSerializer's docstring for what
    that deliberately doesn't expose. `create` is the admin-onboarding
    path: a Facility Admin adding their own staff, or a Super Admin
    creating a new facility's first admin account — see
    CreateUserSerializer and create() below for the facility-scoping
    enforcement that split makes necessary."""

    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "accounts.user.view",
        "retrieve": "accounts.user.view",
        "create": "accounts.user.create",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = []
    queryset = User.objects.none()

    def get_serializer_class(self):
        if self.action == "create":
            return CreateUserSerializer
        return UserSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()
        return User.objects.filter(facility=self.request.user.facility, is_active=True)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        requester = request.user
        is_platform_admin = "core.facility.create" in get_effective_permission_codes(requester)
        if is_platform_admin:
            target_facility = serializer.validated_data.get("facility")
            if target_facility is None:
                raise serializers.ValidationError(
                    {"facility": "Required when creating a user as a platform admin."}
                )
        else:
            # Never trust a non-platform-admin's payload for this — force
            # their own facility regardless of what was submitted.
            target_facility = requester.facility

        user = create_user_with_role(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            first_name=serializer.validated_data.get("first_name", ""),
            last_name=serializer.validated_data.get("last_name", ""),
            phone=serializer.validated_data.get("phone", ""),
            facility=target_facility,
            role=serializer.validated_data.get("role"),
            actor=requester,
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
