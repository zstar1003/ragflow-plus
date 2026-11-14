"""Ensure every service in both deployment variants has bounded Docker logs."""

from pathlib import Path
import unittest

import yaml


DOCKER = Path(__file__).resolve().parents[1]
FILES = ("docker-compose.yml", "docker-compose_gpu.yml", "docker-compose-base.yml")


class DockerLoggingTests(unittest.TestCase):
    def test_all_services_have_bounded_json_logs(self):
        expected = {
            "driver": "json-file",
            "options": {"max-size": "10m", "max-file": "5"},
        }
        for filename in FILES:
            with self.subTest(file=filename):
                config = yaml.safe_load((DOCKER / filename).read_text())
                self.assertTrue(config["services"])
                for service, definition in config["services"].items():
                    with self.subTest(service=service):
                        self.assertEqual(definition.get("logging"), expected)

    def test_variants_include_bounded_dependency_services(self):
        for filename in FILES[:2]:
            config = yaml.safe_load((DOCKER / filename).read_text())
            self.assertIn("./docker-compose-base.yml", config["include"])


if __name__ == "__main__":
    unittest.main()
