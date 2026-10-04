"""Explicit, fail-closed management permissions.

JWTs carry the role selected at login and expire after one hour. Resource access
is checked against current ownership; role revocation takes effect at the next
login/expiry (or immediately by rotating MANAGEMENT_JWT_SECRET).
"""

from flask import current_app, g, jsonify, request

from .auth_utils import get_current_user_from_token, is_admin, _nonempty_string


# These handlers already apply the validated token's user/tenant filter, or only
# operate on the authenticated user. Never allow a route just by URL prefix.
OWNER_ROUTES = {
    ("users.get_current_user", "GET"),
    ("teams.get_teams", "GET"),
    ("files.get_files", "GET"),
    ("files.upload_file", "POST"),
    ("files.upload_chunk", "POST"),
    ("files.merge_upload", "POST"),
    ("knowledgebases.get_knowledgebase_list", "GET"),
}
TEAM_ROUTES = {
    ("teams.get_team", "GET"),
    ("teams.get_team_members_route", "GET"),
    ("teams.add_team_member_route", "POST"),
    ("teams.remove_team_member_route", "DELETE"),
}
FILE_ROUTES = {
    ("files.download_file", "GET"),
    ("files.delete_file_route", "DELETE"),
}
KB_ROUTES = {
    ("knowledgebases.get_knowledgebase_detail", "GET"),
    ("knowledgebases.update_knowledgebase", "PUT"),
    ("knowledgebases.delete_knowledgebase", "DELETE"),
    ("knowledgebases.get_knowledgebase_documents", "GET"),
    ("knowledgebases.add_documents_to_knowledgebase", "POST"),
    ("knowledgebases.start_sequential_batch_parse_route", "POST"),
    ("knowledgebases.get_sequential_batch_parse_progress_route", "GET"),
    ("knowledgebases.get_tenant_embedding_models", "GET"),
}
DOCUMENT_ROUTES = {
    ("knowledgebases.delete_document", "DELETE"),
    ("knowledgebases.get_parse_progress", "GET"),
    ("knowledgebases.parse_document", "POST"),
}


def _query_rows(query, params):
    # Lazy import: auth/startup never connects to storage infrastructure.
    from database import get_db_connection

    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def _owns_resources(kind, resource_ids, user, *, deleting=False):
    if not isinstance(resource_ids, list) or not resource_ids:
        return False
    if any(not _nonempty_string(resource_id) for resource_id in resource_ids):
        return False
    ids = set(resource_ids)
    placeholders = ", ".join(["%s"] * len(ids))
    # Only these fixed SQL fragments are selectable. IDs always use parameters.
    queries = {
        "file": ("SELECT id FROM file WHERE created_by = %s AND id", user["user_id"]),
        "knowledgebase": ("SELECT id FROM knowledgebase WHERE tenant_id = %s AND id", user["tenant_id"]),
        "document": (
            "SELECT d.id FROM document d JOIN knowledgebase k ON d.kb_id = k.id "
            "WHERE k.tenant_id = %s AND d.id", user["tenant_id"],
        ),
    }
    query, scope = queries[kind]
    rows = _query_rows(f"{query} IN ({placeholders})", (scope, *sorted(ids)))
    if {row["id"] for row in rows} != ids:
        return False
    if kind == "file" and deleting:
        # Deleting a file cascades to its linked documents. Do not allow an
        # owner to delete documents belonging to another (or missing) tenant.
        foreign_links = _query_rows(
            "SELECT f2d.file_id FROM file2document f2d "
            "LEFT JOIN document d ON f2d.document_id = d.id "
            "LEFT JOIN knowledgebase k ON d.kb_id = k.id "
            f"WHERE f2d.file_id IN ({placeholders}) "
            "AND (k.tenant_id IS NULL OR k.tenant_id <> %s)",
            (*sorted(ids), user["tenant_id"]),
        )
        return not foreign_links
    return True


def _json_object():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _can_manage_member(user, key):
    data = _json_object()
    if key[1] == "POST":
        target = data.get("userId")
        # Owners cannot mint management access or demote an existing owner.
        if data.get("role", "member") not in ("normal", "member"):
            return False
    else:
        target = request.view_args.get("user_id")
    if not _nonempty_string(target):
        return False
    rows = _query_rows(
        "SELECT role FROM user_tenant WHERE tenant_id = %s AND user_id = %s",
        (user["tenant_id"], target),
    )
    return all(row["role"] != "owner" for row in rows)


def _select_owner_embedding(user, requested_model=None):
    rows = _query_rows(
        "SELECT llm_name FROM tenant_llm WHERE tenant_id = %s "
        "AND model_type = 'embedding' ORDER BY create_time DESC",
        (user["tenant_id"],),
    )
    models = [row["llm_name"] for row in rows if _nonempty_string(row.get("llm_name"))]
    if requested_model is None and models:
        return models[0]
    if not _nonempty_string(requested_model):
        return None
    for model in models:
        if requested_model in (model, model.split("___")[0]):
            return model
    return None


def _owner_is_allowed(user):
    method = "GET" if request.method == "HEAD" else request.method
    key = (request.endpoint, method)
    if key in OWNER_ROUTES:
        return True
    args = request.view_args or {}
    if key in TEAM_ROUTES:
        if args.get("team_id") != user["tenant_id"]:
            return False
        return method == "GET" or _can_manage_member(user, key)
    if key in FILE_ROUTES:
        return _owns_resources("file", [args.get("file_id")], user, deleting=method == "DELETE")
    if key == ("files.batch_delete_files_route", "DELETE"):
        return _owns_resources("file", _json_object().get("ids"), user, deleting=True)
    if key == ("knowledgebases.create_knowledgebase", "POST"):
        data = _json_object()
        if any(field in data for field in ("tenant_id", "created_by", "creator_id")):
            return False
        # Do not use the service's global model fallback for an owner.
        g.management_embedding_id = _select_owner_embedding(user, data.get("embd_id"))
        return g.management_embedding_id is not None
    if key in KB_ROUTES:
        if not _owns_resources("knowledgebase", [args.get("kb_id")], user):
            return False
        data = _json_object() if method in ("POST", "PUT") else {}
        # Do not trust caller-supplied ownership metadata, even if a service
        # currently ignores it. Future fields must not create a tenant escape.
        if any(field in data for field in ("tenant_id", "created_by", "creator_id")):
            return False
        if key == ("knowledgebases.update_knowledgebase", "PUT") and "embd_id" in data:
            if _select_owner_embedding(user, data["embd_id"]) is None:
                return False
        if key == ("knowledgebases.add_documents_to_knowledgebase", "POST"):
            return _owns_resources("file", data.get("file_ids"), user)
        return True
    if key == ("knowledgebases.batch_delete_knowledgebase", "DELETE"):
        return _owns_resources("knowledgebase", _json_object().get("ids"), user)
    if key in DOCUMENT_ROUTES:
        return _owns_resources("document", [args.get("doc_id")], user)
    # Includes global users/tenants/conversations, embedding credentials,
    # unsupported verbs, and newly added routes.
    return False


def protect_management_api():
    """Application-wide guard; run before any API handler or its side effects."""
    if request.path != "/api" and not request.path.startswith("/api/"):
        return None
    if request.method == "OPTIONS":
        # Some legacy explicit OPTIONS handlers run downloads or other work.
        # Always produce the preflight here; Flask-CORS supplies CORS headers.
        if request.url_rule is not None:
            return current_app.make_default_options_response()
        return None
    if request.endpoint == "login" and request.method == "POST":
        return None
    user = get_current_user_from_token()
    if user is None:
        response = jsonify({"code": 401, "message": "未提供有效的认证令牌"})
        response.status_code = 401
        response.headers["WWW-Authenticate"] = "Bearer"
        return response
    if is_admin(user):
        return None
    try:
        if _owner_is_allowed(user):
            return None
    except Exception:
        current_app.logger.exception("Management resource authorization failed")
        return jsonify({"code": 503, "message": "暂时无法验证资源权限"}), 503
    return jsonify({"code": 403, "message": "无权访问此管理接口或资源"}), 403
