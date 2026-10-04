"""Management API authorization regressions with real Flask routes.

Only backing services/database calls are mocked; no live infrastructure is used.
Run: python -m unittest discover -s management/server/tests -v
"""

import importlib
import importlib.util
import logging
import os
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import Mock, patch

import jwt
from flask import jsonify

SERVER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_ROOT))
SECRET = "test-management-auth-key-0123456789abcdef"
ADMIN = {"id": "admin", "username": "admin", "role": "admin", "tenant_id": None}
OWNER = {"id": "owner-id", "username": "owner", "role": "team_owner", "tenant_id": "own-tenant"}

SERVICE_FUNCTIONS = {
    "users": ["authenticate_user", "get_users_with_pagination", "delete_user", "create_user", "update_user", "reset_user_password", "get_user_info_by_id"],
    "teams": ["get_teams_with_pagination", "get_team_by_id", "delete_team", "get_team_members", "add_team_member", "remove_team_member"],
    "tenants": ["get_tenants_with_pagination", "update_tenant"],
    "conversation": ["get_conversations_by_user_id", "get_messages_by_conversation_id"],
    "files": ["batch_delete_files", "delete_file", "download_file_from_minio", "get_file_info", "get_files_list", "handle_chunk_upload", "merge_chunks", "upload_files_to_server"],
}
KB_FUNCTIONS = [
    "get_knowledgebase_list", "get_knowledgebase_detail", "create_knowledgebase", "update_knowledgebase",
    "delete_knowledgebase", "batch_delete_knowledgebase", "get_knowledgebase_documents",
    "add_documents_to_knowledgebase", "delete_document", "get_document_parse_progress", "parse_document",
    "get_system_embedding_config", "set_system_embedding_config", "start_sequential_batch_parse_async",
    "get_sequential_batch_parse_progress", "get_tenant_embedding", "get_kb_embedding_config",
]


def module_stub(name, **attributes):
    module = types.ModuleType(name)
    module.__dict__.update(attributes)
    return module


@contextmanager
def management_app():
    services = {}
    modules = {}
    for service, functions in SERVICE_FUNCTIONS.items():
        module = module_stub(f"services.{service}.service")
        for name in functions:
            setattr(module, name, Mock(name=name, return_value=True))
        services[service] = module
        modules[module.__name__] = module
    kb = types.SimpleNamespace(**{name: Mock(name=name, return_value={}) for name in KB_FUNCTIONS})
    services["knowledgebases"] = kb
    modules["services.knowledgebases.service"] = module_stub("services.knowledgebases.service", KnowledgebaseService=kb)
    modules["services.files.utils"] = module_stub("services.files.utils", FileType=types.SimpleNamespace(FOLDER=types.SimpleNamespace(value="folder")))
    modules["utils"] = module_stub(
        "utils",
        success_response=lambda data=None, message="成功", code=0: jsonify(code=code, data=data, message=message),
        error_response=lambda message="失败", code=500, **kwargs: (jsonify(code=code, message=message), code),
    )
    services["users"].authenticate_user.return_value = (True, ADMIN, None)
    services["users"].get_user_info_by_id.return_value = dict(ADMIN, roles=["admin"])
    for service, function in (
        ("users", "get_users_with_pagination"), ("teams", "get_teams_with_pagination"),
        ("tenants", "get_tenants_with_pagination"), ("files", "get_files_list"),
        ("conversation", "get_conversations_by_user_id"), ("conversation", "get_messages_by_conversation_id"),
    ):
        getattr(services[service], function).return_value = ([], 0)
    services["teams"].get_team_by_id.return_value = {"id": "own-tenant"}
    services["teams"].get_team_members.return_value = []
    services["files"].get_file_info.return_value = {"id": "own-file", "type": "pdf", "parent_id": "bucket", "location": "report.pdf"}
    services["files"].download_file_from_minio.return_value = (b"private report", "report.pdf")
    services["files"].upload_files_to_server.return_value = {"data": []}
    services["files"].handle_chunk_upload.return_value = {"code": 0}
    services["files"].merge_chunks.return_value = {"code": 0}
    services["files"].batch_delete_files.return_value = 1
    kb.get_knowledgebase_detail.return_value = {"id": "own-kb"}
    kb.update_knowledgebase.return_value = {"id": "own-kb"}
    kb.parse_document.return_value = {"success": True}
    kb.start_sequential_batch_parse_async.return_value = {"success": True}
    kb.set_system_embedding_config.return_value = (True, "saved")

    with patch.dict(sys.modules, modules), patch.dict(os.environ, {
        "MANAGEMENT_JWT_SECRET": SECRET,
        "MANAGEMENT_ADMIN_PASSWORD": "test-admin-password-for-regressions",
    }), tempfile.TemporaryDirectory() as directory:
        for name in list(sys.modules):
            if name == "routes" or name.startswith("routes."):
                del sys.modules[name]
        spec = importlib.util.spec_from_file_location("management_auth_test_app", SERVER_ROOT / "app.py")
        app_module = importlib.util.module_from_spec(spec)
        previous_cwd = os.getcwd()
        try:
            os.chdir(directory)
            with patch("logging.FileHandler", return_value=logging.NullHandler()):
                spec.loader.exec_module(app_module)
            app_module.app.config["TESTING"] = True
            permissions = importlib.import_module("services.auth.permissions")
            yield app_module, services, permissions
        finally:
            os.chdir(previous_cwd)


def make_token(user=ADMIN, **changes):
    payload = {
        "user_id": user["id"], "username": user["username"], "role": user["role"],
        "tenant_id": user["tenant_id"], "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    payload.update(changes)
    return jwt.encode(payload, SECRET, algorithm="HS256")


def headers(user=ADMIN, **changes):
    return {"Authorization": "Bearer " + make_token(user, **changes)}


def mock_resource_rows(query, params):
    """Fixtures for the actual authorization queries, never for route handlers."""
    if query.startswith("SELECT f2d.file_id"):
        return []
    if query.startswith("SELECT role FROM user_tenant"):
        return [{"role": "owner"}] if params[1] == "another-owner" else []
    if query.startswith("SELECT llm_name FROM tenant_llm"):
        return [{"llm_name": "own-model___fixture"}] if params[0] == OWNER["tenant_id"] else []
    expected = "own-file" if "FROM file WHERE" in query else "own-doc" if "FROM document d" in query else "own-kb"
    scope = OWNER["id"] if expected == "own-file" else OWNER["tenant_id"]
    return [{"id": resource_id} for resource_id in params[1:] if resource_id == expected and params[0] == scope]


class ManagementAuthenticationTests(unittest.TestCase):
    def test_every_registered_api_method_requires_auth_before_service_calls(self):
        with management_app() as (module, services, permissions), patch.object(permissions, "_query_rows") as query:
            client = module.app.test_client()
            count = 0
            for rule in module.app.url_map.iter_rules():
                if not rule.rule.startswith("/api/") or rule.endpoint == "login":
                    continue
                path = re.sub(r"<[^>]+>", "target", rule.rule)
                for method in rule.methods - {"OPTIONS"}:
                    with self.subTest(path=path, method=method):
                        response = client.open(path, method=method, json={})
                        self.assertEqual(response.status_code, 401)
                        self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")
                        count += 1
            self.assertGreater(count, 40)
            query.assert_not_called()
            for service in services.values():
                for item in vars(service).values():
                    if isinstance(item, Mock):
                        item.assert_not_called()

    def test_login_is_the_only_public_business_endpoint(self):
        with management_app() as (module, services, _):
            client = module.app.test_client()
            response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "fixture"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(jwt.decode(response.json["data"]["token"], SECRET, algorithms=["HS256"])["role"], "admin")
            services["users"].authenticate_user.assert_called_once_with("admin", "fixture")
            for path in ("/api/v1/auth/login/", "/api/v1/auth/login/extra", "/api/v2/future", "/api"):
                self.assertEqual(client.post(path, json={}).status_code, 401)
            self.assertEqual(client.get("/api/v1/auth/login").status_code, 401)

    def test_every_preflight_is_public_and_never_runs_backend_work(self):
        with management_app() as (module, services, permissions), patch.object(permissions, "_query_rows") as query:
            client = module.app.test_client()
            for rule in module.app.url_map.iter_rules():
                if not rule.rule.startswith("/api/"):
                    continue
                path = re.sub(r"<[^>]+>", "target", rule.rule)
                method = next(iter(rule.methods - {"OPTIONS", "HEAD"}))
                with self.subTest(path=path):
                    response = client.options(path, headers={"Origin": "https://ui.example", "Access-Control-Request-Method": method, "Access-Control-Request-Headers": "Authorization, Content-Type"})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "https://ui.example")
                    self.assertIn("Authorization", response.headers.get("Access-Control-Allow-Headers", ""))
            query.assert_not_called()
            for service in services.values():
                for item in vars(service).values():
                    if isinstance(item, Mock):
                        item.assert_not_called()

    def test_invalid_expired_forged_and_incomplete_tokens_are_rejected(self):
        with management_app() as (module, services, _):
            client = module.app.test_client()
            bad_tokens = [
                "not-a-token",
                make_token(exp=datetime.now(timezone.utc) - timedelta(seconds=1)),
                jwt.encode({"user_id": "admin", "role": "admin"}, SECRET, algorithm="HS256"),
                jwt.encode({"user_id": "admin", "username": "admin", "role": "admin", "exp": 9999999999}, "wrong-key-long-enough-for-test-fixture", algorithm="HS256"),
                jwt.encode({"user_id": "admin", "username": "admin", "role": "admin", "exp": 9999999999}, SECRET, algorithm="HS384"),
            ]
            for field, values in {
                "user_id": [None, "", " ", 1, []], "username": [None, "", True, {}],
                "role": [None, "user", "ADMIN", [], {}], "exp": [None, "9999999999", True, float("inf"), float("nan")],
            }.items():
                bad_tokens.extend(make_token(**{field: value}) for value in values)
            for value in (None, "", " ", 0, [], {}):
                bad_tokens.append(make_token(OWNER, tenant_id=value))
            for token in bad_tokens:
                with self.subTest(token=token[:30]):
                    self.assertEqual(client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"}).status_code, 401)
            for value in ("", "Basic abc", "Bearer", "Bearer token extra", "Bearer " + make_token() + " extra"):
                self.assertEqual(client.get("/api/v1/users", headers={"Authorization": value}).status_code, 401)
            services["users"].get_users_with_pagination.assert_not_called()

    def test_authenticated_admin_retains_crud_settings_and_download(self):
        with management_app() as (module, services, permissions), patch.object(permissions, "_query_rows") as query:
            client = module.app.test_client()
            cases = [
                ("GET", "/api/v1/users", None), ("POST", "/api/v1/users", {"nickname": "fixture"}),
                ("PUT", "/api/v1/users/target", {"id": "target"}), ("DELETE", "/api/v1/users/target", None),
                ("PUT", "/api/v1/users/target/reset-password", {"password": "fixture"}),
                ("GET", "/api/v1/tenants", None), ("PUT", "/api/v1/tenants/target", {}),
                ("GET", "/api/v1/conversation?user_id=target", None),
                ("GET", "/api/v1/knowledgebases/system_embedding_config", None),
                ("POST", "/api/v1/knowledgebases/system_embedding_config", {"llm_name": "model", "api_base": "https://example.invalid"}),
                ("GET", "/api/v1/files/target/download", None),
            ]
            for method, path, data in cases:
                with self.subTest(path=path, method=method):
                    self.assertEqual(client.open(path, method=method, json=data, headers=headers()).status_code, 200)
            services["users"].delete_user.assert_called_once_with("target")
            services["files"].download_file_from_minio.assert_called_once_with("target")
            query.assert_not_called()

    def test_bearer_scheme_is_case_insensitive_and_shared_by_me(self):
        with management_app() as (module, services, _):
            response = module.app.test_client().get(
                "/api/v1/users/me", headers={"Authorization": "bearer   " + make_token()},
            )
            self.assertEqual(response.status_code, 200)
            services["users"].get_user_info_by_id.assert_called_once_with("admin")

    def test_principal_cache_cannot_leak_across_requests_in_shared_app_context(self):
        with management_app() as (module, services, _), module.app.app_context():
            client = module.app.test_client()
            self.assertEqual(client.get("/api/v1/users", headers=headers()).status_code, 200)
            self.assertEqual(client.get("/api/v1/users").status_code, 401)
            self.assertEqual(client.get("/api/v1/users", headers=headers(OWNER)).status_code, 403)
            services["users"].get_users_with_pagination.assert_called_once()

    def test_new_routes_are_protected_and_not_implicitly_granted_to_owners(self):
        with management_app() as (module, _, _):
            handler = Mock(return_value={"code": 0})
            module.app.add_url_rule("/api/v1/new-sensitive-operation", "new_sensitive_operation", lambda: handler(), methods=["GET", "POST"])
            client = module.app.test_client()
            self.assertEqual(client.get("/api/v1/new-sensitive-operation").status_code, 401)
            self.assertEqual(client.get("/api/v1/new-sensitive-operation", headers=headers(OWNER)).status_code, 403)
            handler.assert_not_called()
            self.assertEqual(client.get("/api/v1/new-sensitive-operation", headers=headers()).status_code, 200)
            handler.assert_called_once()


class ManagementOwnerAuthorizationTests(unittest.TestCase):
    def setUp(self):
        context = management_app()
        self.module, self.services, self.permissions = context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)
        self.client = self.module.app.test_client()
        self.query = patch.object(self.permissions, "_query_rows", side_effect=mock_resource_rows).start()
        self.addCleanup(patch.stopall)
        self.headers = headers(OWNER)

    def request(self, method, path, data=None):
        return self.client.open(path, method=method, json=data, headers=self.headers)

    def test_owner_global_admin_operations_are_forbidden_without_service_calls(self):
        cases = [
            ("GET", "/api/v1/users"), ("HEAD", "/api/v1/users"), ("POST", "/api/v1/users"),
            ("PUT", "/api/v1/users/target"), ("DELETE", "/api/v1/users/target"),
            ("PUT", "/api/v1/users/me"), ("DELETE", "/api/v1/users/me"),
            ("PUT", "/api/v1/users/target/reset-password"), ("GET", "/api/v1/tenants"),
            ("PUT", "/api/v1/tenants/own-tenant"), ("GET", "/api/v1/conversation?user_id=owner-id"),
            ("GET", "/api/v1/conversation/target/messages"), ("DELETE", "/api/v1/teams/own-tenant"),
            ("GET", "/api/v1/knowledgebases/system_embedding_config"),
            ("POST", "/api/v1/knowledgebases/system_embedding_config"),
            ("GET", "/api/v1/knowledgebases/embedding_config?kb_id=own-kb"),
            ("PATCH", "/api/v1/files/own-file"),
        ]
        for method, path in cases:
            with self.subTest(path=path, method=method):
                self.assertEqual(self.request(method, path, {}).status_code, 403)
        self.query.assert_not_called()
        for service in self.services.values():
            for item in vars(service).values():
                if isinstance(item, Mock):
                    item.assert_not_called()

    def test_owner_lists_use_signed_scope_and_ignore_supplied_scope(self):
        for path in ("files", "teams", "knowledgebases"):
            self.assertEqual(self.request("GET", f"/api/v1/{path}?user_id=foreign&tenant_id=foreign").status_code, 200)
        self.services["files"].get_files_list.assert_called_once_with(1, 10, "", "create_time", "desc", OWNER["id"])
        self.services["teams"].get_teams_with_pagination.assert_called_once_with(1, 10, "", "create_time", "desc", OWNER["tenant_id"])
        self.assertEqual(self.services["knowledgebases"].get_knowledgebase_list.call_args.kwargs["tenant_id"], OWNER["tenant_id"])
        self.query.assert_not_called()

    def test_owner_me_and_head_are_available(self):
        self.services["users"].get_user_info_by_id.return_value = dict(OWNER, roles=["team_owner"])
        self.assertEqual(self.request("GET", "/api/v1/users/me").status_code, 200)
        self.services["users"].get_user_info_by_id.assert_called_once_with(OWNER["id"])
        self.assertEqual(self.request("HEAD", "/api/v1/files").status_code, 200)

    def test_owner_resource_actions_allow_own_and_deny_foreign_ids(self):
        cases = [
            ("GET", "/api/v1/files/{id}/download", "own-file", None),
            ("DELETE", "/api/v1/files/{id}", "own-file", None),
            ("GET", "/api/v1/knowledgebases/{id}", "own-kb", None),
            ("PUT", "/api/v1/knowledgebases/{id}", "own-kb", {"name": "renamed"}),
            ("DELETE", "/api/v1/knowledgebases/{id}", "own-kb", None),
            ("GET", "/api/v1/knowledgebases/{id}/documents", "own-kb", None),
            ("POST", "/api/v1/knowledgebases/{id}/batch_parse_sequential/start", "own-kb", None),
            ("GET", "/api/v1/knowledgebases/{id}/batch_parse_sequential/progress", "own-kb", None),
            ("GET", "/api/v1/knowledgebases/embedding_models/{id}", "own-kb", None),
            ("DELETE", "/api/v1/knowledgebases/documents/{id}", "own-doc", None),
            ("POST", "/api/v1/knowledgebases/documents/{id}/parse", "own-doc", None),
            ("GET", "/api/v1/knowledgebases/documents/{id}/parse/progress", "own-doc", None),
        ]
        self.services["knowledgebases"].delete_knowledgebase.return_value = True
        for method, template, owned_id, data in cases:
            with self.subTest(path=template, method=method):
                self.assertEqual(self.request(method, template.format(id="foreign"), data).status_code, 403)
                self.assertEqual(self.request(method, template.format(id=owned_id), data).status_code, 200)

    def test_batch_and_document_import_check_every_id_before_mutation(self):
        for path, key, owned_id, service in (
            ("/api/v1/files/batch", "ids", "own-file", self.services["files"].batch_delete_files),
            ("/api/v1/knowledgebases/batch", "ids", "own-kb", self.services["knowledgebases"].batch_delete_knowledgebase),
            ("/api/v1/knowledgebases/own-kb/documents", "file_ids", "own-file", self.services["knowledgebases"].add_documents_to_knowledgebase),
        ):
            method = "POST" if key == "file_ids" else "DELETE"
            for ids in ([owned_id, "foreign"], [], None, owned_id, [None], [42], [{}]):
                with self.subTest(path=path, ids=ids):
                    self.assertEqual(self.request(method, path, {key: ids}).status_code, 403)
            service.assert_not_called()
            self.assertEqual(self.request(method, path, {key: [owned_id]}).status_code, 200)
            service.assert_called_once()
        self.assertEqual(self.services["knowledgebases"].add_documents_to_knowledgebase.call_args.kwargs["created_by"], OWNER["id"])
        self.assertEqual(self.request("POST", "/api/v1/knowledgebases/foreign/documents", {"file_ids": ["own-file"]}).status_code, 403)

    def test_owned_file_cannot_cascade_delete_another_tenants_documents(self):
        self.query.side_effect = lambda query, params: [{"file_id": "own-file"}] if query.startswith("SELECT f2d.file_id") else mock_resource_rows(query, params)
        self.assertEqual(self.request("DELETE", "/api/v1/files/own-file").status_code, 403)
        self.assertEqual(self.request("DELETE", "/api/v1/files/batch", {"ids": ["own-file"]}).status_code, 403)
        self.services["files"].delete_file.assert_not_called()
        self.services["files"].batch_delete_files.assert_not_called()

    def test_team_access_cannot_escape_tenant_or_grant_management_ownership(self):
        for suffix in ("", "/members"):
            self.assertEqual(self.request("GET", "/api/v1/teams/foreign" + suffix).status_code, 403)
            self.assertEqual(self.request("GET", "/api/v1/teams/own-tenant" + suffix).status_code, 200)
        for role in ("owner", "admin", "team_owner", {}, None):
            self.assertEqual(self.request("POST", "/api/v1/teams/own-tenant/members", {"userId": "target", "role": role}).status_code, 403)
        for method, suffix, data in (
            ("POST", "/members", {"userId": "another-owner", "role": "normal"}),
            ("DELETE", "/members/another-owner", None),
        ):
            self.assertEqual(self.request(method, "/api/v1/teams/own-tenant" + suffix, data).status_code, 403)
        self.services["teams"].add_team_member.assert_not_called()
        self.services["teams"].remove_team_member.assert_not_called()
        self.assertEqual(self.request("POST", "/api/v1/teams/own-tenant/members", {"userId": "target", "role": "normal"}).status_code, 200)
        self.assertEqual(self.request("DELETE", "/api/v1/teams/own-tenant/members/target").status_code, 200)

    def test_owner_creation_injects_identity_and_never_uses_global_model_fallback(self):
        response = self.request("POST", "/api/v1/knowledgebases", {"name": "owned"})
        self.assertEqual(response.status_code, 200)
        self.services["knowledgebases"].create_knowledgebase.assert_called_once_with(
            name="owned", creator_id=OWNER["tenant_id"], created_by=OWNER["id"], embd_id="own-model___fixture",
        )
        self.services["knowledgebases"].create_knowledgebase.reset_mock()
        for field in ("tenant_id", "created_by", "creator_id"):
            for method, path in (("POST", "/api/v1/knowledgebases"), ("PUT", "/api/v1/knowledgebases/own-kb")):
                self.assertEqual(self.request(method, path, {"name": "owned", field: "foreign"}).status_code, 403)
        self.assertEqual(self.request("POST", "/api/v1/knowledgebases", {"name": "owned", "embd_id": "foreign-model"}).status_code, 403)
        self.assertEqual(self.request("PUT", "/api/v1/knowledgebases/own-kb", {"embd_id": "foreign-model"}).status_code, 403)
        self.query.side_effect = lambda query, params: []
        self.assertEqual(self.request("POST", "/api/v1/knowledgebases", {"name": "owned"}).status_code, 403)
        self.services["knowledgebases"].create_knowledgebase.assert_not_called()

    def test_owned_embedding_model_remains_available_for_create_and_update(self):
        for method, path in (("POST", "/api/v1/knowledgebases"), ("PUT", "/api/v1/knowledgebases/own-kb")):
            self.assertEqual(self.request(method, path, {"name": "owned", "embd_id": "own-model"}).status_code, 200)

    def test_owner_upload_forwards_identity_and_isolates_storage_parent(self):
        response = self.client.post("/api/v1/files/upload", headers=self.headers, data={"files": (BytesIO(b"file"), "report.pdf"), "parent_id": "foreign"})
        self.assertEqual(response.status_code, 200)
        kwargs = self.services["files"].upload_files_to_server.call_args.kwargs
        self.assertEqual(kwargs["user_id"], OWNER["id"])
        self.assertRegex(kwargs["parent_id"], r"^[a-f0-9]{32}$")
        self.assertNotEqual(kwargs["parent_id"], "foreign")

    def test_owner_chunk_routes_forward_only_authenticated_identity(self):
        response = self.client.post("/api/v1/files/upload/chunk", headers=self.headers, data={
            "chunk": (BytesIO(b"fixture"), "chunk"), "chunkIndex": "0", "totalChunks": "1",
            "uploadId": "client-upload", "fileName": "report.pdf", "parent_id": "foreign",
            "user_id": "foreign-user",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.services["files"].handle_chunk_upload.call_args.kwargs, {"user_id": OWNER["id"]})
        response = self.request("POST", "/api/v1/files/upload/merge", {
            "uploadId": "client-upload", "fileName": "report.pdf", "totalChunks": 1,
            "parentId": "foreign", "user_id": "foreign-user",
        })
        self.assertEqual(response.status_code, 200)
        self.services["files"].merge_chunks.assert_called_once_with(
            "client-upload", "report.pdf", 1, user_id=OWNER["id"],
        )

    def test_authorization_backend_failure_is_fail_closed(self):
        self.query.side_effect = RuntimeError("fixture storage failure")
        self.assertEqual(self.request("DELETE", "/api/v1/files/own-file").status_code, 503)
        self.services["files"].delete_file.assert_not_called()

    def test_resource_queries_parameterize_ids_and_tenant(self):
        with self.module.app.test_request_context():
            injection = "' OR 1=1 --"
            self.assertFalse(self.permissions._owns_resources("file", [injection], {"user_id": "owner", "tenant_id": "tenant"}))
        query, params = self.query.call_args.args
        self.assertNotIn(injection, query)
        self.assertEqual(params, ("owner", injection))
        self.assertEqual(query.count("%s"), 2)


if __name__ == "__main__":
    unittest.main()
