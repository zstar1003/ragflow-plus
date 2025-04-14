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
from database import DB_CONFIG, MINIO_CONFIG

# 加载环境变量
load_dotenv("../../docker/.env")

UPLOAD_FOLDER = '/data/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'txt', 'md'}

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
    elif ext in ['.txt', '.md']:
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

def get_files_list(current_page, page_size, parent_id=None, name_filter=""):
    """
    获取文件列表
    
    Args:
        current_page: 当前页码
        page_size: 每页大小
        parent_id: 父文件夹ID
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
        where_clause = "WHERE f.type != 'folder'"  # 排除文件夹类型
        params = []
        
        if parent_id:
            where_clause += " AND f.parent_id = %s"
            params.append(parent_id)
        
        if name_filter:
            where_clause += " AND f.name LIKE %s"
            params.append(f"%{name_filter}%")
        
        # 查询总数
        count_query = f"""
            SELECT COUNT(*) as total
            FROM file f
            {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # 查询文件列表
        query = f"""
            SELECT f.id, f.name, f.parent_id, f.type, f.size, f.location, f.source_type, f.create_time
            FROM file f
            {where_clause}
            ORDER BY f.create_time DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, params + [page_size, offset])
        files = cursor.fetchall()
        
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
        cursor.execute("""
            SELECT id, name, parent_id, type, size, location, source_type
            FROM file
            WHERE id = %s
        """, (file_id,))
        
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
        storage_bucket = file['parent_id']
        storage_location = file['location']
        
        # 检查bucket是否存在
        if not minio_client.bucket_exists(storage_bucket):
            raise Exception(f"存储桶 {storage_bucket} 不存在")
        
        # 下载文件
        response = minio_client.get_object(storage_bucket, storage_location)
        file_data = response.read()
        
        return file_data, file['name']
        
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
        cursor.execute("""
            SELECT id, parent_id, name, location, type
            FROM file
            WHERE id = %s
        """, (file_id,))
        
        file = cursor.fetchone()
        if not file:
            cursor.close()
            conn.close()
            return False
        
        # 如果是文件夹，直接返回成功（不处理文件夹）
        if file['type'] == FileType.FOLDER.value:
            cursor.close()
            conn.close()
            return True
        
        # 查询关联的document记录
        cursor.execute("""
            SELECT f2d.document_id, d.kb_id, d.location
            FROM file2document f2d
            JOIN document d ON f2d.document_id = d.id
            WHERE f2d.file_id = %s
        """, (file_id,))
        
        document_mappings = cursor.fetchall()
        
        # 创建MinIO客户端（在事务外创建）
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
                cursor.execute("DELETE FROM document WHERE id = %s", (doc_mapping['document_id'],))
            
            # 提交事务
            cursor.execute("COMMIT")
            
            # 从MinIO删除文件（在事务提交后进行）
            try:
                # 检查bucket是否存在，如果不存在则跳过MinIO删除操作
                parent_id = file.get('parent_id')
                if parent_id and minio_client.bucket_exists(parent_id):
                    try:
                        # 删除文件，忽略文件不存在的错误
                        minio_client.remove_object(parent_id, file['location'])
                        print(f"从MinIO删除文件成功: {parent_id}/{file['location']}")
                    except Exception as e:
                        print(f"从MinIO删除文件失败: {parent_id}/{file['location']} - {str(e)}")
                else:
                    print(f"存储桶不存在，跳过MinIO删除操作: {parent_id}")
                
                # 如果有关联的document，也删除document存储的文件
                for doc_mapping in document_mappings:
                    kb_id = doc_mapping.get('kb_id')
                    doc_location = doc_mapping.get('location')
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
            except:
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
                cursor.execute("""
                    SELECT id, parent_id, name, location, type
                    FROM file
                    WHERE id = %s
                """, (file_id,))
                
                file = cursor.fetchone()
                if not file:
                    continue
                
                # 如果是文件夹，跳过
                if file['type'] == FileType.FOLDER.value:
                    continue
                
                # 查询关联的document记录
                cursor.execute("""
                    SELECT f2d.id as f2d_id, f2d.document_id, d.kb_id, d.location
                    FROM file2document f2d
                    JOIN document d ON f2d.document_id = d.id
                    WHERE f2d.file_id = %s
                """, (file_id,))
                
                document_mappings = cursor.fetchall()
                
                # 1. 先删除file表中的记录
                cursor.execute("DELETE FROM file WHERE id = %s", (file_id,))
                
                # 2. 删除关联的file2document记录
                cursor.execute("DELETE FROM file2document WHERE file_id = %s", (file_id,))
                
                # 3. 删除关联的document记录
                for doc_mapping in document_mappings:
                    cursor.execute("DELETE FROM document WHERE id = %s", (doc_mapping['document_id'],))
                
                success_count += 1
            
            # 提交事务
            cursor.execute("COMMIT")
            
            # 从MinIO删除文件（在事务提交后进行）
            for file_id in file_ids:
                try:
                    # 查询文件信息
                    cursor.execute("""
                        SELECT id, parent_id, name, location, type
                        FROM file
                        WHERE id = %s
                    """, (file_id,))
                    
                    file = cursor.fetchone()
                    if not file and file['type'] != FileType.FOLDER.value:
                        # 检查bucket是否存在
                        if minio_client.bucket_exists(file['parent_id']):
                            # 删除文件
                            minio_client.remove_object(file['parent_id'], file['location'])
                        
                        # 如果有关联的document，也删除document存储的文件
                        cursor.execute("""
                            SELECT f2d.id as f2d_id, f2d.document_id, d.kb_id, d.location
                            FROM file2document f2d
                            JOIN document d ON f2d.document_id = d.id
                            WHERE f2d.file_id = %s
                        """, (file_id,))
                        
                        document_mappings = cursor.fetchall()
                        for doc_mapping in document_mappings:
                            if minio_client.bucket_exists(doc_mapping['kb_id']):
                                minio_client.remove_object(doc_mapping['kb_id'], doc_mapping['location'])
                except Exception as e:
                    # 即使MinIO删除失败，也不影响数据库操作的成功
                    print(f"从MinIO删除文件失败: {str(e)}")
            
            return success_count
            
        except Exception as e:
            # 回滚事务
            try:
                cursor.execute("ROLLBACK")
            except:
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
                user_id = earliest_user['id']
                print(f"使用创建时间最早的用户ID: {user_id}")
            else:
                user_id = 'system'
                print("未找到用户, 使用默认用户ID: system")
                
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"查询最早用户ID失败: {str(e)}")
            user_id = 'system'
    
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
                parent_id = first_file['id']
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
        if file.filename == '':
            continue
            
        if file and allowed_file(file.filename):
            original_filename = file.filename
            # 修复文件名处理逻辑，保留中文字符
            name, ext = os.path.splitext(original_filename)
            
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
                with open(filepath, 'rb') as file_data:
                    minio_client.put_object(
                        bucket_name=parent_id,
                        object_name=location,
                        data=file_data,
                        length=os.path.getsize(filepath)
                    )
                print(f"文件已上传到MinIO: {parent_id}/{location}")
                
                # 5. 创建文件记录
                file_id = get_uuid()
                current_time = int(datetime.now().timestamp())
                current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
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
                    "update_date": current_date
                }
                
                # 保存文件记录
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    
                    # 插入文件记录
                    columns = ', '.join(file_record.keys())
                    placeholders = ', '.join(['%s'] * len(file_record))
                    query = f"INSERT INTO file ({columns}) VALUES ({placeholders})"
                    cursor.execute(query, list(file_record.values()))
                    
                    conn.commit()
                    
                    results.append({
                        'id': file_id,
                        'name': filename,
                        'size': file_record["size"],
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