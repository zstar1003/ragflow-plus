from datetime import datetime

from database import get_db_connection
from utils import generate_uuid

from . import logger


def _update_document_progress(doc_id, progress=None, message=None, status=None, run=None, chunk_count=None, process_duration=None):
    """DB 내 문서의 진행도와 상태를 갱신"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        updates = []
        params = []

        if progress is not None:
            updates.append("progress = %s")
            params.append(float(progress))
        if message is not None:
            updates.append("progress_msg = %s")
            params.append(message)
        if status is not None:
            updates.append("status = %s")
            params.append(status)
        if run is not None:
            updates.append("run = %s")
            params.append(run)
        if chunk_count is not None:
            updates.append("chunk_num = %s")
            params.append(chunk_count)
        if process_duration is not None:
            updates.append("process_duation = %s")
            params.append(process_duration)

        if not updates:
            return

        query = f"UPDATE document SET {', '.join(updates)} WHERE id = %s"
        params.append(doc_id)
        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        logger.error(f"[Parser-ERROR] 문서 {doc_id} 진행도 갱신 실패: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def _update_kb_chunk_count(kb_id, count_delta):
    """지식베이스의 청크 개수 갱신"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        kb_update = """
            UPDATE knowledgebase
            SET chunk_num = chunk_num + %s,
                update_date = %s
            WHERE id = %s
        """
        cursor.execute(kb_update, (count_delta, current_date, kb_id))
        conn.commit()
    except Exception as e:
        logger.error(f"[Parser-ERROR] 지식베이스 {kb_id} 청크 개수 갱신 실패: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def _create_task_record(doc_id, chunk_ids_list):
    """task 레코드 생성, priority 필드 없는 신규 테이블 구조도 호환"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # task 테이블에 priority 필드가 있는지 확인
        cursor.execute("SHOW COLUMNS FROM task LIKE 'priority'")
        has_priority = cursor.fetchone() is not None

        task_id = generate_uuid()
        current_datetime = datetime.now()
        current_timestamp = int(current_datetime.timestamp() * 1000)
        current_date_only = current_datetime.strftime("%Y-%m-%d")
        digest = f"{doc_id}_{0}_{1}"  # from_page=0, to_page=1로 가정
        chunk_ids_str = " ".join(chunk_ids_list)

        common_fields = [
            "id",
            "create_time",
            "create_date",
            "update_time",
            "update_date",
            "doc_id",
            "from_page",
            "to_page",
            "begin_at",
            "process_duation",
            "progress",
            "progress_msg",
            "retry_count",
            "digest",
            "chunk_ids",
            "task_type",
        ]
        common_values = [task_id, current_timestamp, current_date_only, current_timestamp, current_date_only, doc_id, 0, 1, None, 0.0, 1.0, "MinerU解析完成", 1, digest, chunk_ids_str, ""]

        if has_priority:
            common_fields.append("priority")
            common_values.append(0)

        fields_sql = ", ".join(common_fields)
        placeholders = ", ".join(["%s"] * len(common_values))

        task_insert = f"INSERT INTO task ({fields_sql}) VALUES ({placeholders})"
        cursor.execute(task_insert, common_values)
        conn.commit()
        logger.info(f"[Parser-INFO] Task 레코드 생성 성공, Task ID: {task_id}")

    except Exception as e:
        logger.error(f"[Parser-ERROR] Task 레코드 생성 실패: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_bbox_from_block(block):
    """
    preproc_blocks의 한 블록에서 최상위 bbox 정보를 추출합니다.

    Args:
        block (dict): 'bbox' 키를 포함하는 블록 딕셔너리

    Returns:
        list: 4개의 숫자로 구성된 bbox 리스트, 없거나 형식이 잘못되면 [0, 0, 0, 0] 반환
    """
    if isinstance(block, dict) and "bbox" in block:
        bbox = block.get("bbox")
        # bbox가 4개의 숫자로 구성된 유효한 리스트인지 확인
        if isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(n, (int, float)) for n in bbox):
            return bbox
        else:
            logger.warning(f"[Parser-WARNING] 블록의 bbox 형식이 잘못됨: {bbox}, 기본값 사용")  # noqa: F821
    # block이 딕셔너리가 아니거나 bbox 키가 없거나 형식이 잘못된 경우 기본값 반환
    return [0, 0, 0, 0]
