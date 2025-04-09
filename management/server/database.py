import mysql.connector
import os
from utils import generate_uuid, encrypt_password
from datetime import datetime

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

# 数据库连接配置
db_config = {
    "host": DB_HOST,
    "port": 5455,
    "user": "root",
    "password": "infini_rag_flow",
    "database": "rag_flow",
}