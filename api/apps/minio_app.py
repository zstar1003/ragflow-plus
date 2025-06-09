import os


@manager.route("/endpoint", methods=["GET"])  # noqa: F821
# @login_required
def minio():
    """
    Constructs the MinIO endpoint URL based on environment variables.
    """
    return os.getenv("MINIO_VISIT_HOST", "localhost") + ":" + os.getenv("MINIO_PORT", "9000") + "/"
