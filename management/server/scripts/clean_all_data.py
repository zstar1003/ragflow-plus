import os
from dotenv import load_dotenv
import mysql.connector
from minio import Minio

# 환경 변수 로드
load_dotenv("../../docker/.env")

# 데이터베이스 연결 설정
DB_CONFIG = {"host": "localhost", "port": int(os.getenv("MYSQL_PORT", "5455")), "user": "root", "password": os.getenv("MYSQL_PASSWORD", "infini_rag_flow"), "database": "rag_flow"}

# MinIO 연결 설정
MINIO_CONFIG = {
    "endpoint": "localhost:" + os.getenv("MINIO_PORT", "9000"),
    "access_key": os.getenv("MINIO_USER", "rag_flow"),
    "secret_key": os.getenv("MINIO_PASSWORD", "infini_rag_flow"),
    "secure": False,
}


def get_minio_client():
    """MinIO 클라이언트 생성"""
    return Minio(endpoint=MINIO_CONFIG["endpoint"], access_key=MINIO_CONFIG["access_key"], secret_key=MINIO_CONFIG["secret_key"], secure=MINIO_CONFIG["secure"])


def clear_database_tables():
    """데이터베이스 테이블 정리"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 외래 키 검사 비활성화
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

        # 테이블 데이터 정리
        tables = ["document", "file2document", "file"]
        for table in tables:
            cursor.execute(f"TRUNCATE TABLE {table}")
            print(f"테이블 정리 완료: {table}")

        # 외래 키 검사 활성화
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        conn.commit()
        cursor.close()
        conn.close()

        print("데이터베이스 테이블이 모두 정리되었습니다")

    except Exception as e:
        print(f"데이터베이스 테이블 정리 실패: {str(e)}")
        raise


def clear_minio_buckets():
    """MinIO의 모든 스토리지 버킷을 정리하고 삭제"""
    try:
        minio_client = get_minio_client()
        buckets = minio_client.list_buckets()

        if not buckets:
            print("MinIO에 정리할 스토리지 버킷이 없습니다")
            return

        print(f"{len(buckets)}개의 MinIO 스토리지 버킷 정리 시작...")

        for bucket in buckets:
            bucket_name = bucket.name

            # 시스템 예약 스토리지 버킷 건너뛰기
            if bucket_name.startswith("."):
                print(f"시스템 스토리지 버킷 건너뛰기: {bucket_name}")
                continue

            try:
                # 재귀적으로 스토리지 버킷의 모든 객체 삭제(버전 제어 객체 포함)
                objects = minio_client.list_objects(bucket_name, recursive=True)
                for obj in objects:
                    try:
                        # 강제로 객체 삭제(모든 버전 포함)
                        minio_client.remove_object(bucket_name, obj.object_name, version_id=obj.version_id)
                    except Exception as e:
                        print(f"객체 {obj.object_name} 삭제 실패: {str(e)}")
                        continue

                # 모든 객체가 삭제되었는지 확인
                while True:
                    remaining_objects = list(minio_client.list_objects(bucket_name))
                    if not remaining_objects:
                        break
                    for obj in remaining_objects:
                        minio_client.remove_object(bucket_name, obj.object_name)

                # 실제로 스토리지 버킷 삭제
                try:
                    minio_client.remove_bucket(bucket_name)
                    print(f"스토리지 버킷 삭제됨: {bucket_name}")
                except Exception as e:
                    print(f"스토리지 버킷 {bucket_name} 삭제 실패: {str(e)}. 강제 삭제 시도...")
                    # 강제로 스토리지 버킷 삭제(비어있지 않은 경우에도)
                    try:
                        # 다시 한번 모든 객체 삭제 확인
                        objects = minio_client.list_objects(bucket_name, recursive=True)
                        for obj in objects:
                            minio_client.remove_object(bucket_name, obj.object_name)
                        minio_client.remove_bucket(bucket_name)
                        print(f"강제로 스토리지 버킷 삭제됨: {bucket_name}")
                    except Exception as e:
                        print(f"강제 삭제 스토리지 버킷 {bucket_name} 여전히 실패: {str(e)}")

            except Exception as e:
                print(f"스토리지 버킷 {bucket_name} 처리 중 오류 발생: {str(e)}")

        print("MinIO 스토리지 버킷 정리 완료")

    except Exception as e:
        print(f"MinIO 스토리지 버킷 정리 실패: {str(e)}")
        raise


def confirm_action():
    """작업 확인"""
    print("경고: 이 작업은 모든 데이터를 영구적으로 삭제합니다!")
    confirmation = input("모든 데이터를 정말로 삭제하시겠습니까? ('y' 입력으로 확인): ")
    return confirmation.lower() == "y"


if __name__ == "__main__":
    if confirm_action():
        print("데이터 정리 시작...")
        clear_database_tables()
        clear_minio_buckets()
        print("데이터 정리 완료")
    else:
        print("작업이 취소되었습니다")
