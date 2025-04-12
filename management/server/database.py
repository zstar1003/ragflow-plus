import mysql.connector
import os
from utils import generate_uuid, encrypt_password
from datetime import datetime
from minio import Minio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("../../docker/.env")

# 检测是否在Docker容器中运行
def is_running_in_docker():
    # 检查是否存在/.dockerenv文件
    docker_env = os.path.exists('/.dockerenv')
    # 或者检查cgroup中是否包含docker字符串
    try:
        with open('/proc/self/cgroup', 'r') as f:
            return docker_env or 'docker' in f.read()
    except:
        return docker_env

# 根据运行环境选择合适的主机地址
DB_HOST = 'host.docker.internal' if is_running_in_docker() else 'localhost'
MINIO_HOST = 'host.docker.internal' if is_running_in_docker() else 'localhost'

# 数据库连接配置
DB_CONFIG = {
    "host": DB_HOST,
    "port": int(os.getenv("MYSQL_PORT", "5455")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD", "infini_rag_flow"),
    "database": "rag_flow",
}

# MinIO连接配置
MINIO_CONFIG = {
    "endpoint": f"{MINIO_HOST}:{os.getenv('MINIO_PORT', '9000')}",
    "access_key": os.getenv("MINIO_USER", "rag_flow"),
    "secret_key": os.getenv("MINIO_PASSWORD", "infini_rag_flow"),
    "secure": False
}

def get_db_connection():
    """创建MySQL数据库连接"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"MySQL连接失败: {str(e)}")
        raise e

def get_minio_client():
    """创建MinIO客户端连接"""
    try:
        minio_client = Minio(
            endpoint=MINIO_CONFIG["endpoint"],
            access_key=MINIO_CONFIG["access_key"],
            secret_key=MINIO_CONFIG["secret_key"],
            secure=MINIO_CONFIG["secure"]
        )
        return minio_client
    except Exception as e:
        print(f"MinIO连接失败: {str(e)}")
        raise e

def test_connections():
    """测试数据库和MinIO连接"""
    try:
        # 测试MySQL连接
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        db_conn.close()
        print("MySQL连接测试成功")
        
        # 测试MinIO连接
        minio_client = get_minio_client()
        buckets = minio_client.list_buckets()
        print(f"MinIO连接测试成功，共有 {len(buckets)} 个存储桶")
        
        return True
    except Exception as e:
        print(f"连接测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    # 如果直接运行此文件，则测试连接
    test_connections()