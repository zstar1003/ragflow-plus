"""Render only: never connect to a daemon or start/modify containers."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
VARIANTS = ('docker-compose.yml', 'docker-compose_gpu.yml')


class ComposeDependencyTests(unittest.TestCase):
    def test_required_elasticsearch_is_not_optional(self):
        base = yaml.safe_load((ROOT / 'docker/docker-compose-base.yml').read_text())
        self.assertNotIn('profiles', base['services']['es01'])
        self.assertNotIn('infinity', base['services'])
        for variant in VARIANTS:
            config = yaml.safe_load((ROOT / 'docker' / variant).read_text())
            self.assertEqual(config['services']['management-backend']['depends_on']['es01'],
                             {'condition': 'service_healthy'})

    def test_render_variants_with_profile_overrides(self):
        command = shlex.split(os.environ.get('COMPOSE_TEST_COMMAND', 'docker compose'))
        if not shutil.which(command[0]):
            self.skipTest('Docker Compose CLI unavailable; set COMPOSE_TEST_COMMAND to standalone binary')
        for variant in VARIANTS:
            for overrides in ({}, {'COMPOSE_PROFILES': ''}, {'COMPOSE_PROFILES': 'unrelated'},
                              {'DOC_ENGINE': 'infinity'}, {'DOC_ENGINE': 'ELASTICSEARCH'}):
                with self.subTest(variant=variant, overrides=overrides):
                    env = os.environ.copy()
                    for key in list(env):
                        if key.startswith('COMPOSE_') or key == 'DOC_ENGINE':
                            env.pop(key)
                    env.update(MANAGEMENT_ADMIN_PASSWORD='test-only-password-123456',
                               MANAGEMENT_JWT_SECRET='test-only-secret-at-least-32-bytes-long')
                    env.update(overrides)
                    result = subprocess.run(command + ['-f', f'docker/{variant}', 'config', '--format', 'json'],
                                            cwd=ROOT, env=env, capture_output=True, text=True, check=True)
                    services = json.loads(result.stdout)['services']
                    self.assertIn('es01', services)
                    self.assertEqual(services['es01']['container_name'], 'ragflow-es-01')
                    for service in services.values():
                        for dependency in service.get('depends_on', {}):
                            self.assertIn(dependency, services)


if __name__ == '__main__':
    unittest.main()
