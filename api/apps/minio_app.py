import os

from flask import jsonify


@manager.route("/endpoint", methods=["GET"])  # noqa: F821
def minio():
    host = os.getenv("MINIO_VISIT_HOST", "localhost")
    if not host.startswith("http"):
        host = "http://" + host
    port = os.getenv("MINIO_PORT", "9000")
    return jsonify({"url": f"{host}:{port}/"})
