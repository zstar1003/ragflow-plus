"""Management authentication configuration, initialized after dotenv is loaded."""

import os
import re

from flask import current_app

JWT_SECRET_ENV = "MANAGEMENT_JWT_SECRET"
MIN_SECRET_BYTES = 32
_KNOWN_DEFAULTS = {"12345678", "20250409", "your-secret-key"}
_PLACEHOLDER_MARKERS = (
    "changeme",
    "replaceme",
    "replacewith",
    "placeholder",
    "defaultsecret",
    "examplesecret",
)


def validate_jwt_secret(secret):
    """Reject missing, short or recognizable example keys without logging them."""
    error = (
        "MANAGEMENT_JWT_SECRET must be explicitly set to a unique random secret "
        "of at least 32 UTF-8 bytes; default and placeholder values are not allowed. "
        "See docs/security/jwt-secret.md for setup and migration instructions."
    )
    if not isinstance(secret, str) or len(secret.strip().encode("utf-8")) < MIN_SECRET_BYTES:
        raise RuntimeError(error)

    normalized = re.sub(r"[^a-z0-9]", "", secret.lower())
    if (
        secret != secret.strip()
        or secret.lower() in _KNOWN_DEFAULTS
        or any(marker in normalized for marker in _PLACEHOLDER_MARKERS)
        or (normalized.startswith("your") and "secret" in normalized)
        or any(secret == default * (len(secret) // len(default)) for default in _KNOWN_DEFAULTS)
    ):
        raise RuntimeError(error)
    return secret


def configure_jwt(app):
    """Validate environment configuration before any routes are registered."""
    app.config[JWT_SECRET_ENV] = validate_jwt_secret(os.environ.get(JWT_SECRET_ENV))


def get_jwt_secret(app=None):
    """Use the same startup-validated key for signing and every verifier."""
    if app is None:
        app = current_app
    return app.config[JWT_SECRET_ENV]


ADMIN_PASSWORD_ENV = "MANAGEMENT_ADMIN_PASSWORD"
MIN_ADMIN_PASSWORD_LENGTH = 12
_KNOWN_ADMIN_DEFAULTS = {
    "12345678", "20250409", "password", "admin", "admin123",
    "password1234", "password12345", "password123456", "password12345678",
}
_ADMIN_PASSWORD_PLACEHOLDERS = {
    "changeme", "changethispassword", "pleasechangethispassword",
    "yourpassword", "youradminpassword", "youradministratorpassword",
    "yourpasswordhere", "youradminpasswordhere", "replacethispassword",
    "replaceme", "replacewithastrongpassword", "replacewithauniquepassword",
    "defaultpassword", "examplepassword", "placeholderpassword",
    "123456789012", "1234567890123456", "admin12345678",
}


def validate_admin_password(password):
    """Require a non-default password; allow long passphrases without composition rules."""
    error = (
        "MANAGEMENT_ADMIN_PASSWORD must be explicitly set to a unique password "
        "of at least 12 characters; default and placeholder values are not allowed. "
        "See docs/security/jwt-secret.md for setup and migration instructions."
    )
    if not isinstance(password, str) or len(password.strip()) < MIN_ADMIN_PASSWORD_LENGTH:
        raise RuntimeError(error)
    normalized = re.sub(r"[^a-z0-9]", "", password.lower())
    if (
        normalized in _ADMIN_PASSWORD_PLACEHOLDERS
        or password.lower() in _KNOWN_ADMIN_DEFAULTS
        or any(password.lower() == default * (len(password) // len(default)) for default in _KNOWN_ADMIN_DEFAULTS)
    ):
        raise RuntimeError(error)
    return password


def configure_admin_password(app):
    """Fail startup before loading routes when administrator credentials are unsafe."""
    app.config[ADMIN_PASSWORD_ENV] = validate_admin_password(os.environ.get(ADMIN_PASSWORD_ENV))


def get_admin_password():
    """Read the startup-validated credential instead of capturing an import-time default."""
    return current_app.config[ADMIN_PASSWORD_ENV]
