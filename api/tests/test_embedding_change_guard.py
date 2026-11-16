"""Execute production service/route definitions with a recording DB boundary.

These are transaction/branch regressions, not a MySQL concurrency proof.
"""
import ast
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]


def load_update(path, class_name=None):
    nodes = ast.parse((ROOT / path).read_text()).body
    if class_name:
        nodes = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name).body
    node = next(n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == 'update_knowledgebase')
    node.decorator_list = []
    ns = {'datetime': datetime}
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), ns)
    return ns


class EmbeddingChangeGuardTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_update('management/server/services/knowledgebases/service.py', 'KnowledgebaseService')
        self.cls = Mock()
        self.cls.get_knowledgebase_detail.return_value = {'name': 'KB', 'embd_id': 'stale-model'}
        self.conn = self.cls._get_db_connection.return_value
        self.cursor = self.conn.cursor.return_value

    def update(self, **kwargs):
        return self.ns['update_knowledgebase'](self.cls, 'kb-id', **kwargs)

    def assert_not_written(self):
        self.assertFalse(any('UPDATE knowledgebase' in c.args[0] for c in self.cursor.execute.call_args_list))
        self.conn.commit.assert_not_called()
        self.conn.rollback.assert_called_once()
        self.cursor.close.assert_called_once()
        self.conn.close.assert_called_once()

    def test_existing_aggregate_chunks_rejects_entire_update(self):
        self.cursor.fetchone.return_value = ('old-model', 12)
        with self.assertRaises(ValueError):
            self.update(embd_id='new-model', description='must-not-write')
        self.assert_not_written()

    def test_document_chunks_or_running_parse_rejects_change(self):
        for reason in ('parsed-document', 'running-document'):
            self.setUp()
            self.cursor.fetchone.side_effect = [('old-model', 0), (reason,)]
            with self.assertRaises(ValueError):
                self.update(embd_id='new-model')
            self.assert_not_written()
            query, params = self.cursor.execute.call_args.args
            self.assertIn("COALESCE(chunk_num, 0) <> 0 OR run = '1'", query)
            self.assertIn('FOR UPDATE', query)
            self.assertEqual(params, ('kb-id',))

    def test_empty_kb_can_change_model_with_locked_current_read(self):
        self.cursor.fetchone.side_effect = [('old-model', 0), None]
        self.update(embd_id='new-model')
        self.conn.start_transaction.assert_called_once()
        self.assertIn('FOR UPDATE', self.cursor.execute.call_args_list[0].args[0])
        self.assertEqual(self.cursor.execute.call_args_list[0].args[1], ('kb-id',))
        self.assertIn('new-model', self.cursor.execute.call_args.args[1])
        self.conn.commit.assert_called_once()
        self.conn.rollback.assert_not_called()
        self.cursor.close.assert_called_once()
        self.conn.close.assert_called_once()

    def test_same_model_and_metadata_update_remain_allowed(self):
        self.cursor.fetchone.return_value = ('same-model', 20)
        self.update(embd_id='same-model', description='new description')
        self.assertEqual(self.cursor.fetchone.call_count, 1)
        self.conn.commit.assert_called_once()

    def test_metadata_only_update_does_not_query_model(self):
        self.update(description='new description')
        self.cursor.fetchone.assert_not_called()
        self.conn.commit.assert_called_once()

    def test_database_failure_rolls_back_and_closes(self):
        self.cursor.execute.side_effect = RuntimeError('database unavailable')
        with self.assertRaisesRegex(Exception, 'database unavailable'):
            self.update(embd_id='new-model')
        self.conn.rollback.assert_called_once()
        self.cursor.close.assert_called_once()
        self.conn.close.assert_called_once()

    def test_route_returns_conflict_for_model_guard(self):
        ns = load_update('management/server/routes/knowledgebases/routes.py')
        ns.update(request=SimpleNamespace(json={'embd_id': 'new-model'}),
                  KnowledgebaseService=Mock(), error_response=lambda message, code=500: (message, code))
        ns['KnowledgebaseService'].update_knowledgebase.side_effect = ValueError('cannot change model')
        self.assertEqual(ns['update_knowledgebase']('kb-id'), ('cannot change model', 409))


if __name__ == '__main__':
    unittest.main()
