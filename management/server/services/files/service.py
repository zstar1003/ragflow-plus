import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from database import get_db_connection, get_minio_client, get_redis_connection
from dotenv import load_dotenv

from ..sql_utils import normalize_sort_order
from .utils import FileSource, FileType, get_uuid

# 加载环境变量
load_dotenv("../../docker/.env")

# redis配置参数
UPLOAD_TEMP_DIR = os.getenv("UPLOAD_TEMP_DIR", tempfile.gettempdir())
CHUNK_EXPIRY_SECONDS = 3600 * 24  # 分块24小时过期
MAX_UPLOAD_CHUNKS = 10000

temp_dir = tempfile.gettempdir()
UPLOAD_FOLDER = os.path.join(temp_dir, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "jpg", "jpeg", "png", "bmp", "txt", "md", "html", "csv"}


def allowed_file(filename):
    """Check if the file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def filename_type(filename):
    """根据文件名确定文件类型"""
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


def get_files_list(current_page, page_size, name_filter="", sort_by="create_time", sort_order="desc", user_id=None):
    """
    获取文件列表

    Args:
        current_page: 当前页码
        page_size: 每页大小
        name_filter: 文件名过滤条件
        sort_by: 排序字段
        sort_order: 排序顺序
        user_id: 用户ID（如果提供，则只返回该用户上传的文件）

    Returns:
        tuple: (文件列表, 总数)
    """
    try:
        # 计算偏移量
        offset = (current_page - 1) * page_size

        # 连接数据库
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 构建查询条件
        where_clause = "WHERE f.type != 'folder'"  # 排除文件夹类型
        params = []

        if name_filter:
            where_clause += " AND f.name LIKE %s"
            params.append(f"%{name_filter}%")
        
        # 如果提供了user_id，则只返回该用户上传的文件
        if user_id:
            where_clause += " AND f.created_by = %s"
            params.append(user_id)

        # 验证排序字段
        valid_sort_fields = ["name", "size", "type", "create_time", "create_date"]
        if sort_by not in valid_sort_fields:
            sort_by = "create_time"

        # 构建排序子句
        sort_clause = f"ORDER BY f.{sort_by} {normalize_sort_order(sort_order)}"

        # 查询总数
        count_query = f"""
            SELECT COUNT(*) as total
            FROM file f
            {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()["total"]

        # 查询文件列表
        query = f"""
            SELECT f.id, f.name, f.parent_id, f.type, f.size, f.location, f.source_type, f.create_time, f.create_date
            FROM file f
            {where_clause}
            {sort_clause}
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, params + [page_size, offset])
        files = cursor.fetchall()

        # 格式化 create_date
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
    获取文件信息

    Args:
        file_id: 文件ID

    Returns:
        dict: 文件信息
    """
    try:
        # 连接数据库
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 查询文件信息
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
    从MinIO下载文件

    Args:
        file_id: 文件ID

    Returns:
        tuple: (文件数据, 文件名)
    """
    try:
        # 获取文件信息
        file = get_file_info(file_id)

        if not file:
            raise Exception(f"文件 {file_id} 不存在")

        # 从MinIO下载文件
        minio_client = get_minio_client()

        # 使用parent_id作为存储桶
        storage_bucket = file["parent_id"]
        storage_location = file["location"]

        # 检查bucket是否存在
        if not minio_client.bucket_exists(storage_bucket):
            raise Exception(f"存储桶 {storage_bucket} 不存在")

        # 下载文件
        response = minio_client.get_object(storage_bucket, storage_location)
        file_data = response.read()

        return file_data, file["name"]

    except Exception as e:
        raise e


def delete_file(file_id):
    """
    删除文件

    Args:
        file_id: 文件ID

    Returns:
        bool: 是否删除成功
    """
    try:
        # 连接数据库
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 查询文件信息
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

        # 如果是文件夹，直接返回成功（不处理文件夹）
        if file["type"] == FileType.FOLDER.value:
            cursor.close()
            conn.close()
            return True

        # 查询关联的document记录
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

        # 创建MinIO客户端
        minio_client = get_minio_client()

        # 开始事务
        try:
            # 注意：这里不再使用conn.start_transaction()，而是使用execute直接执行事务相关命令
            cursor.execute("START TRANSACTION")

            # 1. 先删除file表中的记录
            cursor.execute("DELETE FROM file WHERE id = %s", (file_id,))

            # 2. 删除关联的file2document记录
            cursor.execute("DELETE FROM file2document WHERE file_id = %s", (file_id,))

            # 3. 删除关联的document记录
            for doc_mapping in document_mappings:
                cursor.execute("DELETE FROM document WHERE id = %s", (doc_mapping["document_id"],))

            # 提交事务
            cursor.execute("COMMIT")

            # 从MinIO删除文件（在事务提交后进行）
            try:
                # 检查bucket是否存在，如果不存在则跳过MinIO删除操作
                parent_id = file.get("parent_id")
                if parent_id and minio_client.bucket_exists(parent_id):
                    try:
                        # 删除文件，忽略文件不存在的错误
                        minio_client.remove_object(parent_id, file["location"])
                        print(f"从MinIO删除文件成功: {parent_id}/{file['location']}")
                    except Exception as e:
                        print(f"从MinIO删除文件失败: {parent_id}/{file['location']} - {str(e)}")
                else:
                    print(f"存储桶不存在，跳过MinIO删除操作: {parent_id}")

                # 如果有关联的document，也删除document存储的文件
                for doc_mapping in document_mappings:
                    kb_id = doc_mapping.get("kb_id")
                    doc_location = doc_mapping.get("location")
                    if kb_id and doc_location and minio_client.bucket_exists(kb_id):
                        try:
                            minio_client.remove_object(kb_id, doc_location)
                            print(f"从MinIO删除document文件成功: {kb_id}/{doc_location}")
                        except Exception as e:
                            print(f"从MinIO删除document文件失败: {kb_id}/{doc_location} - {str(e)}")
                    else:
                        print(f"document存储桶不存在或位置为空，跳过MinIO删除操作: {kb_id}/{doc_location}")
            except Exception as e:
                # 即使MinIO删除失败，也不影响数据库操作的成功
                print(f"MinIO操作失败，但不影响数据库删除: {str(e)}")

            return True

        except Exception as e:
            # 回滚事务
            try:
                cursor.execute("ROLLBACK")
            except:  # noqa: E722
                pass
            raise e

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"删除文件时发生错误: {str(e)}")
        raise e


def batch_delete_files(file_ids):
    """
    批量删除文件

    Args:
        file_ids: 文件ID列表

    Returns:
        int: 成功删除的文件数量
    """
    if not file_ids:
        return 0

    try:
        # 连接数据库
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 创建MinIO客户端
        minio_client = get_minio_client()

        # 开始事务
        try:
            cursor.execute("START TRANSACTION")

            success_count = 0

            for file_id in file_ids:
                # 查询文件信息
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

                # 如果是文件夹，跳过
                if file["type"] == FileType.FOLDER.value:
                    continue

                # 查询关联的document记录
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

                # 1. 先删除file表中的记录
                cursor.execute("DELETE FROM file WHERE id = %s", (file_id,))

                # 2. 删除关联的file2document记录
                cursor.execute("DELETE FROM file2document WHERE file_id = %s", (file_id,))

                # 3. 删除关联的document记录
                for doc_mapping in document_mappings:
                    cursor.execute("DELETE FROM document WHERE id = %s", (doc_mapping["document_id"],))

                success_count += 1

            # 提交事务
            cursor.execute("COMMIT")

            # 从MinIO删除文件（在事务提交后进行）
            for file_id in file_ids:
                try:
                    # 查询文件信息
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

                        # 如果有关联的document，也删除document存储的文件
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
                    # 即使MinIO删除失败，也不影响数据库操作的成功
                    print(f"从MinIO删除文件失败: {str(e)}")

            return success_count

        except Exception as e:
            # 回滚事务
            try:
                cursor.execute("ROLLBACK")
            except:  # noqa: E722
                pass
            raise e

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"批量删除文件时发生错误: {str(e)}")
        raise e


def upload_files_to_server(files, parent_id=None, user_id=None):
    """处理文件上传到服务器的核心逻辑"""
    if user_id is None:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # 查询创建时间最早的用户ID
            query_earliest_user = """
            SELECT id FROM user 
            WHERE create_time = (SELECT MIN(create_time) FROM user)
            LIMIT 1
            """
            cursor.execute(query_earliest_user)
            earliest_user = cursor.fetchone()

            if earliest_user:
                user_id = earliest_user["id"]
                print(f"使用创建时间最早的用户ID: {user_id}")
            else:
                user_id = "system"
                print("未找到用户, 使用默认用户ID: system")

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"查询最早用户ID失败: {str(e)}")
            user_id = "system"

    # 如果没有指定parent_id，则获取file表中的第一个记录作为parent_id
    if parent_id is None:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # 查询file表中的第一个记录
            query_first_file = """
            SELECT id FROM file 
            LIMIT 1
            """
            cursor.execute(query_first_file)
            first_file = cursor.fetchone()

            if first_file:
                parent_id = first_file["id"]
                print(f"使用file表中的第一个记录ID作为parent_id: {parent_id}")
            else:
                # 如果没有找到记录，创建一个新的ID
                parent_id = get_uuid()
                print(f"file表中没有记录，创建新的parent_id: {parent_id}")

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"查询file表第一个记录失败: {str(e)}")
            parent_id = get_uuid()  # 如果无法获取，生成一个新的ID
            print(f"生成新的parent_id: {parent_id}")

    results = []

    for file in files:
        if file.filename == "":
            continue

        if file and allowed_file(file.filename):
            original_filename = file.filename
            # 修复文件名处理逻辑，保留中文字符
            name, ext = os.path.splitext(original_filename)

            # 只替换文件系统不安全的字符，保留中文和其他Unicode字符
            safe_name = re.sub(r'[\\/:*?"<>|]', "_", name)

            # 如果处理后文件名为空，则使用随机字符串
            if not safe_name or safe_name.strip() == "":
                safe_name = f"file_{get_uuid()[:8]}"

            filename = safe_name + ext.lower()
            filepath = None

            try:
                # 1. 保存文件到本地临时目录
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                # Different users can upload identical filenames concurrently.
                # Never stage their bytes at a shared, filename-derived path.
                with tempfile.NamedTemporaryFile(prefix="upload_", dir=UPLOAD_FOLDER, delete=False) as staged:
                    filepath = staged.name
                file.save(filepath)
                print(f"文件已保存到临时目录: {filepath}")

                # 2. 获取文件类型
                filetype = filename_type(filename)
                if filetype == FileType.OTHER.value:
                    raise RuntimeError("不支持的文件类型")

                # 3. 生成唯一存储位置
                minio_client = get_minio_client()
                location = filename

                # 确保bucket存在
                if not minio_client.bucket_exists(parent_id):
                    minio_client.make_bucket(parent_id)
                    print(f"创建MinIO存储桶: {parent_id}")

                # 4. 上传到MinIO
                with open(filepath, "rb") as file_data:
                    minio_client.put_object(bucket_name=parent_id, object_name=location, data=file_data, length=os.path.getsize(filepath))
                print(f"文件已上传到MinIO: {parent_id}/{location}")

                # 5. 创建文件记录
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

                    # 插入文件记录
                    columns = ", ".join(file_record.keys())
                    placeholders = ", ".join(["%s"] * len(file_record))
                    query = f"INSERT INTO file ({columns}) VALUES ({placeholders})"
                    cursor.execute(query, list(file_record.values()))

                    conn.commit()

                    results.append({"id": file_id, "name": filename, "size": file_record["size"], "type": filetype, "status": "success"})

                except Exception as e:
                    conn.rollback()
                    print(f"数据库操作失败: {str(e)}")
                    raise
                finally:
                    cursor.close()
                    conn.close()

            except Exception as e:
                results.append({"name": filename, "error": str(e), "status": "failed"})
                print(f"文件上传过程中出错: {filename}, 错误: {str(e)}")
            finally:
                # 删除临时文件
                if filepath and os.path.exists(filepath):
                    os.remove(filepath)
        else:
            raise RuntimeError({"name": filename, "error": "不支持的文件类型", "status": "failed"})

    return {"code": 0, "data": results, "message": f"成功上传 {len([r for r in results if r['status'] == 'success'])}/{len(files)} 个文件"}


def _canonical_chunk_number(value, minimum, maximum):
    """Accept only bounded, canonical decimal integers before file/Redis I/O."""
    if type(value) is int:
        number = value
    elif isinstance(value, str) and re.fullmatch(r"0|[1-9][0-9]{0,4}", value):
        number = int(value)
    else:
        raise ValueError("分块索引和数量必须是规范整数")
    if not minimum <= number <= maximum:
        raise ValueError("分块索引或数量超出允许范围")
    return number


def _chunk_upload_identity(upload_id, file_name, total_chunks, user_id):
    """Validate input and scope both Redis and disk state to the verified owner."""
    if not isinstance(user_id, str) or not user_id or len(user_id) > 256:
        raise ValueError("缺少有效的上传用户")
    if not isinstance(upload_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", upload_id):
        raise ValueError("上传ID无效")
    if (
        not isinstance(file_name, str)
        or not file_name
        or len(file_name) > 255
        or file_name in (".", "..")
        or any(char in file_name for char in ("/", "\\"))
        or any(ord(char) < 32 or ord(char) == 127 for char in file_name)
        or not allowed_file(file_name)
    ):
        raise ValueError("文件名或文件类型无效")
    total_chunks = _canonical_chunk_number(total_chunks, 1, MAX_UPLOAD_CHUNKS)
    # Structured encoding avoids ambiguous user/upload prefix concatenations.
    # Neither raw owner identifiers nor credentials are used in storage paths.
    identity = json.dumps([user_id, upload_id], ensure_ascii=True, separators=(",", ":"))
    scoped_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return scoped_id, total_chunks


def _read_chunk_info(redis, info_key, file_name, total_chunks, user_id):
    encoded = redis.hget(info_key, "metadata")
    if not encoded:
        return None
    info = json.loads(encoded)
    if (
        info.get("file_name") != file_name
        or info.get("total_chunks") != total_chunks
        or info.get("user_id") != user_id
        or not re.fullmatch(r"[0-9a-f]{32}", info.get("parent_id", ""))
    ):
        raise ValueError("上传参数与原始上传任务不一致")
    if redis.hget(info_key, "status") in (b"completed", "completed"):
        raise ValueError("上传任务已完成")
    return info


def handle_chunk_upload(chunk_file, chunk_index, total_chunks, upload_id, file_name, parent_id=None, user_id=None):
    """Save a chunk in the authenticated owner's private upload namespace.

    parent_id is retained for call compatibility but deliberately ignored: only
    server-generated buckets may be selected by the management upload API.
    """
    try:
        scoped_id, total_chunks = _chunk_upload_identity(upload_id, file_name, total_chunks, user_id)
        chunk_index = _canonical_chunk_number(chunk_index, 0, total_chunks - 1)
    except ValueError as error:
        return {"code": 400, "message": str(error)}

    temporary_chunk = None
    try:
        r = get_redis_connection()
        info_key = f"upload:v2:{scoped_id}:info"
        chunks_key = f"upload:v2:{scoped_id}:chunks"
        # The first arriving chunk (not necessarily chunk 0) binds immutable
        # metadata atomically. Later chunks cannot rename or resize the upload.
        r.hsetnx(info_key, "metadata", json.dumps({
            "file_name": file_name,
            "total_chunks": total_chunks,
            "user_id": user_id,
            "parent_id": uuid4().hex,
        }))
        if _read_chunk_info(r, info_key, file_name, total_chunks, user_id) is None:
            return {"code": 404, "message": "上传任务不存在或已过期"}
        r.expire(info_key, CHUNK_EXPIRY_SECONDS)

        upload_dir = Path(UPLOAD_TEMP_DIR) / "chunks" / "v2" / scoped_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        # Retried or simultaneous chunks cannot expose partially written bytes.
        with tempfile.NamedTemporaryFile(prefix="chunk_", dir=upload_dir, delete=False) as staged:
            temporary_chunk = staged.name
        chunk_file.save(temporary_chunk)
        os.replace(temporary_chunk, upload_dir / f"{chunk_index}.chunk")
        temporary_chunk = None

        r.setbit(chunks_key, chunk_index, 1)
        r.expire(chunks_key, CHUNK_EXPIRY_SECONDS)
        is_complete = all(r.getbit(chunks_key, i) for i in range(total_chunks))
        return {"code": 0, "data": {"upload_id": upload_id, "chunk_index": chunk_index, "is_complete": is_complete}, "message": "分块上传成功"}
    except ValueError as error:
        return {"code": 400, "message": str(error)}
    except Exception as error:
        print(f"分块上传失败: {str(error)}")
        return {"code": 500, "message": "分块上传失败"}
    finally:
        if temporary_chunk and os.path.exists(temporary_chunk):
            os.remove(temporary_chunk)


def merge_chunks(upload_id, file_name, total_chunks, parent_id=None, user_id=None):
    """Merge only this owner's original upload into its private storage bucket."""
    try:
        scoped_id, total_chunks = _chunk_upload_identity(upload_id, file_name, total_chunks, user_id)
    except ValueError as error:
        return {"code": 400, "message": str(error)}

    merged_path = None
    try:
        r = get_redis_connection()
        info_key = f"upload:v2:{scoped_id}:info"
        chunks_key = f"upload:v2:{scoped_id}:chunks"
        info = _read_chunk_info(r, info_key, file_name, total_chunks, user_id)
        if info is None:
            return {"code": 404, "message": "上传任务不存在或已过期"}

        upload_dir = Path(UPLOAD_TEMP_DIR) / "chunks" / "v2" / scoped_id
        for i in range(total_chunks):
            if not r.getbit(chunks_key, i) or not (upload_dir / f"{i}.chunk").is_file():
                return {"code": 400, "message": f"分块 {i} 未上传，无法合并"}

        # No client-controlled filename or upload ID is used as an output path.
        with tempfile.NamedTemporaryFile(prefix="merged_", dir=UPLOAD_TEMP_DIR, delete=False) as merged_file:
            merged_path = merged_file.name
            for i in range(total_chunks):
                with open(upload_dir / f"{i}.chunk", "rb") as chunk_file:
                    shutil.copyfileobj(chunk_file, merged_file)

        from werkzeug.datastructures import FileStorage

        with open(merged_path, "rb") as file_obj:
            merged_file = FileStorage(stream=file_obj, filename=file_name)
            result = upload_files_to_server([merged_file], parent_id=info["parent_id"], user_id=user_id)

        if result.get("code", 0) != 0 or any(item.get("status") != "success" for item in result.get("data", [])):
            # Keep original chunks available for a retry when storage fails.
            return {**result, "code": result.get("code") or 500}

        r.hset(info_key, "status", "completed")
        r.expire(info_key, CHUNK_EXPIRY_SECONDS)
        r.delete(chunks_key)
        shutil.rmtree(upload_dir)
        return result
    except ValueError as error:
        return {"code": 400, "message": str(error)}
    except Exception as error:
        print(f"合并分块失败: {str(error)}")
        return {"code": 500, "message": "合并分块失败"}
    finally:
        if merged_path and os.path.exists(merged_path):
            os.remove(merged_path)
