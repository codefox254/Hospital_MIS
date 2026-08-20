"""TOTP-based MFA (TRD §4.3) — secrets are Fernet-encrypted at rest, never stored
or logged in plaintext."""

import pyotp
from cryptography.fernet import Fernet
from django.conf import settings


def _fernet():
    key = settings.MFA_SECRET_ENCRYPTION_KEY
    return Fernet(key.encode() if isinstance(key, str) else key)


def generate_secret():
    return pyotp.random_base32()


def encrypt_secret(secret):
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(encrypted_secret):
    return _fernet().decrypt(encrypted_secret.encode()).decode()


def provisioning_uri(secret, email, issuer="FDO Hospital MIS"):
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_code(secret, code):
    if not code:
        return False
    return pyotp.totp.TOTP(secret).verify(code, valid_window=1)


def decrypt_secret_and_verify(encrypted_secret, code):
    if not encrypted_secret or not code:
        return False
    return verify_code(decrypt_secret(encrypted_secret), code)
