import os
import mysql.connector
from tabulate import tabulate
from dotenv import load_dotenv
from minio import Minio
from io import BytesIO

# 환경 변수 로드
load_dotenv("../../docker/.env")

# 데이터베이스 연결 설정
DB_CONFIG = {
    "host": "localhost",  # Docker 외부에서 실행하는 경우 localhost 사용
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

def get_all_documents():
    """모든 문서 정보 및 MinIO 내 저장 위치 조회"""
    try:
        # MySQL 데이터베이스에 연결
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 먼저 document 테이블의 컬럼 정보 획득
        cursor.execute("SHOW COLUMNS FROM document")
        columns = [column['Field'] for column in cursor.fetchall()]
        
        # 존재하는 컬럼만 선택하는 동적 쿼리문 구성
        select_fields = []
        for field in ['id', 'name', 'kb_id', 'location', 'size', 'type', 'created_by', 'create_time']:
            if field in columns:
                select_fields.append(f'd.{field}')
        
        # 선택적 필드 추가
        optional_fields = ['token_count', 'chunk_count']
        for field in optional_fields:
            if field in columns:
                select_fields.append(f'd.{field}')
        
        # 쿼리 구성 및 실행
        query = f"""
            SELECT {', '.join(select_fields)}
            FROM document d
            ORDER BY d.create_time DESC
        """
        cursor.execute(query)
        
        documents = cursor.fetchall()
        
        # 문서와 파일의 연관 정보 획득
        cursor.execute("""
            SELECT f2d.document_id, f.id as file_id, f.parent_id, f.source_type
            FROM file2document f2d
            JOIN file f ON f2d.file_id = f.id
        """)
        
        file_mappings = {}
        for row in cursor.fetchall():
            file_mappings[row['document_id']] = {
                'file_id': row['file_id'],
                'parent_id': row['parent_id'],
                'source_type': row['source_type']
            }
        
        # 정보 통합
        result = []
        for doc in documents:
            doc_id = doc['id']
            kb_id = doc['kb_id']
            location = doc['location']
            
            # 저장 위치 결정
            storage_bucket = kb_id
            storage_location = location
            
            # 파일 매핑이 있으면 파일의 parent_id를 bucket으로 사용해야 하는지 확인
            if doc_id in file_mappings:
                file_info = file_mappings[doc_id]
                # File2DocumentService.get_storage_address의 로직 시뮬레이션
                if file_info.get('source_type') is None or file_info.get('source_type') == 0:  # LOCAL
                    storage_bucket = file_info['parent_id']
            
            # MinIO 저장 경로 구성
            minio_path = f"{storage_bucket}/{storage_location}"
            
            # 존재하는 필드만 포함하는 결과 딕셔너리 구성
            result_item = {
                'id': doc_id,
                'name': doc.get('name', ''),
                'kb_id': kb_id,
                'size': doc.get('size', 0),
                'type': doc.get('type', ''),
                'minio_path': minio_path,
                'storage_bucket': storage_bucket,
                'storage_location': storage_location
            }
            
            # 선택적 필드 추가
            if 'token_count' in doc:
                result_item['token_count'] = doc['token_count']
            if 'chunk_count' in doc:
                result_item['chunk_count'] = doc['chunk_count']
                
            result.append(result_item)
        
        cursor.close()
        conn.close()
        
        return result
    
    except Exception as e:
        print(f"Error: {e}")
        return []

def download_document_from_minio(bucket, object_name, output_path):
    """MinIO에서 문서 다운로드"""
    try:
        # MinIO 클라이언트 생성
        minio_client = Minio(
            endpoint=MINIO_CONFIG["endpoint"],
            access_key=MINIO_CONFIG["access_key"],
            secret_key=MINIO_CONFIG["secret_key"],
            secure=MINIO_CONFIG["secure"]
        )
        
        # bucket이 존재하는지 확인
        if not minio_client.bucket_exists(bucket):
            print(f"오류: Bucket '{bucket}'이 존재하지 않습니다")
            return False
        
        # 파일 다운로드
        print(f"MinIO에서 다운로드 중: {bucket}/{object_name} → {output_path}")
        minio_client.fget_object(bucket, object_name, output_path)
        print(f"파일이 성공적으로 다운로드됨: {output_path}")
        return True
    
    except Exception as e:
        print(f"파일 다운로드 중 오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    documents = get_all_documents()
    
    if not documents:
        print("문서 정보를 찾을 수 없습니다")
        return
    
    # tabulate를 사용하여 테이블 출력
    # 동적으로 테이블 헤더 결정
    sample_doc = documents[0]
    headers = ['ID', '문서명', '데이터셋ID', '크기(바이트)', '타입', 'MinIO경로']
    if 'token_count' in sample_doc:
        headers.insert(-1, '토큰수')
    if 'chunk_count' in sample_doc:
        headers.insert(-1, '청크수')
    
    # 테이블 데이터 구성
    table_data = []
    for doc in documents:
        row = [
            doc['id'], 
            doc['name'], 
            doc['kb_id'], 
            doc['size'], 
            doc['type']
        ]
        
        if 'token_count' in doc:
            row.append(doc['token_count'])
        if 'chunk_count' in doc:
            row.append(doc['chunk_count'])
            
        row.append(doc['minio_path'])
        table_data.append(row)
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"총 {len(documents)}개 문서")
    
    # 첫 번째 문서 다운로드
    if documents:
        first_doc = documents[0]
        doc_name = first_doc['name']
        bucket = first_doc['storage_bucket']
        object_name = first_doc['storage_location']
        
        # 다운로드 디렉토리 생성
        download_dir = "downloads"
        os.makedirs(download_dir, exist_ok=True)
        
        # 출력 파일 경로 구성
        output_path = os.path.join(download_dir, doc_name)
        
        # 파일 다운로드
        # success = download_document_from_minio(bucket, object_name, output_path)
        # if success:
        #     print(f"\n첫 번째 문서를 성공적으로 다운로드했습니다: {doc_name}")
        #     print(f"파일 저장 위치: {os.path.abspath(output_path)}")
        # else:
        #     print("\n첫 번째 문서 다운로드에 실패했습니다")

if __name__ == "__main__":
    main()