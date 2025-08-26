import os
from dotenv import load_dotenv
import mysql.connector
from minio import Minio

# 환경 변수 로드
load_dotenv("../../docker/.env")

# 데이터베이스 연결 설정
DB_CONFIG = {
    "host": "localhost",
    "port": int(os.getenv("MYSQL_PORT", "5455")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD", "infini_rag_flow"),
    "database": "rag_flow"
}

# MinIO 연결 설정
MINIO_CONFIG = {
    "endpoint": "localhost:" + os.getenv("MINIO_PORT", "9000"),
    "access_key": os.getenv("MINIO_USER", "rag_flow"),
    "secret_key": os.getenv("MINIO_PASSWORD", "infini_rag_flow"),
    "secure": False
}

def get_used_buckets_from_db():
    """데이터베이스에서 사용 중인 스토리지 버킷(kb_id) 목록 조회"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 모든 중복되지 않는 kb_id 조회
        cursor.execute("SELECT DISTINCT kb_id FROM document")
        kb_ids = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return kb_ids
        
    except Exception as e:
        print(f"데이터베이스 조회 실패: {str(e)}")
        return []

def cleanup_unused_buckets():
    """사용되지 않는 MinIO 스토리지 버킷 정리"""
    try:
        # MinIO 클라이언트 획득
        minio_client = Minio(
            endpoint=MINIO_CONFIG["endpoint"],
            access_key=MINIO_CONFIG["access_key"],
            secret_key=MINIO_CONFIG["secret_key"],
            secure=MINIO_CONFIG["secure"]
        )
        
        # 데이터베이스에서 유효한 kb_id 목록 획득
        used_buckets = set(get_used_buckets_from_db())
        
        # MinIO의 모든 스토리지 버킷 획득
        all_buckets = minio_client.list_buckets()
        minio_bucket_names = {bucket.name for bucket in all_buckets}
        
        # 삭제해야 할 스토리지 버킷 계산
        buckets_to_delete = minio_bucket_names - used_buckets
        
        if not buckets_to_delete:
            print("삭제해야 할 여분의 스토리지 버킷이 없습니다")
            return
        
        print(f"{len(buckets_to_delete)}개의 여분 스토리지 버킷을 정리해야 합니다:")
        
        # 여분의 스토리지 버킷 삭제
        for bucket_name in buckets_to_delete:
            try:
                # 먼저 스토리지 버킷이 비어있는지 확인
                objects = minio_client.list_objects(bucket_name)
                for obj in objects:
                    minio_client.remove_object(bucket_name, obj.object_name)
                
                # 스토리지 버킷 삭제
                minio_client.remove_bucket(bucket_name)
                print(f"스토리지 버킷 삭제 완료: {bucket_name}")
                
            except Exception as e:
                print(f"스토리지 버킷 {bucket_name} 삭제 실패: {str(e)}")
                
    except Exception as e:
        print(f"스토리지 버킷 정리 과정에서 오류 발생: {str(e)}")

if __name__ == "__main__":
    cleanup_unused_buckets()