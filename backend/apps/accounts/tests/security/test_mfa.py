"""MFA setup/activate/enforcement (TRD §3.3, §4.3)."""

import pyotp
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts import mfa
from apps.accounts.factories import RoleFactory, UserFactory, UserRoleFactory

pytestmark = pytest.mark.django_db

TOKEN_URL = reverse("accounts:token_obtain_pair")
MFA_SETUP_URL = reverse("accounts:mfa_setup")
MFA_ACTIVATE_URL = reverse("accounts:mfa_activate")

RAW_PASSWORD = "Str0ngP@ssword!23"


@pytest.fixture
def client():
    return APIClient()


class TestPrivilegedRoleRequiresMfaSetup:
    def test_privileged_role_without_mfa_cannot_log_in(self, client):
        user = UserFactory(email="admin@fdo-hospital.test", password=RAW_PASSWORD)
        UserRoleFactory(user=user, role=RoleFactory(name="Administrator"))

        response = client.post(
            TOKEN_URL,
            {"email": "admin@fdo-hospital.test", "password": RAW_PASSWORD},
            format="json",
        )
        assert response.status_code == 401
        assert response.data["error"]["code"] == "mfa_setup_required"

    def test_non_privileged_role_logs_in_without_mfa(self, client):
        user = UserFactory(email="nurse@fdo-hospital.test", password=RAW_PASSWORD)
        UserRoleFactory(user=user, role=RoleFactory(name="Nurse"))

        response = client.post(
            TOKEN_URL,
            {"email": "nurse@fdo-hospital.test", "password": RAW_PASSWORD},
            format="json",
        )
        assert response.status_code == 200


class TestMfaSetupAndActivateFlow:
    def test_setup_then_activate_enables_mfa(self, client):
        user = UserFactory(email="admin@fdo-hospital.test", password=RAW_PASSWORD)
        UserRoleFactory(user=user, role=RoleFactory(name="Administrator"))

        setup = client.post(
            MFA_SETUP_URL,
            {"email": "admin@fdo-hospital.test", "password": RAW_PASSWORD},
            format="json",
        )
        assert setup.status_code == 200
        secret = setup.data["secret"]

        code = pyotp.TOTP(secret).now()
        activate = client.post(
            MFA_ACTIVATE_URL,
            {"email": "admin@fdo-hospital.test", "password": RAW_PASSWORD, "code": code},
            format="json",
        )
        assert activate.status_code == 200
        assert activate.data["mfa_enabled"] is True

        user.refresh_from_db()
        assert user.mfa_enabled is True

    def test_activate_with_wrong_code_is_rejected(self, client):
        UserFactory(email="admin@fdo-hospital.test", password=RAW_PASSWORD)
        client.post(
            MFA_SETUP_URL,
            {"email": "admin@fdo-hospital.test", "password": RAW_PASSWORD},
            format="json",
        )
        response = client.post(
            MFA_ACTIVATE_URL,
            {"email": "admin@fdo-hospital.test", "password": RAW_PASSWORD, "code": "000000"},
            format="json",
        )
        assert response.status_code == 400

    def test_activate_without_setup_is_rejected(self, client):
        UserFactory(email="admin@fdo-hospital.test", password=RAW_PASSWORD)
        response = client.post(
            MFA_ACTIVATE_URL,
            {"email": "admin@fdo-hospital.test", "password": RAW_PASSWORD, "code": "123456"},
            format="json",
        )
        assert response.status_code == 400

    def test_setup_requires_correct_password(self, client):
        UserFactory(email="admin@fdo-hospital.test", password=RAW_PASSWORD)
        response = client.post(
            MFA_SETUP_URL, {"email": "admin@fdo-hospital.test", "password": "wrong"}, format="json"
        )
        assert response.status_code == 400


class TestMfaEnforcedAtLogin:
    def _enable_mfa(self, user, raw_password="dummy"):
        secret = mfa.generate_secret()
        user.mfa_secret_encrypted = mfa.encrypt_secret(secret)
        user.mfa_enabled = True
        user.save(update_fields=["mfa_secret_encrypted", "mfa_enabled"])
        return secret

    def test_login_without_code_is_rejected_when_mfa_enabled(self, client):
        user = UserFactory(email="admin@fdo-hospital.test", password=RAW_PASSWORD)
        self._enable_mfa(user)

        response = client.post(
            TOKEN_URL,
            {"email": "admin@fdo-hospital.test", "password": RAW_PASSWORD},
            format="json",
        )
        assert response.status_code == 401
        assert response.data["error"]["code"] == "mfa_invalid"

    def test_login_with_valid_code_succeeds(self, client):
        user = UserFactory(email="admin@fdo-hospital.test", password=RAW_PASSWORD)
        secret = self._enable_mfa(user)

        response = client.post(
            TOKEN_URL,
            {
                "email": "admin@fdo-hospital.test",
                "password": RAW_PASSWORD,
                "mfa_code": pyotp.TOTP(secret).now(),
            },
            format="json",
        )
        assert response.status_code == 200
        assert "access" in response.data

    def test_login_with_invalid_code_is_rejected(self, client):
        user = UserFactory(email="admin@fdo-hospital.test", password=RAW_PASSWORD)
        self._enable_mfa(user)

        response = client.post(
            TOKEN_URL,
            {
                "email": "admin@fdo-hospital.test",
                "password": RAW_PASSWORD,
                "mfa_code": "000000",
            },
            format="json",
        )
        assert response.status_code == 401
