import os

from minio import Minio


# 检测是否在Docker容器中运行
def is_running_in_docker():
    # 检查是否存在/.dockerenv文件
    docker_env = os.path.exists("/.dockerenv")
    # 或者检查cgroup中是否包含docker字符串
    try:
        with open("/proc/self/cgroup", "r") as f:
            return docker_env or "docker" in f.read()
    except:  # noqa: E722
        return docker_env


# 根据运行环境选择合适的主机地址和端口
if is_running_in_docker():
    MINIO_HOST = "minio"
    MINIO_VISIT_HOST = os.getenv("MINIO_VISIT_HOST", "localhost")
    MINIO_PORT = int(os.getenv("MINIO_PORT", "9000"))
else:
    MINIO_HOST = os.getenv("MINIO_HOST", "localhost")
    MINIO_VISIT_HOST = os.getenv("MINIO_VISIT_HOST", "localhost")
    MINIO_PORT = int(os.getenv("MINIO_PORT", "9000"))


# MinIO连接配置
MINIO_CONFIG = {
    "endpoint": f"{MINIO_HOST}:{MINIO_PORT}",
    "access_key": os.getenv("MINIO_USER", "rag_flow"),
    "secret_key": os.getenv("MINIO_PASSWORD", "infini_rag_flow"),
    "secure": False,
    "visit_point": f"{MINIO_VISIT_HOST}:{MINIO_PORT}",
}


def get_minio_client():
    """创建MinIO客户端连接"""
    try:
        minio_client = Minio(endpoint=MINIO_CONFIG["endpoint"], access_key=MINIO_CONFIG["access_key"], secret_key=MINIO_CONFIG["secret_key"], secure=MINIO_CONFIG["secure"])
        return minio_client
    except Exception as e:
        print(f"MinIO连接失败: {str(e)}")
        raise e
