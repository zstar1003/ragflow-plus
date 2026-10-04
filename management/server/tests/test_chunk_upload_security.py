"""Chunk-upload ownership and path regressions without Redis, MinIO, or MySQL.

The production service and route functions run against temporary files and an
in-memory Redis test double. External persistence is mocked at its boundary.
"""

import importlib
import io
import json
import sys
import tempfile
import unittest
from enum import Enum
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch
from uuid import uuid4

from flask import Blueprint, Flask
from werkzeug.datastructures import FileStorage


def stub_module(name, **attributes):
    module = ModuleType(name)
    module.__dict__.update(attributes)
    return module


class FileType(Enum):
    FOLDER = "folder"
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    PPT = "ppt"
    VISUAL = "visual"
    TEXT = "txt"
    HTML = "html"
    OTHER = "other"


class FakeRedis:
    """Keep real Redis's bytes semantics, hash NX, and separate bitmaps."""

    def __init__(self):
        self.hashes = {}
        self.bits = {}

    def hsetnx(self, key, field, value):
        fields = self.hashes.setdefault(key, {})
        if field in fields:
            return 0
        self.hset(key, field, value)
        return 1

    def hset(self, key, field, value):
        self.hashes.setdefault(key, {})[field] = str(value).encode()

    def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    def setbit(self, key, offset, value):
        self.bits.setdefault(key, {})[offset] = value

    def getbit(self, key, offset):
        return self.bits.get(key, {}).get(offset, 0)

    def expire(self, key, ttl):
        return True

    def delete(self, key):
        self.hashes.pop(key, None)
        self.bits.pop(key, None)


class ChunkUploadSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server = Path(__file__).resolve().parents[1]
        namespace = "_chunk_security_services"
        package = stub_module(namespace)
        package.__path__ = [str(server / "services")]
        file_source = stub_module("FileSource", LOCAL=stub_module("local", value=""))
        stubs = {
            namespace: package,
            "dotenv": stub_module("dotenv", load_dotenv=Mock()),
            "database": stub_module(
                "database", get_db_connection=Mock(), get_minio_client=Mock(), get_redis_connection=Mock()
            ),
            f"{namespace}.files.utils": stub_module(
                f"{namespace}.files.utils", FileSource=file_source, FileType=FileType,
                get_uuid=lambda: uuid4().hex,
            ),
        }
        with patch.dict(sys.modules, stubs):
            cls.service = importlib.import_module(f"{namespace}.files.service")

        # Import the real file routes without registering unrelated blueprints.
        route_namespace = "_chunk_security_routes"
        blueprint = Blueprint("chunk_security_files", __name__)
        route_package = stub_module(route_namespace, files_bp=blueprint)
        route_package.__path__ = [str(server / "routes")]
        file_routes_package = stub_module(f"{route_namespace}.files")
        file_routes_package.__path__ = [str(server / "routes" / "files")]
        cls.auth = Mock(return_value={"user_id": "owner-a", "role": "user"})
        route_stubs = {
            route_namespace: route_package,
            f"{route_namespace}.files": file_routes_package,
            "services": stub_module("services"),
            "services.files": stub_module("services.files"),
            "services.files.service": cls.service,
            "services.files.utils": stub_module("services.files.utils", FileType=FileType),
            "services.auth": stub_module(
                "services.auth", get_current_user_from_token=cls.auth, is_admin=Mock(return_value=False)
            ),
        }
        with patch.dict(sys.modules, route_stubs):
            cls.routes = importlib.import_module(f"{route_namespace}.files.routes")
        cls.app = Flask(__name__)
        cls.app.config["TESTING"] = True
        cls.app.register_blueprint(blueprint, url_prefix="/files")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.redis = FakeRedis()
        self.addCleanup(patch.stopall)
        patch.object(self.service, "UPLOAD_TEMP_DIR", self.temp.name).start()
        patch.object(self.service, "UPLOAD_FOLDER", str(self.root / "uploads")).start()
        self.redis_connection = patch.object(self.service, "get_redis_connection", return_value=self.redis).start()
        self.storage_calls = []

        def save(files, parent_id=None, user_id=None):
            self.storage_calls.append({
                "bytes": files[0].read(), "filename": files[0].filename,
                "parent_id": parent_id, "user_id": user_id,
            })
            return {"code": 0, "data": [{"status": "success"}], "message": "ok"}

        self.upload_patch = patch.object(self.service, "upload_files_to_server", side_effect=save)
        self.upload_mock = self.upload_patch.start()
        self.auth.return_value = {"user_id": "owner-a", "role": "user"}
        self.client = self.app.test_client()

    def chunk(self, content=b"first", index="0", count="1", upload_id="upload_123_abc", name="report.pdf", user="owner-a", parent="victim-bucket"):
        return self.service.handle_chunk_upload(
            FileStorage(stream=io.BytesIO(content), filename="blob"), index, count,
            upload_id, name, parent_id=parent, user_id=user,
        )

    def merge(self, count=1, upload_id="upload_123_abc", name="report.pdf", user="owner-a", parent="victim-bucket"):
        return self.service.merge_chunks(upload_id, name, count, parent_id=parent, user_id=user)

    def test_owner_merge_preserves_contents_filename_and_user(self):
        self.assertEqual(self.chunk(b"second", index="1", count="2")["code"], 0)
        first = self.chunk(b"first", index="0", count="2")
        self.assertEqual(first["data"]["upload_id"], "upload_123_abc")
        self.assertTrue(first["data"]["is_complete"])
        self.assertEqual(self.merge(count=2)["code"], 0)
        self.assertEqual(self.storage_calls[0]["bytes"], b"firstsecond")
        self.assertEqual(self.storage_calls[0]["user_id"], "owner-a")
        self.assertEqual(self.storage_calls[0]["filename"], "report.pdf")
        self.assertRegex(self.storage_calls[0]["parent_id"], r"^[0-9a-f]{32}$")
        self.assertFalse(list(self.root.rglob("*.chunk")))
        self.assertFalse(list(self.root.glob("merged_*")))

    def test_other_owner_cannot_merge_victim_upload(self):
        self.chunk(b"secret-owner-a")
        self.assertEqual(self.merge(user="owner-b")["code"], 404)
        self.upload_mock.assert_not_called()
        self.assertEqual(self.merge()["code"], 0)
        self.assertEqual(self.storage_calls[0]["bytes"], b"secret-owner-a")

    def test_same_upload_id_and_filename_are_isolated_between_users(self):
        self.chunk(b"owner-a")
        self.chunk(b"owner-b", user="owner-b")
        self.assertEqual(len(list(self.root.rglob("0.chunk"))), 2)
        self.assertEqual(self.merge()["code"], 0)
        self.assertEqual(self.merge(user="owner-b")["code"], 0)
        self.assertEqual([call["bytes"] for call in self.storage_calls], [b"owner-a", b"owner-b"])
        self.assertEqual(len({call["parent_id"] for call in self.storage_calls}), 2)

    def test_overlapping_merges_have_private_temporary_outputs(self):
        self.chunk(b"owner-a")
        self.chunk(b"owner-b", user="owner-b")
        original_save = self.upload_mock.side_effect

        def interleaved_save(files, parent_id=None, user_id=None):
            if user_id == "owner-a":
                self.assertEqual(self.merge(user="owner-b")["code"], 0)
            else:
                self.assertEqual(len(list(self.root.glob("merged_*"))), 2)
            return original_save(files, parent_id=parent_id, user_id=user_id)

        self.upload_mock.side_effect = interleaved_save
        self.assertEqual(self.merge()["code"], 0)
        self.assertEqual([call["bytes"] for call in self.storage_calls], [b"owner-b", b"owner-a"])
        self.assertFalse(list(self.root.glob("merged_*")))

    def test_scoped_identifier_cannot_be_spoofed_or_prefix_collided(self):
        pairs = (("a_b", "c"), ("a", "b_c"), ("ab", "c"), ("a", "bc"))
        for owner, upload_id in pairs:
            self.assertEqual(self.chunk(owner.encode(), user=owner, upload_id=upload_id)["code"], 0)
        self.assertEqual(len(self.redis.hashes), 4)
        scoped_id = next(iter(self.redis.hashes)).split(":")[2]
        self.assertEqual(self.merge(user="attacker", upload_id=scoped_id)["code"], 404)
        for path in self.root.rglob("*.chunk"):
            self.assertRegex(path.parent.name, r"^[0-9a-f]{64}$")

    def test_path_traversal_ids_rejected_before_storage_io(self):
        for upload_id in ("../escape", "/tmp/escape", "a/b", "a\\b", ".", "..", "a:info", "", "a" * 129, None, {}, 123):
            with self.subTest(upload_id=upload_id):
                self.assertEqual(self.chunk(upload_id=upload_id)["code"], 400)
                self.assertEqual(self.merge(upload_id=upload_id)["code"], 400)
        self.redis_connection.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_path_traversal_and_invalid_filenames_rejected_before_io(self):
        for name in ("../escape.pdf", "/tmp/escape.pdf", "a/b.pdf", "a\\b.pdf", "bad\x00.pdf", "a\n.pdf", "a\x7f.pdf", "", ".", "..", None, {}, "payload.exe", "a" * 256 + ".pdf"):
            with self.subTest(name=name):
                self.assertEqual(self.chunk(name=name)["code"], 400)
                self.assertEqual(self.merge(name=name)["code"], 400)
        self.redis_connection.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_unicode_filename_remains_supported(self):
        self.assertEqual(self.chunk(name="项目 报告.pdf")["code"], 0)
        self.assertEqual(self.merge(name="项目 报告.pdf")["code"], 0)
        self.assertEqual(self.storage_calls[0]["filename"], "项目 报告.pdf")

    def test_noncanonical_and_out_of_bounds_numbers_fail_before_io(self):
        for value in ("01", "+1", " 1", "1 ", "1.0", "1e1", "١", "-1", "0x1", True, False, 1.0, [], {}, None, "9" * 100, 10001):
            with self.subTest(value=value):
                self.assertEqual(self.chunk(index=value)["code"], 400)
                self.assertEqual(self.chunk(count=value)["code"], 400)
                self.assertEqual(self.merge(count=value)["code"], 400)
        for value in (0, "0", -1, "-1"):
            self.assertEqual(self.chunk(count=value)["code"], 400)
            self.assertEqual(self.merge(count=value)["code"], 400)
        self.assertEqual(self.chunk(index="2", count="2")["code"], 400)
        self.redis_connection.assert_not_called()

    def test_maximum_chunk_bound_is_accepted(self):
        self.assertEqual(self.chunk(index="9999", count="10000")["code"], 0)
        self.assertEqual(self.merge(count=10000)["code"], 400)

    def test_missing_owner_fails_closed_before_io(self):
        for owner in (None, "", {}, [], True):
            self.assertEqual(self.chunk(user=owner)["code"], 400)
            self.assertEqual(self.merge(user=owner)["code"], 400)
        self.redis_connection.assert_not_called()

    def test_metadata_cannot_be_changed_by_later_chunks_or_merge(self):
        self.chunk(b"original", count="2")
        self.assertEqual(self.chunk(b"overwrite", name="other.pdf", count="2")["code"], 400)
        self.assertEqual(self.chunk(b"overwrite", count="1")["code"], 400)
        self.assertEqual(self.merge(name="other.pdf", count=2)["code"], 400)
        self.assertEqual(self.merge(count=1)["code"], 400)
        self.assertEqual(next(self.root.rglob("0.chunk")).read_bytes(), b"original")
        self.upload_mock.assert_not_called()

    def test_client_parent_is_ignored_on_both_chunk_and_merge(self):
        self.chunk(parent="victim-one")
        metadata = json.loads(next(iter(self.redis.hashes.values()))["metadata"])
        self.assertEqual(self.merge(parent="victim-two")["code"], 0)
        self.assertEqual(self.storage_calls[0]["parent_id"], metadata["parent_id"])
        self.assertNotIn(self.storage_calls[0]["parent_id"], ("victim-one", "victim-two"))

    def test_missing_chunks_cannot_be_merged(self):
        self.chunk(count="2")
        self.assertEqual(self.merge(count=2)["code"], 400)
        self.upload_mock.assert_not_called()
        self.assertFalse(list(self.root.glob("merged_*")))

    def test_missing_chunk_file_cannot_be_merged_even_if_bitmap_is_set(self):
        self.chunk()
        next(self.root.rglob("0.chunk")).unlink()
        self.assertEqual(self.merge()["code"], 400)
        self.upload_mock.assert_not_called()

    def test_completed_upload_cannot_be_reused(self):
        self.chunk()
        self.assertEqual(self.merge()["code"], 0)
        self.assertEqual(self.merge()["code"], 400)
        self.assertEqual(self.chunk(b"replacement")["code"], 400)
        self.assertEqual(len(self.storage_calls), 1)

    def test_failed_storage_keeps_chunks_but_cleans_merged_temporary_file(self):
        self.chunk()
        self.upload_mock.side_effect = None
        self.upload_mock.return_value = {"code": 0, "data": [{"status": "failed"}]}
        self.assertEqual(self.merge()["code"], 500)
        self.assertTrue(list(self.root.rglob("0.chunk")))
        self.assertFalse(list(self.root.glob("merged_*")))

    def test_upload_exception_cleans_partial_temporary_chunk(self):
        chunk = Mock()
        chunk.save.side_effect = RuntimeError("storage failure")
        with patch("builtins.print"):
            result = self.service.handle_chunk_upload(chunk, "0", "1", "upload_test", "report.pdf", user_id="owner")
        self.assertEqual(result["code"], 500)
        self.assertFalse(list(self.root.rglob("chunk_*")))
        self.assertFalse(self.redis.bits)

    def test_routes_require_verified_owner(self):
        self.auth.return_value = None
        self.assertEqual(self.client.post("/files/upload/chunk").status_code, 401)
        self.assertEqual(self.client.post("/files/upload/merge", json={}).status_code, 401)
        self.redis_connection.assert_not_called()

    def test_actual_routes_pass_owner_ignore_parent_and_preserve_contract(self):
        response = self.client.post("/files/upload/chunk", data={
            "chunk": (io.BytesIO(b"route-bytes"), "blob"),
            "chunkIndex": "0", "totalChunks": "1", "uploadId": "upload_route",
            "fileName": "report.pdf", "parent_id": "victim-bucket",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["upload_id"], "upload_route")
        self.auth.return_value = {"user_id": "owner-b", "role": "user"}
        data = {"uploadId": "upload_route", "fileName": "report.pdf", "totalChunks": 1, "parentId": "victim-bucket"}
        self.assertEqual(self.client.post("/files/upload/merge", json=data).status_code, 404)
        self.auth.return_value = {"user_id": "owner-a", "role": "user"}
        self.assertEqual(self.client.post("/files/upload/merge", json=data).status_code, 200)
        self.assertEqual(self.storage_calls[0]["bytes"], b"route-bytes")
        self.assertEqual(self.storage_calls[0]["user_id"], "owner-a")
        self.assertNotEqual(self.storage_calls[0]["parent_id"], "victim-bucket")

    def test_routes_return_400_for_invalid_json_shapes_and_chunk_parameters(self):
        for value in ([], ["item"], "item", 1, True, None, {}):
            with self.subTest(value=value):
                response = self.client.post("/files/upload/merge", json=value)
                self.assertEqual(response.status_code, 400)
        response = self.client.post("/files/upload/merge", data="{", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/files/upload/chunk", data={
            "chunk": (io.BytesIO(b"content"), "blob"), "chunkIndex": "../escape",
            "totalChunks": "1", "uploadId": "upload_route", "fileName": "report.pdf",
        })
        self.assertEqual(response.status_code, 400)
        self.redis_connection.assert_not_called()

    def test_regular_upload_staging_is_private_even_for_same_filename(self):
        # Interleave another upload after the first writes its staging file.
        # The old shared filename path was overwritten/deleted by this upload.
        self.upload_patch.stop()
        stored = {}
        minio = Mock()
        minio.bucket_exists.return_value = True

        def put_object(bucket_name, object_name, data, length):
            stored[bucket_name] = data.read()

        minio.put_object.side_effect = put_object
        connection = Mock()
        patch.object(self.service, "get_minio_client", return_value=minio).start()
        patch.object(self.service, "get_db_connection", return_value=connection).start()
        inner = FileStorage(stream=io.BytesIO(b"inner"), filename="same.pdf")
        outer = FileStorage(stream=io.BytesIO(b"outer"), filename="same.pdf")
        original_save = outer.save

        def interleaved_save(path):
            original_save(path)
            self.assertEqual(self.service.upload_files_to_server([inner], parent_id="inner-bucket", user_id="inner-user")["data"][0]["status"], "success")
            self.assertEqual(Path(path).read_bytes(), b"outer")

        outer.save = interleaved_save
        with patch("builtins.print"):
            result = self.service.upload_files_to_server([outer], parent_id="outer-bucket", user_id="outer-user")
        self.assertEqual(result["data"][0]["status"], "success")
        self.assertEqual(stored, {"inner-bucket": b"inner", "outer-bucket": b"outer"})
        self.assertFalse(list((self.root / "uploads").iterdir()))
        inserted_records = [call.args[1] for call in connection.cursor.return_value.execute.call_args_list]
        self.assertEqual({record[3] for record in inserted_records}, {"inner-user", "outer-user"})


if __name__ == "__main__":
    unittest.main()
