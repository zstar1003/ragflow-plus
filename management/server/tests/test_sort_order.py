"""SQL sorting regressions, runnable without MySQL or the parser dependencies.

Run from the repository root:
    python -m unittest discover -s management/server/tests -p 'test_sort_order.py' -v

The real service modules and sort helper are imported and executed. Only
unrelated infrastructure/parser imports and database connections are mocked.
"""

import importlib
import re
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch


def stub_module(name, **attributes):
    module = ModuleType(name)
    module.__dict__.update(attributes)
    return module


class SortOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import under a private namespace and restore sys.modules afterwards,
        # so these lightweight stubs cannot affect other server tests.
        namespace = "_sort_security_services"
        package = stub_module(namespace)
        package.__path__ = [str(Path(__file__).resolve().parents[1] / "services")]
        connector = stub_module("mysql.connector", connect=Mock(), Error=RuntimeError)
        stubs = {
            namespace: package,
            "mysql": stub_module("mysql", connector=connector),
            "mysql.connector": connector,
            "pytz": stub_module("pytz"),
            "jwt_config": stub_module("jwt_config", get_admin_password=Mock()),
            "requests": stub_module("requests"),
            "dotenv": stub_module("dotenv", load_dotenv=Mock()),
            "database": stub_module(
                "database",
                DB_CONFIG={},
                get_db_connection=Mock(),
                get_minio_client=Mock(),
                get_redis_connection=Mock(),
                get_es_client=Mock(),
            ),
            "utils": stub_module(
                "utils", generate_uuid=Mock(), encrypt_password=Mock(), verify_password=Mock()
            ),
            f"{namespace}.files.utils": stub_module(
                f"{namespace}.files.utils", FileSource=Mock(), FileType=Mock(), get_uuid=Mock()
            ),
            f"{namespace}.knowledgebases.document_parser": stub_module(
                f"{namespace}.knowledgebases.document_parser",
                _update_document_progress=Mock(),
                perform_parse=Mock(),
            ),
        }
        with patch.dict(sys.modules, stubs):
            modules = {
                name: importlib.import_module(f"{namespace}.{name}.service")
                for name in ("users", "teams", "files", "knowledgebases", "conversation")
            }
            cls.normalize = staticmethod(
                importlib.import_module(f"{namespace}.sql_utils").normalize_sort_order
            )

        knowledgebases = modules["knowledgebases"].KnowledgebaseService
        cls.conversation = modules["conversation"]
        cls.services = (
            ("users", modules["users"].get_users_with_pagination, (1, 10), modules["users"].mysql.connector, "connect", ""),
            ("teams", modules["teams"].get_teams_with_pagination, (1, 10), modules["teams"].mysql.connector, "connect", ""),
            ("files", modules["files"].get_files_list, (1, 10), modules["files"], "get_db_connection", "f."),
            ("knowledgebases", knowledgebases.get_knowledgebase_list, (), knowledgebases, "_get_db_connection", "k."),
            ("documents", knowledgebases.get_knowledgebase_documents, ("kb-id",), knowledgebases, "_get_db_connection", "d."),
        )

    def assert_query_direction(self, service, sort_order, expected, sort_by="create_time"):
        name, function, args, connection_owner, connection_name, prefix = service
        cursor = Mock()
        # Covers both the document-list existence check and count queries.
        cursor.fetchone.return_value = {"id": "kb-id", "total": 0}
        cursor.fetchall.return_value = []
        connection = Mock()
        connection.cursor.return_value = cursor
        with patch.object(connection_owner, connection_name, return_value=connection):
            function(*args, sort_by=sort_by, sort_order=sort_order)

        queries = [call.args[0] for call in cursor.execute.call_args_list]
        ordered_queries = [query for query in queries if "ORDER BY" in query]
        self.assertEqual(len(ordered_queries), 1, name)
        query = " ".join(ordered_queries[0].split())
        column = "name" if sort_by == "name" else "create_time"
        self.assertRegex(
            query,
            rf"ORDER BY {re.escape(prefix + column)} {expected} LIMIT %s OFFSET %s$",
        )
        # Pagination remains parameterized, and no second statement is possible.
        self.assertNotIn(";", query)
        list_call = next(call for call in cursor.execute.call_args_list if "ORDER BY" in call.args[0])
        expected_params = ["kb-id", 10, 0] if name == "documents" else [10, 0]
        self.assertEqual(list_call.args[1], expected_params)
        cursor.close.assert_called_once_with()
        connection.close.assert_called_once_with()

    def test_valid_directions_in_all_five_queries(self):
        for service in self.services:
            for value, expected in (
                ("asc", "ASC"), ("ASC", "ASC"), ("aSc", "ASC"),
                ("desc", "DESC"), ("DESC", "DESC"), ("dEsC", "DESC"),
                (" \tasc\n", "ASC"), (" desc ", "DESC"),
            ):
                with self.subTest(service=service[0], sort_order=value):
                    self.assert_query_direction(service, value, expected)

    def test_injection_and_invalid_directions_in_all_five_queries(self):
        invalid_values = (
            "ASC; DROP TABLE user; --",
            "DESC, (SELECT SLEEP(5))",
            "ASC LIMIT 1 --",
            "ASC/**/, (SELECT SLEEP(5))",
            "ASC\nUNION SELECT 1",
            "DESC --",
            "asc\x00",
            "ascending",
            "",
            " \t\n",
            None,
            1,
            ["asc"],
            {"direction": "asc"},
        )
        for service in self.services:
            for value in invalid_values:
                with self.subTest(service=service[0], sort_order=value):
                    self.assert_query_direction(service, value, "DESC")

    def test_column_allowlists_are_preserved_in_all_five_queries(self):
        for service in self.services:
            with self.subTest(service=service[0], sort_by="name"):
                self.assert_query_direction(service, "asc", "ASC", sort_by="name")
            for value in ("create_time; DROP TABLE user; --", "name DESC, (SELECT SLEEP(5))"):
                with self.subTest(service=service[0], sort_by=value):
                    self.assert_query_direction(service, "asc", "ASC", sort_by=value)

    def test_helper_returns_only_canonical_literals(self):
        for value in (None, False, 0, [], {}, "", "invalid", "DESC; SELECT 1"):
            with self.subTest(sort_order=value):
                self.assertEqual(self.normalize(value), "DESC")
        self.assertEqual(self.normalize("aSc"), "ASC")
        self.assertEqual(self.normalize("dEsC"), "DESC")

    def assert_conversation_sort(self, sort_by, sort_order, expected_column, expected_direction):
        cursor = Mock()
        cursor.fetchone.return_value = {"total": 0}
        cursor.fetchall.return_value = []
        connection = Mock()
        connection.cursor.return_value = cursor
        with patch.object(self.conversation.mysql.connector, "connect", return_value=connection), patch("builtins.print"):
            self.conversation.get_conversations_by_user_id(
                "user-id", page=2, size=20, sort_by=sort_by, sort_order=sort_order
            )

        self.assertEqual(cursor.execute.call_count, 2)
        count_call, list_call = cursor.execute.call_args_list
        query = " ".join(list_call.args[0].split())
        self.assertRegex(
            query,
            rf"ORDER BY d\.{expected_column} {expected_direction} LIMIT %s OFFSET %s$",
        )
        self.assertNotIn(";", query)
        self.assertEqual(count_call.args[1], ("user-id",))
        self.assertEqual(list_call.args[1], ("user-id", 20, 20))
        cursor.close.assert_called_once_with()
        connection.close.assert_called_once_with()

    def test_conversation_valid_sort_fields_and_directions(self):
        for column in ("id", "name", "tenant_id", "create_time", "create_date", "update_time", "update_date"):
            for direction, expected in (("asc", "ASC"), ("ASC", "ASC"), ("desc", "DESC"), ("dEsC", "DESC")):
                with self.subTest(sort_by=column, sort_order=direction):
                    self.assert_conversation_sort(column, direction, column, expected)

    def test_conversation_injected_or_invalid_sort_fields_use_default(self):
        for column in (
            "update_time DESC, (SELECT SLEEP(5))",
            "update_time; DROP TABLE dialog; --",
            "name DESC --",
            "update_time\nASC LIMIT 1 --",
            "`update_time`",
            "unknown",
            "",
            None,
            1,
            ["update_time"],
            {"field": "update_time"},
        ):
            for direction, expected in (("asc", "ASC"), ("desc", "DESC")):
                with self.subTest(sort_by=column, sort_order=direction):
                    self.assert_conversation_sort(column, direction, "update_time", expected)

    def test_conversation_existing_invalid_direction_behavior_is_preserved(self):
        # This service already returns a safe literal and historically defaults
        # non-'desc' directions to ASC, unlike the other five list queries.
        for direction in ("", "invalid", "DESC; SELECT 1", " desc ", "ASC; SELECT 1"):
            with self.subTest(sort_order=direction):
                self.assert_conversation_sort("update_time", direction, "update_time", "ASC")


if __name__ == "__main__":
    unittest.main()
