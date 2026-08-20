"""
JWT auth endpoint tests (TRD §4.3). Negative cases are written first per
CLAUDE.md §4.3 — a permission/auth boundary is worth proving fails closed
before proving it works at all.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import UserFactory

pytestmark = pytest.mark.django_db

TOKEN_URL = reverse("accounts:token_obtain_pair")
REFRESH_URL = reverse("accounts:token_refresh")

RAW_PASSWORD = "Str0ngP@ssword!23"


@pytest.fixture
def client():
    return APIClient()


class TestLoginNegativeCases:
    def test_wrong_password_is_rejected(self, client):
        UserFactory(email="staff@fdo-hospital.test", password=RAW_PASSWORD)
        response = client.post(
            TOKEN_URL, {"email": "staff@fdo-hospital.test", "password": "wrong"}, format="json"
        )
        assert response.status_code == 401
        assert response.data["error"]["code"]

    def test_terminated_user_cannot_obtain_a_token(self, client):
        """BRD edge case: termination revokes access immediately."""
        UserFactory(email="exstaff@fdo-hospital.test", password=RAW_PASSWORD, is_active=False)
        response = client.post(
            TOKEN_URL,
            {"email": "exstaff@fdo-hospital.test", "password": RAW_PASSWORD},
            format="json",
        )
        assert response.status_code == 401

    def test_unknown_email_is_rejected(self, client):
        response = client.post(
            TOKEN_URL, {"email": "nobody@fdo-hospital.test", "password": "x"}, format="json"
        )
        assert response.status_code == 401

    def test_error_envelope_shape_on_auth_failure(self, client):
        response = client.post(
            TOKEN_URL, {"email": "nobody@fdo-hospital.test", "password": "x"}, format="json"
        )
        assert set(response.data.keys()) == {"error"}
        assert set(response.data["error"].keys()) == {"code", "message", "fields"}


class TestLoginPositiveCases:
    @pytest.mark.smoke
    def test_correct_credentials_issue_access_and_refresh_tokens(self, client):
        UserFactory(email="staff@fdo-hospital.test", password=RAW_PASSWORD)
        response = client.post(
            TOKEN_URL,
            {"email": "staff@fdo-hospital.test", "password": RAW_PASSWORD},
            format="json",
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_web_client_gets_7_day_refresh_lifetime(self, client):
        import jwt as pyjwt

        UserFactory(email="staff@fdo-hospital.test", password=RAW_PASSWORD)
        response = client.post(
            TOKEN_URL,
            {
                "email": "staff@fdo-hospital.test",
                "password": RAW_PASSWORD,
                "client_type": "web",
            },
            format="json",
        )
        payload = pyjwt.decode(response.data["refresh"], options={"verify_signature": False})
        lifetime_days = (payload["exp"] - payload["iat"]) / 86400
        assert 6.9 < lifetime_days < 7.1

    def test_mobile_client_gets_30_day_refresh_lifetime(self, client):
        import jwt as pyjwt

        UserFactory(email="staff@fdo-hospital.test", password=RAW_PASSWORD)
        response = client.post(
            TOKEN_URL,
            {
                "email": "staff@fdo-hospital.test",
                "password": RAW_PASSWORD,
                "client_type": "mobile",
            },
            format="json",
        )
        payload = pyjwt.decode(response.data["refresh"], options={"verify_signature": False})
        lifetime_days = (payload["exp"] - payload["iat"]) / 86400
        assert 29.9 < lifetime_days < 30.1

    def test_login_updates_last_login_at(self, client):
        user = UserFactory(email="staff@fdo-hospital.test", password=RAW_PASSWORD)
        assert user.last_login_at is None
        client.post(
            TOKEN_URL,
            {"email": "staff@fdo-hospital.test", "password": RAW_PASSWORD},
            format="json",
        )
        user.refresh_from_db()
        assert user.last_login_at is not None

    def test_refresh_token_issues_a_new_access_token(self, client):
        UserFactory(email="staff@fdo-hospital.test", password=RAW_PASSWORD)
        login = client.post(
            TOKEN_URL,
            {"email": "staff@fdo-hospital.test", "password": RAW_PASSWORD},
            format="json",
        )
        response = client.post(REFRESH_URL, {"refresh": login.data["refresh"]}, format="json")
        assert response.status_code == 200
        assert "access" in response.data


class TestAuthThrottling:
    def test_repeated_failed_logins_are_throttled(self, client):
        UserFactory(email="staff@fdo-hospital.test", password=RAW_PASSWORD)
        responses = [
            client.post(
                TOKEN_URL, {"email": "staff@fdo-hospital.test", "password": "wrong"}, format="json"
            )
            for _ in range(15)
        ]
        assert any(r.status_code == 429 for r in responses)
