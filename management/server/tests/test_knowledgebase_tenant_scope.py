"""Tenant-aware parsing regressions using real service/parser code and fake I/O."""

import importlib
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


SERVER_ROOT = Path(__file__).resolve().parents[1]


def module_stub(name, **attributes):
    module = types.ModuleType(name)
    module.__dict__.update(attributes)
    return module


class KnowledgebaseTenantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        namespace = "_kb_tenant_security_services"
        package = module_stub(namespace)
        package.__path__ = [str(SERVER_ROOT / "services")]
        connector = module_stub("mysql.connector", connect=Mock(), Error=RuntimeError)
        database = module_stub("database", DB_CONFIG={}, MINIO_CONFIG={}, get_es_client=Mock(), get_minio_client=Mock())
        requests = module_stub("requests", post=Mock())
        utilities = module_stub(
            f"{namespace}.knowledgebases.utils",
            _create_task_record=Mock(), _update_document_progress=Mock(), _update_kb_chunk_count=Mock(),
            generate_uuid=Mock(return_value="chunk-id"), get_bbox_from_block=Mock(),
        )
        stubs = {
            namespace: package,
            "mysql": module_stub("mysql", connector=connector), "mysql.connector": connector,
            "database": database, "requests": requests,
            "utils": module_stub("utils", generate_uuid=Mock(return_value="kb-id")),
            f"{namespace}.knowledgebases.utils": utilities,
            f"{namespace}.knowledgebases.excel_parser": module_stub(f"{namespace}.knowledgebases.excel_parser", parse_excel_file=Mock(return_value=[{"type": "text", "text": "test content"}])),
            f"{namespace}.knowledgebases.rag_tokenizer": module_stub(f"{namespace}.knowledgebases.rag_tokenizer", RagTokenizer=Mock()),
        }
        for name in ("magic_pdf", "magic_pdf.config", "magic_pdf.data", "magic_pdf.model"):
            module = module_stub(name)
            module.__path__ = []
            stubs[name] = module
        for name, attributes in {
            "magic_pdf.config.enums": ["SupportedPdfParseMethod"],
            "magic_pdf.data.data_reader_writer": ["FileBasedDataReader", "FileBasedDataWriter"],
            "magic_pdf.data.dataset": ["PymuDocDataset"],
            "magic_pdf.data.read_api": ["read_local_images", "read_local_office"],
            "magic_pdf.model.doc_analyze_by_custom_model": ["doc_analyze"],
        }.items():
            stubs[name] = module_stub(name, **{attribute: Mock() for attribute in attributes})
        with patch.dict(sys.modules, stubs):
            cls.parser = importlib.import_module(f"{namespace}.knowledgebases.document_parser")
            cls.module = importlib.import_module(f"{namespace}.knowledgebases.service")
        cls.service = cls.module.KnowledgebaseService
        cls.database = database
        cls.requests = requests

    def setUp(self):
        self.cursor = Mock()
        self.connection = Mock()
        self.connection.cursor.return_value = self.cursor
        patcher = patch.object(self.service, "_get_db_connection", return_value=self.connection)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.database.get_es_client.reset_mock()
        self.database.get_minio_client.reset_mock()
        self.requests.post.reset_mock()

    def test_creation_preserves_separate_tenant_and_creator_columns(self):
        with patch.object(self.service, "_check_name_exists", return_value=False), patch.object(self.service, "get_knowledgebase_detail", return_value={"id": "kb-id"}):
            self.service.create_knowledgebase(
                name="owned", creator_id="tenant-A", created_by="owner-B", embd_id="own-model___provider",
            )
        query, params = self.cursor.execute.call_args.args
        self.assertIn("INSERT INTO knowledgebase", query)
        self.assertEqual(params[6], "tenant-A")
        self.assertEqual(params[10], "own-model")
        self.assertEqual(params[12], "owner-B")
        self.assertEqual(self.cursor.execute.call_count, 1)

    def test_model_credentials_come_from_kb_tenant_not_creator_or_global_user(self):
        self.cursor.fetchone.return_value = {"tenant_id": "tenant-A", "created_by": "owner-B", "embd_id": "own-model"}
        self.cursor.fetchall.return_value = [
            {"llm_name": "other-model", "api_key": "other-fixture-key", "api_base": "https://other.invalid"},
            {"llm_name": "own-model___provider", "api_key": "tenant-A-fixture-key", "api_base": "https://tenant-a.invalid/v1"},
        ]
        config = self.service.get_kb_embedding_config("owned-kb")
        self.assertEqual(config, {"llm_name": "own-model", "api_key": "tenant-A-fixture-key", "api_base": "https://tenant-a.invalid/v1"})
        queries = self.cursor.execute.call_args_list
        self.assertEqual(len(queries), 2)
        self.assertEqual(queries[0].args[1], ("owned-kb",))
        self.assertIn("tenant_id, embd_id FROM knowledgebase", queries[0].args[0])
        self.assertIn("WHERE tenant_id = %s", queries[1].args[0])
        self.assertEqual(queries[1].args[1], ("tenant-A",))
        self.assertNotIn("FROM user", " ".join(call.args[0] for call in queries))
        self.cursor.close.assert_called_once()
        self.connection.close.assert_called_once()

    def test_missing_own_model_never_falls_back_to_global_credentials(self):
        for models in ([], [{"llm_name": "different-model", "api_key": "fixture-key", "api_base": "https://example.invalid"}]):
            with self.subTest(models=models):
                self.cursor.fetchone.return_value = {"tenant_id": "tenant-A", "embd_id": "own-model"}
                self.cursor.fetchall.return_value = models
                with self.assertRaisesRegex(ValueError, "所属租户"):
                    self.service.get_kb_embedding_config("owned-kb")

    def test_missing_kb_tenant_or_model_fails_closed(self):
        for knowledgebase in (None, {"tenant_id": None}, {"tenant_id": " "}, {"tenant_id": "tenant-A", "embd_id": None}):
            with self.subTest(knowledgebase=knowledgebase):
                self.cursor.fetchone.return_value = knowledgebase
                with self.assertRaises(ValueError):
                    self.service.get_kb_embedding_config("owned-kb")
        self.cursor.fetchall.assert_not_called()

    def test_parse_passes_authoritative_tenant_separately_from_both_authors(self):
        doc_info = {"id": "doc-id", "kb_id": "owned-kb", "created_by": "owner-C"}
        kb_info = {"tenant_id": "tenant-A", "created_by": "owner-B"}
        self.cursor.fetchone.side_effect = [doc_info, {"file_id": "file-id"}, {"parent_id": "private-bucket"}, kb_info]
        config = {"llm_name": "own-model", "api_key": "tenant-A-fixture-key", "api_base": "https://tenant-a.invalid"}
        with patch.object(self.service, "get_kb_embedding_config", return_value=config) as get_config, patch.object(self.module, "perform_parse", return_value={"success": True}) as parse:
            self.assertTrue(self.service.parse_document("doc-id")["success"])
            get_config.assert_called_once_with("owned-kb")
            parse.assert_called_once_with("doc-id", doc_info, {"parent_id": "private-bucket"}, config, kb_info)
        query, params = self.cursor.execute.call_args.args
        self.assertIn("SELECT tenant_id, created_by FROM knowledgebase", query)
        self.assertEqual(params, ("owned-kb",))
        self.cursor.close.assert_called_once()
        self.connection.close.assert_called_once()

    def test_parse_stops_before_parser_when_tenant_or_model_is_unavailable(self):
        for kb_info in ({"created_by": "owner-B"}, {"tenant_id": "tenant-A", "created_by": "owner-B"}):
            with self.subTest(kb_info=kb_info):
                self.cursor.fetchone.side_effect = [{"kb_id": "owned-kb"}, {"file_id": "file-id"}, {"parent_id": "private-bucket"}, kb_info]
                with patch.object(self.service, "get_kb_embedding_config", side_effect=ValueError("no tenant model")), patch.object(self.module, "perform_parse") as parse:
                    self.assertFalse(self.service.parse_document("doc-id")["success"])
                    parse.assert_not_called()

    def test_delete_cleans_only_kb_tenant_index_not_document_creator_index(self):
        self.cursor.fetchone.return_value = {"kb_id": "owned-kb", "tenant_id": "tenant-A", "created_by": "owner-C"}
        es = Mock()
        es.indices.exists.return_value = True
        es.delete_by_query.return_value = {"deleted": 1}
        self.database.get_es_client.return_value = es
        self.assertTrue(self.service.delete_document("doc-id"))
        query, params = self.cursor.execute.call_args_list[0].args
        self.assertIn("kb.tenant_id", query)
        self.assertIn("JOIN knowledgebase kb ON d.kb_id = kb.id", query)
        self.assertNotIn("d.created_by", query)
        self.assertEqual(params, ("doc-id",))
        es.delete_by_query.assert_called_once_with(index="ragflow_tenant-A", body={"query": {"term": {"doc_id": "doc-id"}}}, refresh=True, ignore_unavailable=True)

    def test_delete_without_tenant_never_mutates_or_cleans_an_index(self):
        self.cursor.fetchone.return_value = {"kb_id": "owned-kb", "tenant_id": None, "created_by": "owner-C"}
        with self.assertRaisesRegex(Exception, "缺少租户"):
            self.service.delete_document("doc-id")
        self.assertEqual(self.cursor.execute.call_count, 1)
        self.connection.commit.assert_not_called()
        self.database.get_es_client.assert_not_called()

    def test_real_parser_indexes_in_tenant_scope_and_never_logs_embedding_secret(self):
        minio = Mock()
        minio.bucket_exists.return_value = True
        minio.get_object.return_value.read.return_value = b"fixture workbook"
        self.database.get_minio_client.return_value = minio
        es = Mock()
        es.indices.exists.return_value = False
        self.database.get_es_client.return_value = es
        self.requests.post.return_value.json.return_value = {"data": [{"embedding": [0.1, 0.2]}]}
        with tempfile.TemporaryDirectory() as directory, patch.object(self.parser.tempfile, "gettempdir", return_value=directory), patch.object(self.parser, "logger") as logger:
            result = self.parser.perform_parse(
                "doc-id", {"name": "report.xlsx", "location": "report.xlsx", "type": "excel", "kb_id": "owned-kb", "created_by": "owner-C"},
                {"parent_id": "private-bucket"},
                {"llm_name": "own-model", "api_key": "tenant-A-fixture-key", "api_base": "https://tenant-a.invalid/v1"},
                {"tenant_id": "tenant-A", "created_by": "owner-B"},
            )
        self.assertTrue(result["success"])
        self.assertEqual(es.indices.create.call_args.kwargs["index"], "ragflow_tenant-A")
        self.assertEqual(es.index.call_args.kwargs["index"], "ragflow_tenant-A")
        self.assertEqual(self.requests.post.call_args.kwargs["headers"]["Authorization"], "Bearer tenant-A-fixture-key")
        for call in logger.method_calls:
            self.assertNotIn("tenant-A-fixture-key", str(call))

    def test_real_parser_rejects_missing_tenant_without_storage_or_embedding_io(self):
        result = self.parser.perform_parse(
            "doc-id", {"name": "report.xlsx", "location": "report.xlsx", "type": "excel", "kb_id": "owned-kb"},
            {"parent_id": "private-bucket"}, {"llm_name": "own-model"}, {"created_by": "owner-B"},
        )
        self.assertFalse(result["success"])
        self.database.get_minio_client.assert_not_called()
        self.database.get_es_client.assert_not_called()
        self.requests.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
