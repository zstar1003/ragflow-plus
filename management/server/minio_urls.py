"""Public MinIO URLs, independent of the internal storage connection.

Kept identical to management/server/minio_urls.py because the two Docker images
have separate build contexts. The parity regression prevents drift.
"""
import os
from urllib.parse import quote, urlsplit, urlunsplit


def minio_public_url(object_path=""):
    host = os.environ.get("MINIO_VISIT_HOST", "localhost").strip() or "localhost"
    explicit_scheme = "://" in host
    parsed = urlsplit(host if explicit_scheme else "http://" + host)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("MINIO_VISIT_HOST must be an HTTP(S) URL or hostname")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ValueError("MINIO_VISIT_HOST must not contain credentials, a query or fragment")
    port = parsed.port  # Validate a supplied port before constructing the URL.
    netloc = parsed.netloc
    if not explicit_scheme and port is None:
        port = int(os.environ.get("MINIO_PORT", "9000"))
        if not 1 <= port <= 65535:
            raise ValueError("MINIO_PORT must be between 1 and 65535")
        netloc += ":" + str(port)
    path = parsed.path.rstrip("/") + "/"
    if object_path:
        path += quote(str(object_path).lstrip("/"), safe="/%")
    return urlunsplit((parsed.scheme, netloc, path, "", ""))
