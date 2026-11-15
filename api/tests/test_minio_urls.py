import ast
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('minio_urls', ROOT / 'api/utils/minio_urls.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MinioPublicUrlTests(unittest.TestCase):
    def test_legacy_hosts_and_explicit_urls(self):
        cases = [
            ({}, 'http://localhost:9000/'),
            ({'MINIO_VISIT_HOST': '192.0.2.1', 'MINIO_PORT': '19000'}, 'http://192.0.2.1:19000/'),
            ({'MINIO_VISIT_HOST': 'storage.example'}, 'http://storage.example:9000/'),
            ({'MINIO_VISIT_HOST': 'storage.example:9443'}, 'http://storage.example:9443/'),
            ({'MINIO_VISIT_HOST': 'https://storage.example', 'MINIO_PORT': '9000'}, 'https://storage.example/'),
            ({'MINIO_VISIT_HOST': 'http://storage.example'}, 'http://storage.example/'),
            ({'MINIO_VISIT_HOST': 'https://storage.example:9443/media/'}, 'https://storage.example:9443/media/'),
            ({'MINIO_VISIT_HOST': '[::1]'}, 'http://[::1]:9000/'),
            ({'MINIO_VISIT_HOST': 'https://[::1]:9443/'}, 'https://[::1]:9443/'),
        ]
        for env, expected in cases:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                self.assertEqual(MODULE.minio_public_url(), expected)
                self.assertEqual(MODULE.minio_public_url('/bucket/images/a b.png'), expected + 'bucket/images/a%20b.png')

    def test_invalid_public_urls_rejected(self):
        for host in ['ftp://storage.example', 'https://u:p@storage.example', 'https://storage.example/?token=x',
                     'https://storage.example/#frag', 'http://', 'https://storage.example:bad']:
            with self.subTest(host=host), patch.dict(os.environ, {'MINIO_VISIT_HOST': host}, clear=True):
                with self.assertRaises(ValueError):
                    MODULE.minio_public_url()

    def test_separate_images_ship_identical_helper(self):
        self.assertEqual((ROOT / 'api/utils/minio_urls.py').read_bytes(),
                         (ROOT / 'management/server/minio_urls.py').read_bytes())

    def test_endpoint_calls_same_builder(self):
        tree = ast.parse((ROOT / 'api/apps/minio_app.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
        node.decorator_list = []
        ns = dict(jsonify=lambda value: value, minio_public_url=MODULE.minio_public_url)
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'endpoint', 'exec'), ns)
        with patch.dict(os.environ, {'MINIO_VISIT_HOST': 'https://images.example/media'}, clear=True):
            self.assertEqual(ns['minio'](), {'url': 'https://images.example/media/'})

    def test_parser_to_search_to_reply_does_not_duplicate_proxy_prefix(self):
        tree = ast.parse((ROOT / 'management/server/services/knowledgebases/document_parser.py').read_text())
        def assignment(name):
            return next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
        ns = dict(img_url='https://images.example/media/bucket/images/a.png',
                  output_bucket='bucket', img_key='images/a.png', chunk_count=0)
        exec(compile(ast.Module(body=[assignment('image_info')], type_ignores=[]), 'parser', 'exec'), ns)
        ns['nearest_image'] = ns['image_info']
        exec(compile(ast.Module(body=[assignment('relative_path'), assignment('direct_update')], type_ignores=[]), 'parser', 'exec'), ns)
        image_id = ns['direct_update']['doc']['img_id']
        self.assertEqual(image_id, 'bucket/images/a.png')
        with patch.dict(os.environ, {'MINIO_VISIT_HOST': 'https://images.example/media'}, clear=True):
            self.assertEqual(MODULE.minio_public_url(image_id), ns['img_url'])

    def test_actual_image_url_assignments_use_public_not_internal_endpoint(self):
        # Execute the actual URL assignments from both response paths, upload,
        # and parsing, without loading models/external services.
        counts = {'api/db/services/dialog_service.py': 1, 'api/db/services/write_service.py': 2,
                  'management/server/services/knowledgebases/document_parser.py': 1}
        for path, count in counts.items():
            tree = ast.parse((ROOT / path).read_text())
            assignments = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                           and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
                           and n.value.func.id == 'minio_public_url']
            self.assertEqual(len(assignments), count)
            for node in assignments:
                ns = dict(minio_public_url=MODULE.minio_public_url, img_path='bucket/images/a.png',
                          bucket_name='bucket', output_bucket='bucket', object_name='images/a.png', img_key='images/a.png')
                with patch.dict(os.environ, {'MINIO_VISIT_HOST': 'https://images.example/media'}, clear=True):
                    exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), ns)
                self.assertEqual(ns[node.targets[0].id], 'https://images.example/media/bucket/images/a.png')


if __name__ == '__main__':
    unittest.main()
