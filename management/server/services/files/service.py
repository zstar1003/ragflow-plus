import os
import mysql.connector
import re
from io import BytesIO
from minio import Minio
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from datetime import datetime 
from .utils import FileType, FileSource, StatusEnum, get_uuid
from .document_service import DocumentService
from .file_service import FileService 
from .file2document_service import File2DocumentService


# 加载环境变量
load_dotenv("../../docker/.env")

UPLOAD_FOLDER = '/data/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'txt', 'md'}

# 数据库连接配置
DB_CONFIG = {
    "host": "localhost",
    "port": int(os.getenv("MYSQL_PORT", "5455")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD", "infini_rag_flow"),
    "database": "rag_flow"
}

# MinIO连接配置
MINIO_CONFIG = {
    "endpoint": "localhost:" + os.getenv("MINIO_PORT", "9000"),
    "access_key": os.getenv("MINIO_USER", "rag_flow"),
    "secret_key": os.getenv("MINIO_PASSWORD", "infini_rag_flow"),
    "secure": False
}


def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def filename_type(filename):
    """根据文件名确定文件类型"""
    ext = os.path.splitext(filename)[1].lower()
    
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
        return FileType.VISUAL.value
    elif ext in ['.pdf']:
        return FileType.PDF.value
    elif ext in ['.doc', '.docx']:
        return FileType.WORD.value
    elif ext in ['.xls', '.xlsx']:
        return FileType.EXCEL.value
    elif ext in ['.ppt', '.pptx']:
        return FileType.PPT.value
    elif ext in ['.txt', '.md']:  # 添加对 txt 和 md 文件的支持
        return FileType.TEXT.value
    
    return FileType.OTHER.value

def get_minio_client():
    """创建MinIO客户端"""
    return Minio(
        endpoint=MINIO_CONFIG["endpoint"],
        access_key=MINIO_CONFIG["access_key"],
        secret_key=MINIO_CONFIG["secret_key"],
        secure=MINIO_CONFIG["secure"]
    )

def get_db_connection():
    """创建数据库连接"""
    return mysql.connector.connect(**DB_CONFIG)

def get_files_list(current_page, page_size, name_filter=""):
    """
    获取文件列表
    
    Args:
        current_page: 当前页码
        page_size: 每页大小
        name_filter: 文件名过滤条件
        
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
        where_clause = ""
        params = []
        
        if name_filter:
            where_clause = "WHERE d.name LIKE %s"
            params.append(f"%{name_filter}%")
        
        # 查询总数
        count_query = f"""
            SELECT COUNT(*) as total
            FROM document d
            {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # 查询文件列表
        query = f"""
            SELECT d.id, d.name, d.kb_id, d.location, d.size, d.type, d.create_time
            FROM document d
            {where_clause}
            ORDER BY d.create_time DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, params + [page_size, offset])
        documents = cursor.fetchall()
        
        # 获取文档与文件的关联信息
        doc_ids = [doc['id'] for doc in documents]
        file_mappings = {}
        
        if doc_ids:
            placeholders = ', '.join(['%s'] * len(doc_ids))
            cursor.execute(f"""
                SELECT f2d.document_id, f.id as file_id, f.parent_id, f.source_type
                FROM file2document f2d
                JOIN file f ON f2d.file_id = f.id
                WHERE f2d.document_id IN ({placeholders})
            """, doc_ids)
            
            for row in cursor.fetchall():
                file_mappings[row['document_id']] = {
                    'file_id': row['file_id'],
                    'parent_id': row['parent_id'],
                    'source_type': row['source_type']
                }
        
        # 整合信息
        result = []
        for doc in documents:
            doc_id = doc['id']
            kb_id = doc['kb_id']
            location = doc['location']
            
            # 确定存储位置
            storage_bucket = kb_id
            storage_location = location
            
            # 如果有文件映射，检查是否需要使用文件的parent_id作为bucket
            if doc_ids and doc_id in file_mappings:
                file_info = file_mappings[doc_id]
                # 模拟File2DocumentService.get_storage_address的逻辑
                if file_info.get('source_type') is None or file_info.get('source_type') == 0:  # LOCAL
                    storage_bucket = file_info['parent_id']
            
            # 构建结果字典
            result_item = {
                'id': doc_id,
                'name': doc.get('name', ''),
                'kb_id': kb_id,
                'size': doc.get('size', 0),
                'type': doc.get('type', ''),
                'location': location,
                'create_time': doc.get('create_time', 0)
            }
                
            result.append(result_item)
        
        cursor.close()
        conn.close()
        
        return result, total
        
    except Exception as e:
        raise e

def get_file_info(file_id):
    """
    获取文件信息
    
    Args:
        file_id: 文件ID
        
    Returns:
        tuple: (文档信息, 文件映射信息, 存储桶, 存储位置)
    """
    try:
        # 连接数据库
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 查询文档信息
        cursor.execute("""
            SELECT d.id, d.name, d.kb_id, d.location, d.type
            FROM document d
            WHERE d.id = %s
        """, (file_id,))
        
        document = cursor.fetchone()
        if not document:
            cursor.close()
            conn.close()
            return None, None, None, None
        
        # 获取文档与文件的关联信息
        cursor.execute("""
            SELECT f2d.document_id, f.id as file_id, f.parent_id, f.source_type
            FROM file2document f2d
            JOIN file f ON f2d.file_id = f.id
            WHERE f2d.document_id = %s
        """, (file_id,))
        
        file_mapping = cursor.fetchone()
        
        # 确定存储位置
        storage_bucket = document['kb_id']
        storage_location = document['location']
        
        # 如果有文件映射，检查是否需要使用文件的parent_id作为bucket
        if file_mapping:
            # 模拟File2DocumentService.get_storage_address的逻辑
            if file_mapping.get('source_type') is None or file_mapping.get('source_type') == 0:  # LOCAL
                storage_bucket = file_mapping['parent_id']
        
        cursor.close()
        conn.close()
        
        return document, file_mapping, storage_bucket, storage_location
        
    except Exception as e:
        raise e

def download_file_from_minio(storage_bucket, storage_location):
    """
    从MinIO下载文件
    
    Args:
        storage_bucket: 存储桶
        storage_location: 存储位置
        
    Returns:
        bytes: 文件数据
    """
    try:
        # 从MinIO下载文件
        minio_client = get_minio_client()
        
        # 检查bucket是否存在
        if not minio_client.bucket_exists(storage_bucket):
            raise Exception(f"存储桶 {storage_bucket} 不存在")
        
        # 下载文件
        response = minio_client.get_object(storage_bucket, storage_location)
        file_data = response.read()
        
        return file_data
        
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
        # 获取文件信息
        document, file_mapping, storage_bucket, storage_location = get_file_info(file_id)
        
        if not document:
            return False
        
        # 连接数据库
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 如果有文件映射，获取文件ID
        file_id_to_delete = None
        if file_mapping:
            file_id_to_delete = file_mapping['file_id']
        
        # 开始事务
        conn.start_transaction()
        
        try:
            # 1. 删除document表中的记录
            cursor.execute("DELETE FROM document WHERE id = %s", (file_id,))
            
            # 2. 如果有关联的file2document记录，删除它
            if file_mapping:
                cursor.execute("DELETE FROM file2document WHERE document_id = %s", (file_id,))
            
            # 3. 如果有关联的file记录，删除它
            if file_id_to_delete:
                cursor.execute("DELETE FROM file WHERE id = %s", (file_id_to_delete,))
            
            # 提交事务
            conn.commit()
            
            # 从MinIO删除文件
            try:
                minio_client = get_minio_client()
                
                # 检查bucket是否存在
                if minio_client.bucket_exists(storage_bucket):
                    # 删除文件
                    minio_client.remove_object(storage_bucket, storage_location)
            except Exception as e:
                # 即使MinIO删除失败，也不影响数据库操作的成功
                print(f"从MinIO删除文件失败: {str(e)}")
            
            return True
            
        except Exception as e:
            # 回滚事务
            conn.rollback()
            raise e
        
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
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
        conn.start_transaction()
        
        try:
            success_count = 0
            
            for file_id in file_ids:
                # 查询文档信息
                cursor.execute("""
                    SELECT d.id, d.kb_id, d.location
                    FROM document d
                    WHERE d.id = %s
                """, (file_id,))
                
                document = cursor.fetchone()
                if not document:
                    continue
                
                # 获取文档与文件的关联信息
                cursor.execute("""
                    SELECT f2d.id as f2d_id, f2d.document_id, f2d.file_id, f.parent_id, f.source_type
                    FROM file2document f2d
                    JOIN file f ON f2d.file_id = f.id
                    WHERE f2d.document_id = %s
                """, (file_id,))
                
                file_mapping = cursor.fetchone()
                
                # 确定存储位置
                storage_bucket = document['kb_id']
                storage_location = document['location']
                
                # 如果有文件映射，检查是否需要使用文件的parent_id作为bucket
                file_id_to_delete = None
                if file_mapping:
                    file_id_to_delete = file_mapping['file_id']
                    # 模拟File2DocumentService.get_storage_address的逻辑
                    if file_mapping.get('source_type') is None or file_mapping.get('source_type') == 0:  # LOCAL
                        storage_bucket = file_mapping['parent_id']
                
                # 1. 删除document表中的记录
                cursor.execute("DELETE FROM document WHERE id = %s", (file_id,))
                
                # 2. 如果有关联的file2document记录，删除它
                if file_mapping:
                    cursor.execute("DELETE FROM file2document WHERE id = %s", (file_mapping['f2d_id'],))
                
                # 3. 如果有关联的file记录，删除它
                if file_id_to_delete:
                    cursor.execute("DELETE FROM file WHERE id = %s", (file_id_to_delete,))
                
                # 从MinIO删除文件
                try:
                    # 检查bucket是否存在
                    if minio_client.bucket_exists(storage_bucket):
                        # 删除文件
                        minio_client.remove_object(storage_bucket, storage_location)
                except Exception as e:
                    # 即使MinIO删除失败，也不影响数据库操作的成功
                    print(f"从MinIO删除文件失败: {str(e)}")
                
                success_count += 1
            
            # 提交事务
            conn.commit()
            
            return success_count
            
        except Exception as e:
            # 回滚事务
            conn.rollback()
            raise e
        
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        raise e

def upload_files_to_server(files, kb_id=None, user_id=None):
    """处理文件上传到服务器的核心逻辑"""
    results = []

    for file in files:
        if file.filename == '':
            continue
            
        if file and allowed_file(file.filename):
            # 为每个文件生成独立的存储桶名称
            file_bucket_id = FileService.generate_bucket_name()
            original_filename = file.filename
            # 修复文件名处理逻辑，保留中文字符
            name, ext = os.path.splitext(original_filename)
            
            # 保留中文字符，但替换不安全字符
            # 只替换文件系统不安全的字符，保留中文和其他Unicode字符
            safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)
            
            # 如果处理后文件名为空，则使用随机字符串
            if not safe_name or safe_name.strip() == '':
                safe_name = f"file_{get_uuid()[:8]}"
                
            filename = safe_name + ext.lower()
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            try:
                # 1. 保存文件到本地临时目录
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file.save(filepath)
                print(f"文件已保存到临时目录: {filepath}")
                print(f"原始文件名: {original_filename}, 处理后文件名: {filename}, 扩展名: {ext[1:]}")  # 修改打印信息
                
                # 2. 获取文件类型 - 使用修复后的文件名
                filetype = filename_type(filename)
                if filetype == FileType.OTHER.value:
                    raise RuntimeError("不支持的文件类型")
                
                # 3. 生成唯一存储位置
                minio_client = get_minio_client()
                location = filename
                
                # 确保bucket存在（使用文件独立的bucket）
                if not minio_client.bucket_exists(file_bucket_id):
                    minio_client.make_bucket(file_bucket_id)
                    print(f"创建MinIO存储桶: {file_bucket_id}")
                
                # 4. 上传到MinIO（使用文件独立的bucket）
                with open(filepath, 'rb') as file_data:
                    minio_client.put_object(
                        bucket_name=file_bucket_id,
                        object_name=location,
                        data=file_data,
                        length=os.path.getsize(filepath)
                    )
                print(f"文件已上传到MinIO: {file_bucket_id}/{location}")
                
                # 5. 创建缩略图(如果是图片/PDF等)
                thumbnail_location = ''
                if filetype in [FileType.VISUAL.value, FileType.PDF.value]:
                    try:
                        thumbnail_location = f'thumbnail_{get_uuid()}.png'
                    except Exception as e:
                        print(f"生成缩略图失败: {str(e)}")
                
                # 6. 创建数据库记录
                doc_id = get_uuid()
                current_time = int(datetime.now().timestamp())
                current_date = datetime.now().strftime('%Y-%m-%d')
                
                doc = {
                    "id": doc_id,
                    "kb_id": file_bucket_id,  # 使用文件独立的bucket_id
                    "parser_id": FileService.get_parser(filetype, filename, ""),
                    "parser_config": {"pages": [[1, 1000000]]},
                    "source_type": "local",
                    "created_by": user_id or 'system',
                    "type": filetype,
                    "name": filename,
                    "location": location,
                    "size": os.path.getsize(filepath),
                    "thumbnail": thumbnail_location,
                    "token_num": 0,
                    "chunk_num": 0,
                    "progress": 0,
                    "progress_msg": "",
                    "run": "0",
                    "status": StatusEnum.VALID.value,
                    "create_time": current_time,
                    "create_date": current_date,
                    "update_time": current_time,
                    "update_date": current_date
                }
                
                # 7. 保存文档记录 (添加事务处理)
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    DocumentService.insert(doc)
                    print(f"文档记录已保存到MySQL: {doc_id}")
                    
                    # 8. 创建文件记录和关联
                    file_record = {
                        "id": get_uuid(),
                        "parent_id": file_bucket_id,  # 使用文件独立的bucket_id
                        "tenant_id": user_id or 'system',
                        "created_by": user_id or 'system',
                        "name": filename,
                        "type": filetype,
                        "size": doc["size"],
                        "location": location,
                        "source_type": FileSource.KNOWLEDGEBASE.value,
                        "create_time": current_time,
                        "create_date": current_date,
                        "update_time": current_time,
                        "update_date": current_date
                    }
                    FileService.insert(file_record)
                    print(f"文件记录已保存到MySQL: {file_record['id']}")
                    
                    # 9. 创建文件-文档关联
                    File2DocumentService.insert({
                        "id": get_uuid(),
                        "file_id": file_record["id"],
                        "document_id": doc_id,
                        "create_time": current_time,
                        "create_date": current_date,
                        "update_time": current_time,
                        "update_date": current_date
                    })
                    print(f"关联记录已保存到MySQL: {file_record['id']} -> {doc_id}")
                    
                    conn.commit()
                    
                    results.append({
                        'id': doc_id,
                        'name': filename,
                        'size': doc["size"],
                        'type': filetype,
                        'status': 'success'
                    })
                    
                except Exception as e:
                    conn.rollback()
                    print(f"数据库操作失败: {str(e)}")
                    raise
                finally:
                    cursor.close()
                    conn.close()
                
            except Exception as e:
                results.append({
                    'name': filename,
                    'error': str(e),
                    'status': 'failed'
                })
                print(f"文件上传过程中出错: {filename}, 错误: {str(e)}")
            finally:
                # 删除临时文件
                if os.path.exists(filepath):
                    os.remove(filepath)
    
    return {
        'code': 0,
        'data': results,
        'message': f'成功上传 {len([r for r in results if r["status"] == "success"])}/{len(files)} 个文件'
    }