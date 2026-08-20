"""
Regression coverage for the standard error envelope (TRD §4.2). Caught a real
bug during the auth-engine build: reading exc.default_code (the exception
*class's* default) instead of the instance's actual `code=...` returns the
wrong value for any exception raised with an explicit code, e.g.
AuthenticationFailed("...", code="mfa_invalid") was surfacing as
"authentication_failed" instead of "mfa_invalid".
"""

from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import AuthenticationFailed as SimpleJWTAuthFailed

from apps.core.exceptions import standard_exception_handler


class _DummyView(APIView):
    pass


def _context():
    return {"view": _DummyView(), "request": None, "args": (), "kwargs": {}}


class TestStandardExceptionHandler:
    def test_explicit_instance_code_is_preserved_not_the_class_default(self):
        exc = AuthenticationFailed("A valid MFA code is required.", code="mfa_invalid")
        response = standard_exception_handler(exc, _context())

        assert response.data["error"]["code"] == "mfa_invalid"
        assert response.data["error"]["message"] == "A valid MFA code is required."

    def test_default_code_used_when_none_given(self):
        exc = AuthenticationFailed("Bad credentials.")
        response = standard_exception_handler(exc, _context())

        assert response.data["error"]["code"] == "authentication_failed"

    def test_field_validation_errors_populate_fields_not_message(self):
        exc = ValidationError({"email": ["This field is required."]})
        response = standard_exception_handler(exc, _context())

        assert response.data["error"]["fields"] == {"email": ["This field is required."]}
        assert response.data["error"]["message"] == "Validation failed."

    def test_envelope_always_has_exactly_the_three_keys(self):
        exc = ValidationError("Something went wrong.")
        response = standard_exception_handler(exc, _context())

        assert set(response.data["error"].keys()) == {"code", "message", "fields"}

    def test_simplejwt_exception_explicit_code_is_preserved(self):
        """
        djangorestframework-simplejwt's AuthenticationFailed (DetailDictMixin)
        serializes as {"detail": ..., "code": ...} and stores an explicit
        `code=...` as a plain dict value rather than on the ErrorDetail — a
        different shape than a plain DRF APIException. Regression test for a
        bug where this leaked "code" into `fields` and lost the real code.
        """
        exc = SimpleJWTAuthFailed("A valid MFA code is required.", code="mfa_invalid")
        response = standard_exception_handler(exc, _context())

        assert response.data["error"]["code"] == "mfa_invalid"
        assert response.data["error"]["message"] == "A valid MFA code is required."
        assert response.data["error"]["fields"] == {}
