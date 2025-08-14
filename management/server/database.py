import os
from pathlib import Path

import mysql.connector
import redis
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from minio import Minio
from root_path import get_root_folder

# 환경 변수 로드
env_path = Path(get_root_folder()) / "docker" / ".env"
load_dotenv(env_path)


# Docker 컨테이너에서 실행 중인지 확인
def is_running_in_docker():
    # /.dockerenv 파일 존재 여부 확인
    docker_env = os.path.exists("/.dockerenv")
    # 또는 cgroup에 docker 문자열이 포함되어 있는지 확인
    try:
        with open("/proc/self/cgroup", "r") as f:
            return docker_env or "docker" in f.read()
    except:  # noqa: E722
        return docker_env


# 실행 환경에 따라 적절한 호스트 주소와 포트 선택
if is_running_in_docker():
    MYSQL_HOST = "mysql"
    MYSQL_PORT = 3306
    MINIO_HOST = "minio"
    MINIO_PORT = 9000
    ES_HOST = "es01"
    ES_PORT = 9200
    REDIS_HOST = "redis"
    REDIS_PORT = 6379
else:
    MYSQL_HOST = "localhost"
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "5455"))
    MINIO_HOST = "localhost"
    MINIO_PORT = int(os.getenv("MINIO_PORT", "9000"))
    ES_HOST = "localhost"
    ES_PORT = int(os.getenv("ES_PORT", "9200"))
    REDIS_HOST = "localhost"
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


# 데이터베이스 연결 설정
DB_CONFIG = {
    "host": MYSQL_HOST,
    "port": MYSQL_PORT,
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD", "infini_rag_flow"),
    "database": "rag_flow",
}

# MinIO 연결 설정
MINIO_CONFIG = {
    "endpoint": f"{MINIO_HOST}:{MINIO_PORT}",
    "access_key": os.getenv("MINIO_USER", "rag_flow"),
    "secret_key": os.getenv("MINIO_PASSWORD", "infini_rag_flow"),
    "secure": False,
}

# Elasticsearch 연결 설정
ES_CONFIG = {
    "host": f"http://{ES_HOST}:{ES_PORT}",
    "user": os.getenv("ELASTIC_USER", "elastic"),
    "password": os.getenv("ELASTIC_PASSWORD", "infini_rag_flow"),
    "use_ssl": os.getenv("ES_USE_SSL", "false").lower() == "true",
}

# Redis 연결 설정
REDIS_CONFIG = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "password": os.getenv("REDIS_PASSWORD", "infini_rag_flow"),
    "decode_responses": False,
}


def get_db_connection():
    """MySQL 데이터베이스 연결 생성"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"MySQL 연결 실패: {str(e)}")
        raise e


def get_minio_client():
    """MinIO 클라이언트 연결 생성"""
    try:
        minio_client = Minio(endpoint=MINIO_CONFIG["endpoint"], access_key=MINIO_CONFIG["access_key"], secret_key=MINIO_CONFIG["secret_key"], secure=MINIO_CONFIG["secure"])
        return minio_client
    except Exception as e:
        print(f"MinIO 연결 실패: {str(e)}")
        raise e


def get_es_client():
    """Elasticsearch 클라이언트 연결 생성"""
    try:
        # 연결 파라미터 구성
        es_params = {"hosts": [ES_CONFIG["host"]]}

        # 인증 정보 추가
        if ES_CONFIG["user"] and ES_CONFIG["password"]:
            es_params["basic_auth"] = (ES_CONFIG["user"], ES_CONFIG["password"])

        # SSL 설정 추가
        if ES_CONFIG["use_ssl"]:
            es_params["use_ssl"] = True
            es_params["verify_certs"] = False  # 개발 환경에서는 False, 운영 환경에서는 True로 설정

        es_client = Elasticsearch(**es_params)
        return es_client
    except Exception as e:
        print(f"Elasticsearch 연결 실패: {str(e)}")
        raise e


def get_redis_connection():
    """Redis 연결 생성"""
    try:
        # 설정을 사용하여 Redis 연결 생성
        r = redis.Redis(**REDIS_CONFIG)
        # 연결 테스트
        r.ping()
        return r
    except Exception as e:
        print(f"Redis 연결 실패: {str(e)}")
        raise e


def test_connections():
    """데이터베이스와 MinIO 연결 테스트"""
    try:
        # MySQL 연결 테스트
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        db_conn.close()
        print("MySQL 연결 테스트 성공")

        # MinIO 연결 테스트
        minio_client = get_minio_client()
        buckets = minio_client.list_buckets()
        print(f"MinIO 연결 테스트 성공, 총 {len(buckets)}개의 버킷")

        # Elasticsearch 연결 테스트
        try:
            es_client = get_es_client()
            es_info = es_client.info()
            print(f"Elasticsearch 연결 테스트 성공, 버전: {es_info.get('version', {}).get('number', '알 수 없음')}")
        except Exception as e:
            print(f"Elasticsearch 연결 테스트 실패: {str(e)}")

        return True
    except Exception as e:
        print(f"연결 테스트 실패: {str(e)}")
        return False


if __name__ == "__main__":
    # 이 파일을 직접 실행하면 연결 테스트 수행
    test_connections()
