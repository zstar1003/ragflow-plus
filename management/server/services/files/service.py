import os
import mysql.connector
from io import BytesIO
from minio import Minio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("../../docker/.env")

# 数据库连接配置
DB_CONFIG = {
    "host": "localhost",  # 如果在Docker外运行，使用localhost
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