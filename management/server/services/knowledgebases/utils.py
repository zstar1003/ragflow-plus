from datetime import datetime

from database import get_db_connection
from utils import generate_uuid

from . import logger


def _update_document_progress(doc_id, progress=None, message=None, status=None, run=None, chunk_count=None, process_duration=None):
    """更新数据库中文档的进度和状态"""
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
        logger.error(f"[Parser-ERROR] 更新文档 {doc_id} 进度失败: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def _update_kb_chunk_count(kb_id, count_delta):
    """更新知识库的块数量"""
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
        logger.error(f"[Parser-ERROR] 更新知识库 {kb_id} 块数量失败: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def _create_task_record(doc_id, chunk_ids_list):
    """创建task记录，兼容无 priority 字段的新表结构"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查 task 表中是否有 priority 字段
        cursor.execute("SHOW COLUMNS FROM task LIKE 'priority'")
        has_priority = cursor.fetchone() is not None

        task_id = generate_uuid()
        current_datetime = datetime.now()
        current_timestamp = int(current_datetime.timestamp() * 1000)
        current_date_only = current_datetime.strftime("%Y-%m-%d")
        digest = f"{doc_id}_{0}_{1}"  # 假设 from_page=0, to_page=1
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
        logger.info(f"[Parser-INFO] Task记录创建成功，Task ID: {task_id}")

    except Exception as e:
        logger.error(f"[Parser-ERROR] 创建Task记录失败: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_bbox_from_block(block):
    """
    从 preproc_blocks 中的一个块提取最外层的 bbox 信息。

    Args:
        block (dict): 代表一个块的字典，期望包含 'bbox' 键。

    Returns:
        list: 包含4个数字的 bbox 列表，如果找不到或格式无效则返回 [0, 0, 0, 0]。
    """
    if isinstance(block, dict) and "bbox" in block:
        bbox = block.get("bbox")
        # 验证 bbox 是否为包含4个数字的有效列表
        if isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(n, (int, float)) for n in bbox):
            return bbox
        else:
            logger.warning(f"[Parser-WARNING] 块的 bbox 格式无效: {bbox}，将使用默认值。")  # noqa: F821
    # 如果 block 不是字典或没有 bbox 键，或 bbox 格式无效，返回默认值
    return [0, 0, 0, 0]
