"""Administrator credential configuration and login regressions."""

import importlib
import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

import jwt
from flask import Flask

from test_jwt_security import ADMIN_PASSWORD, DOTENV_SECRET, SERVER_ROOT, REPO_ROOT, UNSET, management_app
from jwt_config import configure_admin_password, get_admin_password, validate_admin_password


def stub_module(name, **attributes):
    module = types.ModuleType(name)
    module.__dict__.update(attributes)
    return module


class AdminPasswordTests(unittest.TestCase):
    def test_missing_blank_short_defaults_and_placeholders_are_rejected(self):
        for password in (
            None, "", " " * 20, "abcdefghijk", "é" * 11, "12345678", "password",
            "12345678" * 2, "admin" * 4, "password" * 2,
            "your-admin-password", "your-admin-password-here", "your_password", "change-this-password",
            "password123456",
            "please-change-this-password", "replace-with-a-strong-password",
            "replace_with_a_unique_password", "default-password", "example-password",
            "placeholder-password", "123456789012", "admin12345678",
        ):
            with self.subTest(password=password), self.assertRaisesRegex(RuntimeError, "MANAGEMENT_ADMIN_PASSWORD"):
                validate_admin_password(password)

    def test_nondefault_passwords_and_passphrases_are_preserved_without_composition_rules(self):
        for password in (
            "abcdefghijk!", ADMIN_PASSWORD, "lantern orchard river meadow",
            "青山绿水明月清风春花秋实星河", "  lantern orchard river meadow  ",
            "E4" * 100,
        ):
            with self.subTest(password=password):
                self.assertEqual(validate_admin_password(password), password)

    def test_validation_error_does_not_echo_the_password(self):
        with self.assertRaises(RuntimeError) as raised:
            validate_admin_password("your-admin-password")
        self.assertNotIn("your-admin-password", str(raised.exception))

    def test_startup_fails_when_admin_password_is_not_configured(self):
        with self.assertRaisesRegex(RuntimeError, "MANAGEMENT_ADMIN_PASSWORD"):
            with management_app(DOTENV_SECRET, environment_password=UNSET):
                self.fail("Startup must fail without an administrator password")

    def test_invalid_environment_password_is_not_replaced_by_dotenv(self):
        for password in ("", " " * 20, "12345678", "your-admin-password"):
            with self.subTest(password=password), self.assertRaisesRegex(RuntimeError, "MANAGEMENT_ADMIN_PASSWORD"):
                with management_app(DOTENV_SECRET, environment_password=password, dotenv_password=ADMIN_PASSWORD):
                    self.fail("Explicit invalid environment configuration must fail closed")

    def test_dotenv_password_is_loaded_and_environment_takes_precedence(self):
        with management_app(DOTENV_SECRET, environment_password=UNSET, dotenv_password=ADMIN_PASSWORD) as (module, _, _):
            with module.app.app_context():
                self.assertEqual(get_admin_password(), ADMIN_PASSWORD)
        environment_password = "test-environment-admin-password"
        with management_app(DOTENV_SECRET, environment_password=environment_password, dotenv_password=ADMIN_PASSWORD) as (module, _, _):
            with module.app.app_context():
                self.assertEqual(get_admin_password(), environment_password)

    def test_password_is_app_scoped_and_not_read_again_for_each_request(self):
        first, second = Flask("first-admin"), Flask("second-admin")
        with patch.dict(os.environ, MANAGEMENT_ADMIN_PASSWORD=ADMIN_PASSWORD):
            configure_admin_password(first)
        with patch.dict(os.environ, MANAGEMENT_ADMIN_PASSWORD="another-regression-test-password"):
            configure_admin_password(second)
            with first.app_context():
                self.assertEqual(get_admin_password(), ADMIN_PASSWORD)
            with second.app_context():
                self.assertEqual(get_admin_password(), "another-regression-test-password")

    def test_real_admin_login_uses_validated_password_and_rejects_old_default(self):
        # Load the real authentication service before any password is configured.
        # Only database and unrelated cryptographic helpers are stubbed.
        namespace = "_admin_security_services"
        package = stub_module(namespace)
        package.__path__ = [str(SERVER_ROOT / "services")]
        connector = stub_module("mysql.connector", connect=Mock(side_effect=AssertionError("Admin login must not query a database")))
        stubs = {
            namespace: package,
            "mysql": stub_module("mysql", connector=connector),
            "mysql.connector": connector,
            "pytz": stub_module("pytz"),
            "database": stub_module("database", DB_CONFIG={}),
            "utils": stub_module("utils", generate_uuid=Mock(), encrypt_password=Mock(), verify_password=Mock()),
        }
        with patch.dict(os.environ, MANAGEMENT_ADMIN_USERNAME="admin"), patch.dict(sys.modules, stubs):
            os.environ.pop("MANAGEMENT_ADMIN_PASSWORD", None)
            service = importlib.import_module(f"{namespace}.users.service")
            with management_app(DOTENV_SECRET) as (module, _, _):
                module.authenticate_user = service.authenticate_user
                client = module.app.test_client()
                for password in ("12345678", "your-admin-password", "wrong-regression-password"):
                    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": password})
                    self.assertEqual(response.status_code, 400)
                    self.assertNotIn("data", response.json)
                # Runtime environment changes cannot silently switch credentials.
                os.environ["MANAGEMENT_ADMIN_PASSWORD"] = "changed-environment-password"
                response = client.post("/api/v1/auth/login", json={"username": "admin", "password": ADMIN_PASSWORD})
                self.assertEqual(response.status_code, 200)
                claims = jwt.decode(response.json["data"]["token"], DOTENV_SECRET, algorithms=["HS256"])
                self.assertEqual(claims["role"], "admin")
                response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "changed-environment-password"})
                self.assertEqual(response.status_code, 400)
                connector.connect.assert_not_called()

    def test_deployment_examples_never_supply_a_default_admin_password(self):
        for filename in ("docker/.env", "management/.env"):
            with self.subTest(filename=filename):
                lines = (REPO_ROOT / filename).read_text(encoding="utf-8").splitlines()
                self.assertEqual([line for line in lines if line.startswith("MANAGEMENT_ADMIN_PASSWORD=")], ["MANAGEMENT_ADMIN_PASSWORD="])
        for filename in ("docker/docker-compose.yml", "docker/docker-compose_gpu.yml", "management/docker-compose.yml"):
            with self.subTest(filename=filename):
                lines = (REPO_ROOT / filename).read_text(encoding="utf-8").splitlines()
                assignments = [line.strip() for line in lines if "MANAGEMENT_ADMIN_PASSWORD=" in line]
                self.assertEqual(len(assignments), 1)
                self.assertTrue(assignments[0].startswith("- MANAGEMENT_ADMIN_PASSWORD=${MANAGEMENT_ADMIN_PASSWORD:?"))
                self.assertNotIn(":-", assignments[0])


if __name__ == "__main__":
    unittest.main()
