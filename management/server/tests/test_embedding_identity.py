"""No model/provider requests: synthetic tenant records and actual lookup code."""
import ast
import json
import os
from pathlib import Path
import sys
import unittest

SERVER = Path(__file__).resolve().parents[1]
ROOT = SERVER.parents[1]
sys.path.insert(0, str(SERVER))
from services.embedding_identity import model_identity, select_embedding


class EmbeddingIdentityTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {'llm_name': 'bge-m3___VLLM', 'llm_factory': 'VLLM'},
            {'llm_name': 'bge-m3___Ollama', 'llm_factory': 'Ollama'},
        ]

    def test_provider_qualified_name_resolves_exactly(self):
        self.assertIs(select_embedding(self.rows, 'bge-m3___VLLM@VLLM'), self.rows[0])
        self.assertEqual(model_identity(self.rows[0]), 'bge-m3___VLLM@VLLM')

    def test_unique_stored_and_legacy_names(self):
        self.assertIs(select_embedding(self.rows, 'bge-m3___VLLM'), self.rows[0])
        self.assertIs(select_embedding(self.rows[:1], 'bge-m3'), self.rows[0])

    def test_ambiguous_legacy_or_same_named_providers_fail_closed(self):
        with self.assertRaises(ValueError):
            select_embedding(self.rows, 'bge-m3')
        with self.assertRaises(ValueError):
            select_embedding([dict(r, llm_name='shared') for r in self.rows], 'shared')

    def test_exact_name_wins_over_alias_and_wrong_provider_is_rejected(self):
        exact = {'llm_name': 'bge-m3', 'llm_factory': 'OpenAI'}
        self.assertIs(select_embedding(self.rows + [exact], 'bge-m3'), exact)
        with self.assertRaises(ValueError):
            select_embedding(self.rows, 'bge-m3___VLLM@Ollama')
        with self.assertRaises(ValueError):
            select_embedding([], 'bge-m3')

    def test_custom_legacy_identity_not_silently_reassigned(self):
        self.assertEqual(model_identity({'llm_name': 'legacy', 'llm_factory': 'Custom'}), 'legacy')

    def test_actual_core_lookup_accepts_canonical_identity_and_scopes_tenant(self):
        # Extract just these production methods to avoid importing model SDKs
        # or database connectors. Query is the only substituted boundary.
        tree = ast.parse((ROOT / 'api/db/services/llm_service.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'TenantLLMService')
        cls.bases = []
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('get_api_key', 'split_model_name_and_factory')]
        for method in cls.body:
            method.decorator_list = [d for d in method.decorator_list if isinstance(d, ast.Name)]
        ns = {'json': json, 'os': os, 'get_project_base_directory': lambda: str(ROOT)}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), 'core-lookup', 'exec'), ns)
        core = ns['TenantLLMService']
        rows = [dict(r, tenant_id='tenant-A') for r in self.rows]
        core.query = staticmethod(lambda **kw: [r for r in rows if all(r.get(k) == v for k, v in kw.items())])
        identity = model_identity(select_embedding(self.rows, 'bge-m3___VLLM@VLLM'))
        self.assertEqual(core.get_api_key('tenant-A', identity), rows[0])
        self.assertIsNone(core.get_api_key('tenant-B', identity))
        self.assertIsNone(core.get_api_key('tenant-A', 'bge-m3'))
