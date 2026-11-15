"""Isolated production-function regressions; no external services or real secrets."""
import ast
import contextlib
import copy
import io
import json
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
SENTINEL = 'synthetic-credential-must-not-be-logged'


def load(path, names, namespace, class_name=None):
    tree = ast.parse((ROOT / path).read_text())
    nodes = tree.body
    if class_name:
        nodes = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name).body
    chosen = [n for n in nodes if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in chosen} == set(names)
    for node in chosen:
        node.decorator_list = []
    exec(compile(ast.Module(body=chosen, type_ignores=[]), path, 'exec'), namespace)
    return namespace


class CredentialLoggingTests(unittest.TestCase):
    def setUp(self):
        self.out = io.StringIO()
        self.stdout = contextlib.redirect_stdout(self.out)
        self.stdout.__enter__()
        previous_level = logging.getLogger().level
        logging.getLogger().setLevel(logging.DEBUG)
        self.addCleanup(logging.getLogger().setLevel, previous_level)
        self.handler = logging.StreamHandler(self.out)
        logging.getLogger().addHandler(self.handler)
        self.addCleanup(self.stdout.__exit__, None, None, None)
        self.addCleanup(logging.getLogger().removeHandler, self.handler)

    def tearDown(self):
        self.assertNotIn(SENTINEL, self.out.getvalue())

    def auth_namespace(self, header=SENTINEL):
        serializer = Mock()
        serializer.loads.return_value = SENTINEL
        user = SimpleNamespace(id='user-id', email=SENTINEL)
        service = Mock()
        service.query.return_value = [user]
        return dict(
            Serializer=Mock(return_value=serializer),
            settings=SimpleNamespace(SECRET_KEY=SENTINEL, RetCode=SimpleNamespace(AUTHENTICATION_ERROR=401)),
            UserService=service, StatusEnum=SimpleNamespace(VALID=SimpleNamespace(value='1')),
            logging=logging, request=SimpleNamespace(headers={'Authorization': header}, json={'doc_ids': ['doc']}),
            get_json_result=lambda **kwargs: kwargs, get_data_error_result=lambda **kwargs: kwargs,
            server_error_response=lambda e: {'error': str(e)}, json=json,
        )

    def test_request_loader_preserves_success_lookup(self):
        ns = self.auth_namespace()
        load('api/apps/__init__.py', ['load_user'], ns)
        self.assertIs(ns['load_user'](ns['request']), ns['UserService'].query.return_value[0])
        ns['Serializer'].return_value.loads.assert_called_once_with(SENTINEL)
        ns['UserService'].query.assert_called_once_with(access_token=SENTINEL, status='1')

    def test_request_loader_rejects_missing_invalid_and_unknown(self):
        for mode in ('missing', 'invalid', 'unknown'):
            ns = self.auth_namespace(None if mode == 'missing' else SENTINEL)
            if mode == 'invalid':
                ns['Serializer'].return_value.loads.side_effect = ValueError(SENTINEL)
            if mode == 'unknown':
                ns['UserService'].query.return_value = []
            load('api/apps/__init__.py', ['load_user'], ns)
            self.assertIsNone(ns['load_user'](ns['request']))

    def test_temp_file_auth_and_ownership_unchanged(self):
        for owner in ('user-id', 'different-user'):
            ns = self.auth_namespace()
            ns['REDIS_CONN'] = Mock()
            ns['REDIS_CONN'].get.return_value = json.dumps({'id': 'file', 'user_id': owner})
            load('api/apps/conversation_app.py', ['get_temp_file'], ns)
            result = ns['get_temp_file']('file')
            ns['UserService'].query.assert_called_once_with(access_token=SENTINEL, status='1')
            if owner == 'user-id':
                self.assertEqual(result['data']['id'], 'file')
            else:
                self.assertEqual(result['message'], '无权访问此文件')

    def test_temp_file_rejects_missing_invalid_unknown(self):
        for mode in ('missing', 'invalid', 'unknown'):
            ns = self.auth_namespace(None if mode == 'missing' else SENTINEL)
            if mode == 'invalid':
                ns['Serializer'].return_value.loads.side_effect = ValueError(SENTINEL)
            if mode == 'unknown':
                ns['UserService'].query.return_value = []
            load('api/apps/conversation_app.py', ['get_temp_file'], ns)
            self.assertEqual(ns['get_temp_file']('file')['code'], 401)

    def test_docinfos_preserves_bearer_and_raw_token(self):
        for header in (SENTINEL, 'Bearer ' + SENTINEL):
            ns = self.auth_namespace(header)
            ns['APIToken'] = Mock()
            ns['APIToken'].query.return_value = [SimpleNamespace(token=SENTINEL)]
            ns['DocumentService'] = Mock()
            ns['DocumentService'].get_by_ids.return_value.dicts.return_value = [{'id': 'doc'}]
            load('api/apps/api_app.py', ['docinfos'], ns)
            self.assertEqual(ns['docinfos']()['data'], [{'id': 'doc'}])
            ns['APIToken'].query.assert_called_once_with(token=SENTINEL)

    def test_docinfos_rejects_missing_malformed_unknown(self):
        for header in (None, 'Bearer ', SENTINEL):
            ns = self.auth_namespace(header)
            ns['APIToken'] = Mock()
            ns['APIToken'].query.return_value = []
            load('api/apps/api_app.py', ['docinfos'], ns)
            self.assertEqual(ns['docinfos']()['code'], 401)

    def test_embedding_test_receives_credential_without_logging_it(self):
        ns = {}
        load('management/server/services/knowledgebases/service.py', ['set_system_embedding_config'], ns,
             class_name='KnowledgebaseService')
        cls = Mock()
        cls._get_earliest_user_tenant_id.return_value = 'tenant'
        cls._test_embedding_connection.return_value = (False, 'offline')
        result = ns['set_system_embedding_config'](cls, 'model', 'https://example.invalid', SENTINEL)
        self.assertEqual(result, (False, '连接测试失败: offline'))
        cls._test_embedding_connection.assert_called_once_with(
            base_url='https://example.invalid', model_name='model', api_key=SENTINEL)

    def test_embedding_save_success_and_failure_do_not_log_credentials(self):
        from datetime import datetime
        for fail in (False, True):
            ns = dict(datetime=datetime)
            load('management/server/services/knowledgebases/service.py', ['set_system_embedding_config'], ns,
                 class_name='KnowledgebaseService')
            cls = Mock()
            cls._get_earliest_user_tenant_id.return_value = 'tenant'
            cls._test_embedding_connection.return_value = (True, 'ok')
            cursor = cls._get_db_connection.return_value.cursor.return_value
            cursor.fetchone.return_value = {'tenant_id': 'tenant'}
            if fail:
                cursor.execute.side_effect = ValueError(SENTINEL)
            result = ns['set_system_embedding_config'](cls, 'model', 'https://example.invalid', SENTINEL)
            self.assertEqual(result[0], not fail)
            cursor.close.assert_called_once()
            if not fail:
                self.assertIn(SENTINEL, cursor.execute.call_args.args[1])
                cls._get_db_connection.return_value.commit.assert_called_once()

    def test_embedding_connection_exception_does_not_log_url_or_secret(self):
        ns = dict(requests=Mock())
        ns['requests'].post.side_effect = ValueError(SENTINEL)
        load('management/server/services/knowledgebases/service.py', ['_test_embedding_connection'], ns,
             class_name='KnowledgebaseService')
        result = ns['_test_embedding_connection'](Mock(), 'https://' + SENTINEL + '@example.invalid', 'model', SENTINEL)
        self.assertFalse(result[0])
        self.assertEqual(ns['requests'].post.call_args.kwargs['headers']['Authorization'], 'Bearer ' + SENTINEL)

    def test_config_redacts_nested_credentials_without_mutating(self):
        config = {'api_key': SENTINEL, 'ragflow': {'secret_key': SENTINEL, 'port': 9380},
                  'oauth': {'providers': [{'client_secret': SENTINEL, 'access-token': SENTINEL}]},
                  'llm': {'api_key': SENTINEL, 'max_tokens': 512},
                  'services': ({'PASSWORD': SENTINEL, 'authorization': SENTINEL},),
                  'storage': {'container_url': 'https://example.invalid/?sig=' + SENTINEL},
                  'provider': {'api_base': 'https://' + SENTINEL + '@example.invalid'}}
        before = copy.deepcopy(config)
        logger = Mock()
        ns = dict(CONFIGS=config, logging=logger, SERVICE_CONF='test', conf_realpath=lambda _: 'test')
        load('api/utils/__init__.py', ['_redact_config', 'show_configs'], ns)
        ns['show_configs']()
        message = logger.info.call_args.args[0]
        self.assertNotIn(SENTINEL, message)
        self.assertIn('9380', message)
        self.assertIn('512', message)
        self.assertEqual(config, before)


if __name__ == '__main__':
    unittest.main()
