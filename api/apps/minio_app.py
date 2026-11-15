from flask import jsonify
from api.utils.minio_urls import minio_public_url


@manager.route("/endpoint", methods=["GET"])  # noqa: F821
def minio():
    return jsonify({"url": minio_public_url()})
