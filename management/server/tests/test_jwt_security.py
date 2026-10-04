"""JWT regressions without database, model, Redis or object-store dependencies."""

import importlib
import importlib.util
import logging
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import jwt
from flask import Blueprint, Flask

SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parents[1]
sys.path.insert(0, str(SERVER_ROOT))

from jwt_config import configure_jwt, get_jwt_secret, validate_jwt_secret

# Public test fixtures only. Never use these values in a deployment.
DOTENV_SECRET = "test-dotenv-signing-key-0123456789abcdef"
ENV_SECRET = "test-environment-signing-key-abcdef0123456789"
ADMIN_PASSWORD = "test-admin-password-for-regressions"
USER = {"id": "admin", "username": "admin", "role": "admin", "tenant_id": None}
UNSET = object()


@contextmanager
def management_app(dotenv_secret=UNSET, environment_secret=UNSET,
                   environment_password=ADMIN_PASSWORD, dotenv_password=UNSET):
    """Load real app/auth/user-route code with only external services stubbed."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        server = root / "management" / "server"
        server.mkdir(parents=True)
        shutil.copyfile(SERVER_ROOT / "app.py", server / "app.py")
        (root / "docker").mkdir()
        dotenv_lines = []
        if dotenv_secret is not UNSET:
            dotenv_lines.append(f"MANAGEMENT_JWT_SECRET={dotenv_secret}")
        if dotenv_password is not UNSET:
            dotenv_lines.append(f"MANAGEMENT_ADMIN_PASSWORD={dotenv_password}")
        if dotenv_lines:
            (root / "docker" / ".env").write_text("\n".join(dotenv_lines) + "\n", encoding="utf-8")

        routes = types.ModuleType("routes")
        routes.__path__ = [str(SERVER_ROOT / "routes")]
        routes.users_bp = Blueprint("users", "routes", url_prefix="/api/v1/users")
        routes.register_routes = lambda app: app.register_blueprint(routes.users_bp)
        users_service = types.ModuleType("services.users.service")
        for name in (
            "authenticate_user", "get_users_with_pagination", "delete_user", "create_user",
            "update_user", "reset_user_password", "get_user_info_by_id",
        ):
            setattr(users_service, name, Mock())
        users_service.authenticate_user.return_value = (True, USER, None)
        users_service.get_user_info_by_id.return_value = dict(USER, roles=["admin"])

        with patch.dict(os.environ), patch.dict(sys.modules, {"routes": routes, "services.users.service": users_service}):
            os.environ.pop("MANAGEMENT_JWT_SECRET", None)
            os.environ.pop("MANAGEMENT_ADMIN_PASSWORD", None)
            if environment_password is not UNSET:
                os.environ["MANAGEMENT_ADMIN_PASSWORD"] = environment_password
            if environment_secret is not UNSET:
                os.environ["MANAGEMENT_JWT_SECRET"] = environment_secret
            sys.modules.pop("routes.users", None)
            sys.modules.pop("routes.users.routes", None)
            # Import both verifiers BEFORE dotenv: neither may capture a key.
            auth = importlib.import_module("services.auth.auth_utils")
            importlib.import_module("routes.users.routes")
            spec = importlib.util.spec_from_file_location("jwt_test_app", server / "app.py")
            module = importlib.util.module_from_spec(spec)
            previous_cwd = os.getcwd()
            try:
                os.chdir(root)
                with patch("logging.FileHandler", return_value=logging.NullHandler()):
                    spec.loader.exec_module(module)
                module.app.config["TESTING"] = True
                yield module, auth, users_service
            finally:
                os.chdir(previous_cwd)


class JwtConfigurationTests(unittest.TestCase):
    def test_rejects_missing_empty_short_and_whitespace_secrets(self):
        for secret in (None, "", " " * 40, "a" * 31, "a" * 31 + " ", " " + ENV_SECRET):
            with self.subTest(secret=secret), self.assertRaisesRegex(RuntimeError, "MANAGEMENT_JWT_SECRET"):
                validate_jwt_secret(secret)

    def test_rejects_shipped_defaults_and_long_placeholders(self):
        for secret in (
            "12345678", "20250409", "your-secret-key", "12345678" * 4, "20250409" * 4,
            "your-secret-key-must-be-at-least-32-characters",
            "YOUR_SUPER_SECRET_KEY_AT_LEAST_32_BYTES",
            "change_me_before_using_this_service_in_production",
            "replace-with-a-random-secret-of-at-least-32-bytes",
            "placeholder-key-for-management-only-0123456789",
            "default-secret-key-for-management-0123456789",
        ):
            with self.subTest(secret=secret), self.assertRaises(RuntimeError):
                validate_jwt_secret(secret)

    def test_error_never_discloses_configured_secret(self):
        secret = "change-me-sensitive-value-0123456789"
        with self.assertRaises(RuntimeError) as raised:
            validate_jwt_secret(secret)
        self.assertNotIn(secret, str(raised.exception))

    def test_length_is_measured_in_utf8_bytes(self):
        self.assertEqual(validate_jwt_secret("abcdefgh" * 4), "abcdefgh" * 4)
        self.assertEqual(validate_jwt_secret("é" * 16), "é" * 16)
        with self.assertRaises(RuntimeError):
            validate_jwt_secret("é" * 15)

    def test_configuration_is_app_scoped_and_snapshotted(self):
        first, second = Flask("first"), Flask("second")
        with patch.dict(os.environ, MANAGEMENT_JWT_SECRET=DOTENV_SECRET):
            configure_jwt(first)
        with patch.dict(os.environ, MANAGEMENT_JWT_SECRET=ENV_SECRET):
            configure_jwt(second)
            with first.app_context():
                self.assertEqual(get_jwt_secret(), DOTENV_SECRET)
            with second.app_context():
                self.assertEqual(get_jwt_secret(), ENV_SECRET)
        self.assertEqual(get_jwt_secret(first), DOTENV_SECRET)

    def test_startup_fails_without_a_secret(self):
        with self.assertRaisesRegex(RuntimeError, "MANAGEMENT_JWT_SECRET"):
            with management_app():
                self.fail("Startup must fail before serving requests")

    def test_invalid_environment_does_not_fall_back_to_valid_dotenv(self):
        for secret in ("", "12345678", "your-secret-key", "placeholder" * 4):
            with self.subTest(secret=secret), self.assertRaises(RuntimeError):
                with management_app(DOTENV_SECRET, secret):
                    self.fail("An explicitly invalid environment must not be overridden")


class JwtAuthenticationTests(unittest.TestCase):
    def assert_both_verifiers_accept(self, module, auth, token):
        headers = {"Authorization": f"Bearer {token}"}
        with module.app.test_request_context(headers=headers):
            self.assertEqual(auth.get_current_user_from_token()["user_id"], USER["id"])
        response = module.app.test_client().get("/api/v1/users/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["username"], USER["username"])

    def assert_both_verifiers_reject(self, module, auth, token):
        headers = {"Authorization": f"Bearer {token}"}
        with module.app.test_request_context(headers=headers):
            self.assertIsNone(auth.get_current_user_from_token())
        response = module.app.test_client().get("/api/v1/users/me", headers=headers)
        self.assertEqual(response.status_code, 401)

    def test_dotenv_key_signs_and_verifies_after_early_verifier_imports(self):
        with management_app(DOTENV_SECRET) as (module, auth, _):
            response = module.app.test_client().post("/api/v1/auth/login", json={"username": "admin", "password": "unused-test-password"})
            self.assertEqual(response.status_code, 200)
            token = response.json["data"]["token"]
            self.assertEqual(jwt.decode(token, DOTENV_SECRET, algorithms=["HS256"])["user_id"], USER["id"])
            self.assert_both_verifiers_accept(module, auth, token)

    def test_environment_takes_precedence_and_key_does_not_change_per_request(self):
        with management_app(DOTENV_SECRET, ENV_SECRET) as (module, auth, _):
            token = module.generate_token(USER)
            self.assertEqual(jwt.decode(token, ENV_SECRET, algorithms=["HS256"])["role"], "admin")
            with self.assertRaises(jwt.InvalidSignatureError):
                jwt.decode(token, DOTENV_SECRET, algorithms=["HS256"])
            os.environ["MANAGEMENT_JWT_SECRET"] = DOTENV_SECRET
            self.assert_both_verifiers_accept(module, auth, token)
            self.assert_both_verifiers_accept(module, auth, module.generate_token(USER))

    def test_forged_tokens_using_every_old_default_are_rejected(self):
        with management_app(DOTENV_SECRET) as (module, auth, service):
            for secret in ("12345678", "20250409", "your-secret-key"):
                with self.subTest(secret=secret):
                    claims = {"user_id": "admin", "username": "admin", "role": "admin", "tenant_id": None,
                              "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
                    token = jwt.encode(claims, secret, algorithm="HS256")
                    self.assert_both_verifiers_reject(module, auth, token)
            service.get_user_info_by_id.assert_not_called()

    def test_expired_malformed_and_wrong_algorithm_tokens_are_rejected(self):
        with management_app(DOTENV_SECRET) as (module, auth, service):
            claims = {"user_id": "admin", "username": "admin", "role": "admin", "tenant_id": None,
                      "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
            expired = jwt.encode(dict(claims, exp=datetime.now(timezone.utc) - timedelta(seconds=1)), DOTENV_SECRET, algorithm="HS256")
            wrong_algorithm = jwt.encode(claims, DOTENV_SECRET, algorithm="HS384")
            for token in (expired, wrong_algorithm, "not-a-jwt"):
                with self.subTest(token=token):
                    self.assert_both_verifiers_reject(module, auth, token)
            service.get_user_info_by_id.assert_not_called()


class JwtDeploymentTests(unittest.TestCase):
    def test_every_compose_variant_requires_an_explicit_key(self):
        for filename in ("docker/docker-compose.yml", "docker/docker-compose_gpu.yml", "management/docker-compose.yml"):
            with self.subTest(filename=filename):
                content = (REPO_ROOT / filename).read_text(encoding="utf-8")
                lines = [line.strip() for line in content.splitlines() if "MANAGEMENT_JWT_SECRET=" in line]
                self.assertEqual(len(lines), 1)
                self.assertTrue(lines[0].startswith("- MANAGEMENT_JWT_SECRET=${MANAGEMENT_JWT_SECRET:?"))
                self.assertNotIn(":-", lines[0])

    def test_example_env_files_do_not_ship_a_jwt_secret(self):
        for filename in ("docker/.env", "management/.env"):
            with self.subTest(filename=filename):
                lines = (REPO_ROOT / filename).read_text(encoding="utf-8").splitlines()
                assignments = [line for line in lines if line.startswith("MANAGEMENT_JWT_SECRET=")]
                self.assertEqual(assignments, ["MANAGEMENT_JWT_SECRET="])


if __name__ == "__main__":
    unittest.main()
