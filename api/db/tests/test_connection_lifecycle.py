"""Exercise the production cleanup hooks without importing external RAG services.

Run with: python -m unittest discover -s api/db/tests -v
Requires the application's Flask==3.0.3 and peewee==3.17.1.
"""
import ast
import logging
from pathlib import Path
import tempfile
import threading
import unittest

from flask import Flask, Response
from playhouse.pool import PooledSqliteDatabase


ROOT = Path(__file__).resolve().parents[3]


def load_functions(path, names, namespace):
    """Load actual function definitions, including their Flask decorators."""
    tree = ast.parse((ROOT / path).read_text())
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in functions} == set(names)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)


class ConnectionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = PooledSqliteDatabase(
            str(Path(self.directory.name) / "pool.sqlite"),
            max_connections=2, check_same_thread=False,
        )
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True)
        namespace = {"DB": self.db, "logging": logging, "app": self.app}
        load_functions("api/db/db_models.py", ["close_connection"], namespace)
        self.close = namespace["close_connection"]
        load_functions("api/apps/__init__.py", ["_db_close", "_db_close_response"], namespace)

        @self.app.route("/query")
        def query():
            self.db.execute_sql("SELECT 1").fetchone()
            return "ok"

        @self.app.route("/error")
        def error():
            self.db.execute_sql("SELECT 1").fetchone()
            raise RuntimeError("view failed")

        @self.app.route("/stream/<mode>")
        def stream(mode):
            def chunks():
                try:
                    self.db.execute_sql("SELECT 1").fetchone()
                    yield "first"
                    if mode == "error":
                        raise RuntimeError("stream failed")
                    yield "second"
                finally:
                    # Generator finalization itself can access the database.
                    self.db.execute_sql("SELECT 2").fetchone()
                    if mode == "close-error":
                        raise RuntimeError("finalizer failed")
            return Response(chunks())

    def tearDown(self):
        self.db.close_all()
        self.directory.cleanup()

    def assert_released(self):
        self.assertTrue(self.db.is_closed())
        self.assertEqual(len(self.db._in_use), 0)

    def test_completed_requests_reuse_pool(self):
        client = self.app.test_client()
        for _ in range(6):
            response = client.get("/query")
            self.assertEqual(response.data, b"ok")
            self.assert_released()
            response.close()
        self.assertEqual(len(self.db._connections), 1)

    def test_exception_releases_connection(self):
        with self.assertRaisesRegex(RuntimeError, "view failed"):
            self.app.test_client().get("/error")
        self.assert_released()

    def test_no_connection_and_repeated_cleanup_are_safe(self):
        self.close()
        self.db.execute_sql("SELECT 1")
        self.close()
        self.close()
        self.assert_released()

    def test_service_context_can_release_before_teardown(self):
        with self.app.test_request_context():
            with self.db.connection_context():
                self.db.execute_sql("SELECT 1")
        self.assert_released()

    def test_stream_completion_releases_late_connection(self):
        response = self.app.test_client().get("/stream/ok", buffered=False)
        self.assertEqual(b"".join(response.response), b"firstsecond")
        response.close()
        self.assert_released()

    def test_stream_disconnect_releases_after_generator_finalizer(self):
        response = self.app.test_client().get("/stream/ok", buffered=False)
        self.assertFalse(self.db.is_closed())
        response.close()
        self.assert_released()

    def test_stream_raising_finalizer_still_releases_connection(self):
        response = self.app.test_client().get("/stream/close-error", buffered=False)
        with self.assertRaisesRegex(RuntimeError, "finalizer failed"):
            response.close()
        self.assert_released()

    def test_stream_exception_releases_connection_on_wsgi_close(self):
        response = self.app.test_client().get("/stream/error", buffered=False)
        try:
            with self.assertRaisesRegex(RuntimeError, "stream failed"):
                list(response.response)
        finally:
            response.close()
        self.assert_released()

    def test_teardown_does_not_close_other_threads_old_connection(self):
        ready, resume = threading.Event(), threading.Event()
        failures = []

        def background_request():
            try:
                self.db.execute_sql("SELECT 1").fetchone()
                ready.set()
                if not resume.wait(5):
                    raise TimeoutError("cleanup did not resume worker")
                self.assertEqual(self.db.execute_sql("SELECT 2").fetchone(), (2,))
            except BaseException as exc:
                failures.append(exc)
            finally:
                self.close()

        worker = threading.Thread(target=background_request)
        worker.start()
        try:
            self.assertTrue(ready.wait(5))
            # Simulate a long-running request without slow sleeps.
            with self.db._pool_lock:
                for key, conn in list(self.db._in_use.items()):
                    self.db._in_use[key] = conn._replace(checked_out=0)
            response = self.app.test_client().get("/query")
            response.close()
            self.assertEqual(len(self.db._in_use), 1)
        finally:
            resume.set()
            worker.join(6)
        self.assertFalse(worker.is_alive())
        self.assertEqual(failures, [])
        self.assert_released()


if __name__ == "__main__":
    unittest.main()
