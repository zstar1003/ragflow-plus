import mysql.connector
from utils import generate_uuid, encrypt_password
from datetime import datetime

# 数据库连接配置
db_config = {
    # "host": "host.docker.internal", # 如果是在Docke容器内部访问数据库
    "host": "localhost",
    "port": 5455,
    "user": "root",
    "password": "infini_rag_flow",
    "database": "rag_flow",
}