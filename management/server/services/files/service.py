import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from database import get_db_connection, get_minio_client, get_redis_connection
from dotenv import load_dotenv

from .utils import FileSource, FileType, get_uuid

 # 환경 변수 로드
load_dotenv("../../docker/.env")

 # redis 설정 파라미터
UPLOAD_TEMP_DIR = os.getenv("UPLOAD_TEMP_DIR", tempfile.gettempdir())
CHUNK_EXPIRY_SECONDS = 3600 * 24  # 청크 24시간 만료

temp_dir = tempfile.gettempdir()
UPLOAD_FOLDER = os.path.join(temp_dir, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "jpg", "jpeg", "png", "bmp", "txt", "md", "html", "csv"}


def allowed_file(filename):
    """Check if the file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def filename_type(filename):
    """파일명으로 파일 타입 결정"""
    ext = os.path.splitext(filename)[1].lower()

    if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
        return FileType.VISUAL.value
    elif ext in [".pdf"]:
        return FileType.PDF.value
    elif ext in [".doc", ".docx"]:
        return FileType.WORD.value
    elif ext in [".xls", ".xlsx", ".csv"]:
        return FileType.EXCEL.value
    elif ext in [".ppt", ".pptx"]:
        return FileType.PPT.value
    elif ext in [".txt", ".md"]:
        return FileType.TEXT.value
    elif ext in [".html"]:
        return FileType.HTML.value

    return FileType.OTHER.value


def get_files_list(current_page, page_size, name_filter="", sort_by="create_time", sort_order="desc"):
    """
    파일 목록 조회

    Args:
        current_page: 현재 페이지 번호
        page_size: 페이지 크기
        parent_id: 상위 폴더 ID
        name_filter: 파일명 필터 조건

    Returns:
        tuple: (파일 목록, 전체 개수)
    """
    try:
        # 오프셋 계산
        offset = (current_page - 1) * page_size

        # DB 연결
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 쿼리 조건 생성
        where_clause = "WHERE f.type != 'folder'"  # 폴더 타입 제외
        params = []

        if name_filter:
            where_clause += " AND f.name LIKE %s"
            params.append(f"%{name_filter}%")

        # 정렬 필드 검증
        valid_sort_fields = ["name", "size", "type", "create_time", "create_date"]
        if sort_by not in valid_sort_fields:
            sort_by = "create_time"

        # 정렬 쿼리 생성
        sort_clause = f"ORDER BY f.{sort_by} {sort_order.upper()}"

        # 전체 개수 쿼리
        count_query = f"""
            SELECT COUNT(*) as total
            FROM file f
            {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()["total"]

        # 파일 목록 쿼리
        query = f"""
            SELECT f.id, f.name, f.parent_id, f.type, f.size, f.location, f.source_type, f.create_time, f.create_date
            FROM file f
            {where_clause}
            {sort_clause}
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, params + [page_size, offset])
        files = cursor.fetchall()

        # create_date 포맷팅
        for file_item in files:
            if isinstance(file_item.get("create_date"), datetime):
                file_item["create_date"] = file_item["create_date"].strftime("%Y-%m-%d %H:%M:%S")

        cursor.close()
        conn.close()

        return files, total
    except Exception as e:
        raise e


def get_file_info(file_id):
    """
    파일 정보 조회

    Args:
        file_id: 파일 ID

    Returns:
        dict: 파일 정보
    """
    try:
        # DB 연결
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 파일 정보 쿼리
        cursor.execute(
            """
            SELECT id, name, parent_id, type, size, location, source_type
            FROM file
            WHERE id = %s
        """,
            (file_id,),
        )

        file = cursor.fetchone()
        cursor.close()
        conn.close()

        return file
    except Exception as e:
        raise e


def download_file_from_minio(file_id):
    """
    MinIO에서 파일 다운로드

    Args:
        file_id: 파일 ID

    Returns:
        tuple: (파일 데이터, 파일명)
    """
    try:
        # 파일 정보 가져오기
        file = get_file_info(file_id)

        if not file:
            raise Exception(f"파일 {file_id} 이(가) 존재하지 않음")

        # MinIO에서 파일 다운로드
        minio_client = get_minio_client()

        # parent_id를 버킷으로 사용
        storage_bucket = file["parent_id"]
        storage_location = file["location"]

        # 버킷 존재 여부 확인
        if not minio_client.bucket_exists(storage_bucket):
            raise Exception(f"버킷 {storage_bucket} 이(가) 존재하지 않음")

        # 파일 다운로드
        response = minio_client.get_object(storage_bucket, storage_location)
        file_data = response.read()

        return file_data, file["name"]

    except Exception as e:
        raise e


def delete_file(file_id):
    """
    파일 삭제

    Args:
        file_id: 파일 ID

    Returns:
        bool: 삭제 성공 여부
    """
    try:
    # DB 연결
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 파일 정보 쿼리
        cursor.execute(
            """
            SELECT id, parent_id, name, location, type
            FROM file
            WHERE id = %s
        """,
            (file_id,),
        )

        file = cursor.fetchone()
        if not file:
            cursor.close()
            conn.close()
            return False

        # 폴더면 바로 성공 반환(폴더는 처리하지 않음)
        if file["type"] == FileType.FOLDER.value:
            cursor.close()
            conn.close()
            return True

        # 연관 document 레코드 쿼리
        cursor.execute(
            """
            SELECT f2d.document_id, d.kb_id, d.location
            FROM file2document f2d
            JOIN document d ON f2d.document_id = d.id
            WHERE f2d.file_id = %s
        """,
            (file_id,),
        )

        document_mappings = cursor.fetchall()

        # MinIO 클라이언트 생성
        minio_client = get_minio_client()

        # 트랜잭션 시작
        try:
            # 주의: conn.start_transaction() 대신 execute로 트랜잭션 명령 실행
            cursor.execute("START TRANSACTION")

            # 1. file 테이블 레코드 먼저 삭제
            cursor.execute("DELETE FROM file WHERE id = %s", (file_id,))

            # 2. 연관 file2document 레코드 삭제
            cursor.execute("DELETE FROM file2document WHERE file_id = %s", (file_id,))

            # 3. 연관 document 레코드 삭제
            for doc_mapping in document_mappings:
                cursor.execute("DELETE FROM document WHERE id = %s", (doc_mapping["document_id"],))

            # 트랜잭션 커밋
            cursor.execute("COMMIT")

            # MinIO에서 파일 삭제(트랜잭션 커밋 후)
            try:
                # 버킷 존재 여부 확인, 없으면 MinIO 삭제 생략
                parent_id = file.get("parent_id")
                if parent_id and minio_client.bucket_exists(parent_id):
                    try:
                        # 파일 삭제, 파일 없음 오류 무시
                        minio_client.remove_object(parent_id, file["location"])
                        print(f"MinIO에서 파일 삭제 성공: {parent_id}/{file['location']}")
                    except Exception as e:
                        print(f"MinIO에서 파일 삭제 실패: {parent_id}/{file['location']} - {str(e)}")
                else:
                    print(f"버킷이 존재하지 않아 MinIO 삭제 생략: {parent_id}")

                # 연관 document가 있으면 document 저장 파일도 삭제
                for doc_mapping in document_mappings:
                    kb_id = doc_mapping.get("kb_id")
                    doc_location = doc_mapping.get("location")
                    if kb_id and doc_location and minio_client.bucket_exists(kb_id):
                        try:
                            minio_client.remove_object(kb_id, doc_location)
                            print(f"MinIO에서 document 파일 삭제 성공: {kb_id}/{doc_location}")
                        except Exception as e:
                            print(f"MinIO에서 document 파일 삭제 실패: {kb_id}/{doc_location} - {str(e)}")
                    else:
                        print(f"document 버킷이 없거나 위치가 비어있어 MinIO 삭제 생략: {kb_id}/{doc_location}")
            except Exception as e:
                # MinIO 삭제 실패여도 DB 삭제에는 영향 없음
                print(f"MinIO 작업 실패, DB 삭제에는 영향 없음: {str(e)}")

            return True

        except Exception as e:
            # 트랜잭션 롤백
            try:
                cursor.execute("ROLLBACK")
            except:  # noqa: E722
                pass
            raise e

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"파일 삭제 중 오류 발생: {str(e)}")
        raise e


def batch_delete_files(file_ids):
    """
    파일 일괄 삭제

    Args:
        file_ids: 파일 ID 리스트

    Returns:
        int: 성공적으로 삭제된 파일 개수
    """
    if not file_ids:
        return 0

    try:
        # DB 연결
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # MinIO 클라이언트 생성
        minio_client = get_minio_client()

        # 트랜잭션 시작
        try:
            cursor.execute("START TRANSACTION")

            success_count = 0

            for file_id in file_ids:
                # 파일 정보 쿼리
                cursor.execute(
                    """
                    SELECT id, parent_id, name, location, type
                    FROM file
                    WHERE id = %s
                """,
                    (file_id,),
                )

                file = cursor.fetchone()
                if not file:
                    continue

                # 폴더면 건너뜀
                if file["type"] == FileType.FOLDER.value:
                    continue

                # 연관 document 레코드 쿼리
                cursor.execute(
                    """
                    SELECT f2d.id as f2d_id, f2d.document_id, d.kb_id, d.location
                    FROM file2document f2d
                    JOIN document d ON f2d.document_id = d.id
                    WHERE f2d.file_id = %s
                """,
                    (file_id,),
                )

                document_mappings = cursor.fetchall()

                # 1. file 테이블 레코드 먼저 삭제
                cursor.execute("DELETE FROM file WHERE id = %s", (file_id,))

                # 2. 연관 file2document 레코드 삭제
                cursor.execute("DELETE FROM file2document WHERE file_id = %s", (file_id,))

                # 3. 연관 document 레코드 삭제
                for doc_mapping in document_mappings:
                    cursor.execute("DELETE FROM document WHERE id = %s", (doc_mapping["document_id"],))

                success_count += 1

            # 트랜잭션 커밋
            cursor.execute("COMMIT")

            # MinIO에서 파일 삭제(트랜잭션 커밋 후)
            for file_id in file_ids:
                try:
                    # 파일 정보 쿼리
                    cursor.execute(
                        """
                        SELECT id, parent_id, name, location, type
                        FROM file
                        WHERE id = %s
                    """,
                        (file_id,),
                    )

                    file = cursor.fetchone()
                    if not file and file["type"] != FileType.FOLDER.value:
                        # 检查bucket是否存在
                        if minio_client.bucket_exists(file["parent_id"]):
                            # 删除文件
                            minio_client.remove_object(file["parent_id"], file["location"])

                        # 연관 document가 있으면 document 저장 파일도 삭제
                        cursor.execute(
                            """
                            SELECT f2d.id as f2d_id, f2d.document_id, d.kb_id, d.location
                            FROM file2document f2d
                            JOIN document d ON f2d.document_id = d.id
                            WHERE f2d.file_id = %s
                        """,
                            (file_id,),
                        )

                        document_mappings = cursor.fetchall()
                        for doc_mapping in document_mappings:
                            if minio_client.bucket_exists(doc_mapping["kb_id"]):
                                minio_client.remove_object(doc_mapping["kb_id"], doc_mapping["location"])
                except Exception as e:
                    # MinIO 삭제 실패여도 DB 삭제에는 영향 없음
                    print(f"MinIO에서 파일 삭제 실패: {str(e)}")

            return success_count

        except Exception as e:
            # 트랜잭션 롤백
            try:
                cursor.execute("ROLLBACK")
            except:  # noqa: E722
                pass
            raise e

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"파일 일괄 삭제 중 오류 발생: {str(e)}")
        raise e


def upload_files_to_server(files, parent_id=None, user_id=None):
    """파일을 서버에 업로드하는 핵심 로직 처리"""
    if user_id is None:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # 생성 시간이 가장 빠른 사용자 ID 조회
            query_earliest_user = """
            SELECT id FROM user 
            WHERE create_time = (SELECT MIN(create_time) FROM user)
            LIMIT 1
            """
            cursor.execute(query_earliest_user)
            earliest_user = cursor.fetchone()

            if earliest_user:
                user_id = earliest_user["id"]
                print(f"가장 빠른 생성 시간의 사용자 ID 사용: {user_id}")
            else:
                user_id = "system"
                print("사용자를 찾지 못해 기본 사용자 ID(system) 사용")

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"가장 빠른 사용자 ID 조회 실패: {str(e)}")
            user_id = "system"

    # parent_id가 지정되지 않으면 file 테이블의 첫 번째 레코드를 parent_id로 사용
    if parent_id is None:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # file 테이블의 첫 번째 레코드 조회
            query_first_file = """
            SELECT id FROM file 
            LIMIT 1
            """
            cursor.execute(query_first_file)
            first_file = cursor.fetchone()

            if first_file:
                parent_id = first_file["id"]
                print(f"file 테이블의 첫 번째 레코드 ID를 parent_id로 사용: {parent_id}")
            else:
                # 레코드가 없으면 새 ID 생성
                parent_id = get_uuid()
                print(f"file 테이블에 레코드가 없어 새 parent_id 생성: {parent_id}")

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"file 테이블 첫 번째 레코드 조회 실패: {str(e)}")
            parent_id = get_uuid()  # 가져올 수 없으면 새 ID 생성
            print(f"새 parent_id 생성: {parent_id}")

    results = []

    for file in files:
        if file.filename == "":
            continue

        if file and allowed_file(file.filename):
            original_filename = file.filename
            # 파일명 처리 로직 수정, 한글 등 유니코드 문자 보존
            name, ext = os.path.splitext(original_filename)

            # 파일 시스템에 안전하지 않은 문자만 치환, 한글 등 유니코드 문자 보존
            safe_name = re.sub(r'[\\/:*?"<>|]', "_", name)

            # 처리 후 파일명이 비어있으면 랜덤 문자열 사용
            if not safe_name or safe_name.strip() == "":
                safe_name = f"file_{get_uuid()[:8]}"

            filename = safe_name + ext.lower()
            filepath = os.path.join(UPLOAD_FOLDER, filename)

            try:
                # 1. 파일을 로컬 임시 디렉토리에 저장
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file.save(filepath)
                print(f"파일이 임시 디렉토리에 저장됨: {filepath}")

                # 2. 파일 타입 확인
                filetype = filename_type(filename)
                if filetype == FileType.OTHER.value:
                    raise RuntimeError("지원하지 않는 파일 타입")

                # 3. 고유 저장 위치 생성
                minio_client = get_minio_client()
                location = filename

                # 버킷 존재 확인
                if not minio_client.bucket_exists(parent_id):
                    minio_client.make_bucket(parent_id)
                    print(f"MinIO 버킷 생성: {parent_id}")

                # 4. MinIO에 업로드
                with open(filepath, "rb") as file_data:
                    minio_client.put_object(bucket_name=parent_id, object_name=location, data=file_data, length=os.path.getsize(filepath))
                print(f"파일이 MinIO에 업로드됨: {parent_id}/{location}")

                # 5. 파일 레코드 생성
                file_id = get_uuid()
                current_time = int(datetime.now().timestamp())
                current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                file_record = {
                    "id": file_id,
                    "parent_id": parent_id,
                    "tenant_id": user_id,
                    "created_by": user_id,
                    "name": filename,
                    "type": filetype,
                    "size": os.path.getsize(filepath),
                    "location": location,
                    "source_type": FileSource.LOCAL.value,
                    "create_time": current_time,
                    "create_date": current_date,
                    "update_time": current_time,
                    "update_date": current_date,
                }

                # 保存文件记录
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()

                    # 파일 레코드 삽입
                    columns = ", ".join(file_record.keys())
                    placeholders = ", ".join(["%s"] * len(file_record))
                    query = f"INSERT INTO file ({columns}) VALUES ({placeholders})"
                    cursor.execute(query, list(file_record.values()))

                    conn.commit()

                    results.append({"id": file_id, "name": filename, "size": file_record["size"], "type": filetype, "status": "success"})

                except Exception as e:
                    conn.rollback()
                    print(f"DB 작업 실패: {str(e)}")
                    raise
                finally:
                    cursor.close()
                    conn.close()

            except Exception as e:
                results.append({"name": filename, "error": str(e), "status": "failed"})
                print(f"파일 업로드 중 오류 발생: {filename}, 오류: {str(e)}")
            finally:
                # 임시 파일 삭제
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            raise RuntimeError({"name": filename, "error": "지원하지 않는 파일 타입", "status": "failed"})

    return {"code": 0, "data": results, "message": f"{len([r for r in results if r['status'] == 'success'])}/{len(files)}개 파일 업로드 성공"}


def handle_chunk_upload(chunk_file, chunk_index, total_chunks, upload_id, file_name, parent_id=None):
    """
    파일 청크 업로드 처리

    Args:
        chunk_file: 업로드된 파일 청크
        chunk_index: 청크 인덱스
        total_chunks: 전체 청크 수
        upload_id: 업로드 ID
        file_name: 파일명
        parent_id: 상위 디렉토리 ID

    Returns:
        dict: 업로드 결과
    """
    try:
        # 청크 저장용 임시 디렉토리 생성
        upload_dir = Path(UPLOAD_TEMP_DIR) / "chunks" / upload_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 청크 저장
        chunk_path = upload_dir / f"{chunk_index}.chunk"
        chunk_file.save(str(chunk_path))

        # Redis로 업로드 상태 기록
        r = get_redis_connection()

        # 파일 정보 기록
        if int(chunk_index) == 0:
            r.hmset(f"upload:{upload_id}:info", {"file_name": file_name, "total_chunks": total_chunks, "parent_id": parent_id or "", "status": "uploading"})
            r.expire(f"upload:{upload_id}:info", CHUNK_EXPIRY_SECONDS)

        # 청크 상태 기록
        r.setbit(f"upload:{upload_id}:chunks", int(chunk_index), 1)
        r.expire(f"upload:{upload_id}:chunks", CHUNK_EXPIRY_SECONDS)

        # 모든 청크가 업로드되었는지 확인
        is_complete = True
        for i in range(int(total_chunks)):
            if not r.getbit(f"upload:{upload_id}:chunks", i):
                is_complete = False
                break

        return {"code": 0, "data": {"upload_id": upload_id, "chunk_index": chunk_index, "is_complete": is_complete}, "message": "청크 업로드 성공"}
    except Exception as e:
        print(f"청크 업로드 실패: {str(e)}")
        return {"code": 500, "message": f"청크 업로드 실패: {str(e)}"}


def merge_chunks(upload_id, file_name, total_chunks, parent_id=None):
    """
    파일 청크 병합

    Args:
        upload_id: 업로드 ID
        file_name: 파일명
        total_chunks: 전체 청크 수
        parent_id: 상위 디렉토리 ID

    Returns:
        dict: 병합 결과
    """
    try:
        r = get_redis_connection()

        # 업로드 상태 확인
        if not r.exists(f"upload:{upload_id}:info"):
            return {"code": 404, "message": "업로드 작업이 존재하지 않거나 만료됨"}

        # 모든 청크가 업로드되었는지 확인
        for i in range(int(total_chunks)):
            if not r.getbit(f"upload:{upload_id}:chunks", i):
                return {"code": 400, "message": f"청크 {i}가 업로드되지 않아 병합 불가"}

        # 업로드 정보 가져오기
        upload_info = r.hgetall(f"upload:{upload_id}:info")
        if not upload_info:
            return {"code": 404, "message": "업로드 정보가 존재하지 않음"}

        # 바이트 문자열을 일반 문자열로 변환
        upload_info = {k.decode("utf-8"): v.decode("utf-8") for k, v in upload_info.items()}

        # 저장된 정보 사용, 파라미터에 없으면
        file_name = file_name or upload_info.get("file_name")

        # 병합용 임시 파일 생성
        upload_dir = Path(UPLOAD_TEMP_DIR) / "chunks" / upload_id
        merged_path = Path(UPLOAD_TEMP_DIR) / f"merged_{upload_id}_{file_name}"

        # 파일 병합
        with open(merged_path, "wb") as merged_file:
            for i in range(int(total_chunks)):
                chunk_path = upload_dir / f"{i}.chunk"
                with open(chunk_path, "rb") as chunk_file:
                    merged_file.write(chunk_file.read())

        # 업로드 함수로 병합된 파일 처리
        with open(merged_path, "rb") as file_obj:
            # FileStorage 객체 생성
            class MockFileStorage:
                def __init__(self, file_obj, filename):
                    self.file = file_obj
                    self.filename = filename

                def save(self, dst):
                    with open(dst, "wb") as f:
                        f.write(self.file.read())
                        self.file.seek(0)  # 파일 포인터 리셋

            mock_file = MockFileStorage(file_obj, file_name)
            result = upload_files_to_server([mock_file])

        # 상태를 완료로 업데이트
        r.hset(f"upload:{upload_id}:info", "status", "completed")

        # 임시 파일 정리
        try:
            if os.path.exists(merged_path):
                os.remove(merged_path)
            if upload_dir.exists():
                shutil.rmtree(upload_dir)
        except Exception as e:
            print(f"임시 파일 정리 실패: {str(e)}")

        return result
    except Exception as e:
        print(f"청크 병합 실패: {str(e)}")
        return {"code": 500, "message": f"청크 병합 실패: {str(e)}"}
