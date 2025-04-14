import mysql.connector
import json
from flask import current_app
from datetime import datetime
from utils import generate_uuid
from database import DB_CONFIG, get_minio_client
import io
import os
import json
import threading
import time
import tempfile
import shutil
from io import BytesIO

# 解析相关模块
from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod

# 自定义tokenizer和文本处理函数，替代rag.nlp中的功能
def tokenize_text(text):
    """将文本分词，替代rag_tokenizer功能"""
    # 简单实现，实际应用中可能需要更复杂的分词逻辑
    return text.split()

def merge_chunks(sections, chunk_token_num=128, delimiter="\n。；！？"):
    """合并文本块，替代naive_merge功能"""
    if not sections:
        return []
    
    chunks = [""]
    token_counts = [0]
    
    for section in sections:
        # 计算当前部分的token数量
        text = section[0] if isinstance(section, tuple) else section
        position = section[1] if isinstance(section, tuple) and len(section) > 1 else ""
        
        # 简单估算token数量
        token_count = len(text.split())
        
        # 如果当前chunk已经超过限制，创建新chunk
        if token_counts[-1] > chunk_token_num:
            chunks.append(text)
            token_counts.append(token_count)
        else:
            # 否则添加到当前chunk
            chunks[-1] += text
            token_counts[-1] += token_count
    
    return chunks

def process_document_chunks(chunks, document_info):
    """处理文档块，替代tokenize_chunks功能"""
    results = []
    
    for chunk in chunks:
        if not chunk.strip():
            continue
            
        # 创建文档块对象
        chunk_data = document_info.copy()
        chunk_data["content"] = chunk
        chunk_data["tokens"] = tokenize_text(chunk)
        
        results.append(chunk_data)
    
    return results



class KnowledgebaseService:

    @classmethod
    def _get_db_connection(cls):
        """Get database connection"""
        return mysql.connector.connect(**DB_CONFIG)
        
    @classmethod
    def get_knowledgebase_list(cls, page=1, size=10, name=''):
        """获取知识库列表"""
        conn = cls._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                k.id, 
                k.name, 
                k.description, 
                k.create_date,
                k.update_date,
                k.doc_num,
                k.language,
                k.permission
            FROM knowledgebase k
        """
        params = []
        
        if name:
            query += " WHERE k.name LIKE %s"
            params.append(f"%{name}%")
            
        query += " LIMIT %s OFFSET %s"
        params.extend([size, (page-1)*size])
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # 处理结果
        for result in results:
            # 处理空描述
            if not result.get('description'):
                result['description'] = "暂无描述"
            # 处理时间格式
            if result.get('create_date'):
                if isinstance(result['create_date'], datetime):
                    result['create_date'] = result['create_date'].strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(result['create_date'], str):
                    try:
                        # 尝试解析已有字符串格式
                        datetime.strptime(result['create_date'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        result['create_date'] = ""
        
        # 获取总数
        count_query = "SELECT COUNT(*) as total FROM knowledgebase"
        if name:
            count_query += " WHERE name LIKE %s"
        cursor.execute(count_query, params[:1] if name else [])
        total = cursor.fetchone()['total']
        
        cursor.close()
        conn.close()
    
        return {
            'list': results,
            'total': total
        }

    @classmethod
    def get_knowledgebase_detail(cls, kb_id):
        """获取知识库详情"""
        conn = cls._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                k.id, 
                k.name, 
                k.description, 
                k.create_date,
                k.update_date,
                k.doc_num
            FROM knowledgebase k
            WHERE k.id = %s
        """
        cursor.execute(query, (kb_id,))
        result = cursor.fetchone()
        
        if result:
            # 处理空描述
            if not result.get('description'):
                result['description'] = "暂无描述"
            # 处理时间格式
            if result.get('create_date'):
                if isinstance(result['create_date'], datetime):
                    result['create_date'] = result['create_date'].strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(result['create_date'], str):
                    try:
                        datetime.strptime(result['create_date'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        result['create_date'] = ""
        
        cursor.close()
        conn.close()
        
        return result

    @classmethod
    def _check_name_exists(cls, name):
        """检查知识库名称是否已存在"""
        conn = cls._get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT COUNT(*) as count 
            FROM knowledgebase 
            WHERE name = %s
        """
        cursor.execute(query, (name,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result[0] > 0

    @classmethod
    def create_knowledgebase(cls, **data):
        """创建知识库"""
        try:
            # 检查知识库名称是否已存在
            exists = cls._check_name_exists(data['name'])
            if exists:
                raise Exception("知识库名称已存在")
    
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 获取最早的用户ID作为tenant_id和created_by
            tenant_id = None
            created_by = None
            try:
                query_earliest_user = """
                SELECT id FROM user 
                WHERE create_time = (SELECT MIN(create_time) FROM user)
                LIMIT 1
                """
                cursor.execute(query_earliest_user)
                earliest_user = cursor.fetchone()
                
                if earliest_user:
                    tenant_id = earliest_user['id']
                    created_by = earliest_user['id']  # 使用最早用户ID作为created_by
                    print(f"使用创建时间最早的用户ID作为tenant_id和created_by: {tenant_id}")
                else:
                    # 如果找不到用户，使用默认值
                    tenant_id = "system"
                    created_by = "system"
                    print(f"未找到用户, 使用默认值作为tenant_id和created_by: {tenant_id}")
            except Exception as e:
                print(f"获取用户ID失败: {str(e)}，使用默认值")
                tenant_id = "system"
                created_by = "system"
            
            current_time = datetime.now()
            create_date = current_time.strftime('%Y-%m-%d %H:%M:%S')
            create_time = int(current_time.timestamp() * 1000)  # 毫秒级时间戳
            update_date = create_date
            update_time = create_time
            
            # 完整的字段列表
            query = """
                INSERT INTO knowledgebase (
                    id, create_time, create_date, update_time, update_date,
                    avatar, tenant_id, name, language, description,
                    embd_id, permission, created_by, doc_num, token_num,
                    chunk_num, similarity_threshold, vector_similarity_weight, parser_id, parser_config,
                    pagerank, status
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s
                )
            """
            
            # 设置默认值
            default_parser_config = json.dumps({
                "layout_recognize": "DeepDOC", 
                "chunk_token_num": 512, 
                "delimiter": "\n!?;。；！？", 
                "auto_keywords": 0, 
                "auto_questions": 0, 
                "html4excel": False, 
                "raptor": {"use_raptor": False}, 
                "graphrag": {"use_graphrag": False}
            })
            
            kb_id = generate_uuid()
            cursor.execute(query, (
                kb_id,                                      # id
                create_time,                                # create_time
                create_date,                                # create_date
                update_time,                                # update_time
                update_date,                                # update_date
                None,                                       # avatar
                tenant_id,                                  # tenant_id
                data['name'],                               # name
                data.get('language', 'Chinese'),            # language
                data.get('description', ''),                # description
                'bge-m3:latest@Ollama',                     # embd_id
                data.get('permission', 'me'),               # permission
                created_by,                                 # created_by - 使用内部获取的值
                0,                                          # doc_num
                0,                                          # token_num
                0,                                          # chunk_num
                0.7,                                        # similarity_threshold
                0.3,                                        # vector_similarity_weight
                'naive',                                    # parser_id
                default_parser_config,                      # parser_config
                0,                                          # pagerank
                '1'                                         # status
            ))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            # 返回创建后的知识库详情
            return cls.get_knowledgebase_detail(kb_id)
            
        except Exception as e:
            current_app.logger.error(f"创建知识库失败: {str(e)}")
            raise Exception(f"创建知识库失败: {str(e)}")

    @classmethod
    def update_knowledgebase(cls, kb_id, **data):
        """更新知识库"""
        try:
            # 直接通过ID检查知识库是否存在
            kb = cls.get_knowledgebase_detail(kb_id)
            if not kb:
                return None
            
            conn = cls._get_db_connection()
            cursor = conn.cursor()
            
            # 如果要更新名称，先检查名称是否已存在
            if data.get('name') and data['name'] != kb['name']:
                exists = cls._check_name_exists(data['name'])
                if exists:
                    raise Exception("知识库名称已存在")
            
            # 构建更新语句
            update_fields = []
            params = []
            
            if data.get('name'):
                update_fields.append("name = %s")
                params.append(data['name'])
                
            if 'description' in data:
                update_fields.append("description = %s")
                params.append(data['description'])
            
            # 更新时间
            current_time = datetime.now()
            update_date = current_time.strftime('%Y-%m-%d %H:%M:%S')
            update_fields.append("update_date = %s")
            params.append(update_date)
            
            # 如果没有要更新的字段，直接返回
            if not update_fields:
                return kb_id
                
            # 构建并执行更新语句
            query = f"""
                UPDATE knowledgebase 
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            params.append(kb_id)
            
            cursor.execute(query, params)
            conn.commit()
            
            cursor.close()
            conn.close()
            
            # 返回更新后的知识库详情
            return cls.get_knowledgebase_detail(kb_id)
            
        except Exception as e:
            print(f"更新知识库失败: {str(e)}")
            raise Exception(f"更新知识库失败: {str(e)}")

    @classmethod
    def delete_knowledgebase(cls, kb_id):
        """删除知识库"""
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor()
            
            # 先检查知识库是否存在
            check_query = "SELECT id FROM knowledgebase WHERE id = %s"
            cursor.execute(check_query, (kb_id,))
            if not cursor.fetchone():
                raise Exception("知识库不存在")
            
            # 执行删除
            delete_query = "DELETE FROM knowledgebase WHERE id = %s"
            cursor.execute(delete_query, (kb_id,))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return True
        except Exception as e:
            current_app.logger.error(f"删除知识库失败: {str(e)}")
            raise Exception(f"删除知识库失败: {str(e)}")

    @classmethod
    def batch_delete_knowledgebase(cls, kb_ids):
        """批量删除知识库"""
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor()
            
            # 检查所有ID是否存在
            check_query = "SELECT id FROM knowledgebase WHERE id IN (%s)" % \
                         ','.join(['%s'] * len(kb_ids))
            cursor.execute(check_query, kb_ids)
            existing_ids = [row[0] for row in cursor.fetchall()]
            
            if len(existing_ids) != len(kb_ids):
                missing_ids = set(kb_ids) - set(existing_ids)
                raise Exception(f"以下知识库不存在: {', '.join(missing_ids)}")
            
            # 执行批量删除
            delete_query = "DELETE FROM knowledgebase WHERE id IN (%s)" % \
                          ','.join(['%s'] * len(kb_ids))
            cursor.execute(delete_query, kb_ids)
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return len(kb_ids)
        except Exception as e:
            current_app.logger.error(f"批量删除知识库失败: {str(e)}")
            raise Exception(f"批量删除知识库失败: {str(e)}")

    @classmethod
    def get_knowledgebase_documents(cls, kb_id, page=1, size=10, name=''):
        """获取知识库下的文档列表"""
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 先检查知识库是否存在
            check_query = "SELECT id FROM knowledgebase WHERE id = %s"
            cursor.execute(check_query, (kb_id,))
            if not cursor.fetchone():
                raise Exception("知识库不存在")
            
            # 查询文档列表
            query = """
                SELECT 
                    d.id, 
                    d.name, 
                    d.chunk_num,
                    d.create_date,
                    d.status,
                    d.run,
                    d.progress,
                    d.parser_id,
                    d.parser_config,
                    d.meta_fields
                FROM document d
                WHERE d.kb_id = %s
            """
            params = [kb_id]
            
            if name:
                query += " AND d.name LIKE %s"
                params.append(f"%{name}%")
                
            query += " ORDER BY d.create_date DESC LIMIT %s OFFSET %s"
            params.extend([size, (page-1)*size])
            
            cursor.execute(query, params)
            results = cursor.fetchall()

            # 处理日期时间格式
            for result in results:
                if result.get('create_date'):
                    result['create_date'] = result['create_date'].strftime('%Y-%m-%d %H:%M:%S')

            # 获取总数
            count_query = "SELECT COUNT(*) as total FROM document WHERE kb_id = %s"
            count_params = [kb_id]
            if name:
                count_query += " AND name LIKE %s"
                count_params.append(f"%{name}%")
                
            cursor.execute(count_query, count_params)
            total = cursor.fetchone()['total']
            
            cursor.close()
            conn.close()

            print(results)
            return {
                'list': results,
                'total': total
            }
                
        except Exception as e:
            current_app.logger.error(f"获取知识库文档列表失败: {str(e)}")
            raise Exception(f"获取知识库文档列表失败: {str(e)}")

    @classmethod
    def add_documents_to_knowledgebase(cls, kb_id, file_ids, created_by=None):
        """添加文档到知识库"""
        try:
            print(f"[DEBUG] 开始添加文档，参数: kb_id={kb_id}, file_ids={file_ids}")
            
            # 如果没有传入created_by，则获取最早的用户ID
            if created_by is None:
                conn = cls._get_db_connection()
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
                    created_by = earliest_user['id']
                    print(f"使用创建时间最早的用户ID: {created_by}")
                else:
                    created_by = 'system'
                    print("未找到用户, 使用默认用户ID: system")
                    
                cursor.close()
                conn.close()
            
            # 检查知识库是否存在
            kb = cls.get_knowledgebase_detail(kb_id)
            print(f"[DEBUG] 知识库检查结果: {kb}")
            if not kb:
                print(f"[ERROR] 知识库不存在: {kb_id}")
                raise Exception("知识库不存在")
            
            conn = cls._get_db_connection()
            cursor = conn.cursor()
            
            # 获取文件信息
            file_query = """
                SELECT id, name, location, size, type 
                FROM file 
                WHERE id IN (%s)
            """ % ','.join(['%s'] * len(file_ids))
            
            print(f"[DEBUG] 执行文件查询SQL: {file_query}")
            print(f"[DEBUG] 查询参数: {file_ids}")
            
            try:
                cursor.execute(file_query, file_ids)
                files = cursor.fetchall()
                print(f"[DEBUG] 查询到的文件数据: {files}")
            except Exception as e:
                print(f"[ERROR] 文件查询失败: {str(e)}")
                raise
            
            if len(files) != len(file_ids):
                print(f"部分文件不存在: 期望={len(file_ids)}, 实际={len(files)}")
                raise Exception("部分文件不存在")
            
            # 添加文档记录
            added_count = 0
            for file in files:
                file_id = file[0]
                file_name = file[1]
                print(f"处理文件: id={file_id}, name={file_name}")
                
                file_location = file[2]
                file_size = file[3]
                file_type = file[4]
                
                # 检查文档是否已存在于知识库
                check_query = """
                    SELECT COUNT(*) 
                    FROM document d
                    JOIN file2document f2d ON d.id = f2d.document_id
                    WHERE d.kb_id = %s AND f2d.file_id = %s
                """
                cursor.execute(check_query, (kb_id, file_id))
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    continue  # 跳过已存在的文档
                
                # 创建文档记录
                doc_id = generate_uuid()
                current_datetime = datetime.now()
                create_time = int(current_datetime.timestamp() * 1000)  # 毫秒级时间戳
                current_date = current_datetime.strftime("%Y-%m-%d %H:%M:%S")  # 格式化日期字符串
                
                # 设置默认值
                default_parser_id = "naive"
                default_parser_config = json.dumps({
                    "layout_recognize": "DeepDOC",
                    "chunk_token_num": 512,
                    "delimiter": "\n!?;。；！？",
                    "auto_keywords": 0,
                    "auto_questions": 0,
                    "html4excel": False,
                    "raptor": {
                        "use_raptor": False
                    },
                    "graphrag": {
                        "use_graphrag": False
                    }
                })
                default_source_type = "local"
                
                # 插入document表
                doc_query = """
                    INSERT INTO document (
                        id, create_time, create_date, update_time, update_date,
                        thumbnail, kb_id, parser_id, parser_config, source_type,
                        type, created_by, name, location, size,
                        token_num, chunk_num, progress, progress_msg, process_begin_at,
                        process_duation, meta_fields, run, status
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                """
                
                doc_params = [
                    doc_id, create_time, current_date, create_time, current_date,  # ID和时间
                    None, kb_id, default_parser_id, default_parser_config, default_source_type,  # thumbnail到source_type
                    file_type, created_by, file_name, file_location, file_size,  # type到size
                    0, 0, 0.0, None, None,  # token_num到process_begin_at
                    0.0, None, '0', '1'  # process_duation到status
                ]
                
                cursor.execute(doc_query, doc_params)
                
                # 创建文件到文档的映射
                f2d_id = generate_uuid()
                f2d_query = """
                    INSERT INTO file2document (
                        id, create_time, create_date, update_time, update_date,
                        file_id, document_id
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s
                    )
                """
                
                f2d_params = [
                    f2d_id, create_time, current_date, create_time, current_date,
                    file_id, doc_id
                ]
                
                cursor.execute(f2d_query, f2d_params)
                
                added_count += 1
            
            # 更新知识库文档数量
            if added_count > 0:
                try:
                    update_query = """
                        UPDATE knowledgebase 
                        SET doc_num = doc_num + %s,
                            update_date = %s
                        WHERE id = %s
                    """
                    cursor.execute(update_query, (added_count, current_date, kb_id))
                    conn.commit()  # 先提交更新操作
                except Exception as e:
                    print(f"[WARNING] 更新知识库文档数量失败，但文档已添加: {str(e)}")
                    # 这里不抛出异常，因为文档已经添加成功
            
            cursor.close()
            conn.close()
            
            return {
                "added_count": added_count
            }
            
        except Exception as e:
            print(f"[ERROR] 添加文档失败: {str(e)}")
            print(f"[ERROR] 错误类型: {type(e)}")
            import traceback
            print(f"[ERROR] 堆栈信息: {traceback.format_exc()}")
            raise Exception(f"添加文档到知识库失败: {str(e)}")

    @classmethod
    def delete_document(cls, doc_id):
        """删除文档"""
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor()
            
            # 先检查文档是否存在
            check_query = "SELECT kb_id FROM document WHERE id = %s"
            cursor.execute(check_query, (doc_id,))
            result = cursor.fetchone()
            
            if not result:
                raise Exception("文档不存在")
                
            kb_id = result[0]
            
            # 删除文件到文档的映射
            f2d_query = "DELETE FROM file2document WHERE document_id = %s"
            cursor.execute(f2d_query, (doc_id,))
            
            # 删除文档
            doc_query = "DELETE FROM document WHERE id = %s"
            cursor.execute(doc_query, (doc_id,))
            
            # 更新知识库文档数量
            update_query = """
                UPDATE knowledgebase 
                SET doc_num = doc_num - 1,
                    update_date = %s
                WHERE id = %s
            """
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(update_query, (current_date, kb_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 删除文档失败: {str(e)}")
            raise Exception(f"删除文档失败: {str(e)}")

    @classmethod
    def parse_document(cls, doc_id, callback=None):
        """解析文档并提供进度反馈"""
        conn = None
        cursor = None
        try:
            # 获取文档信息
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 查询文档信息
            query = """
                SELECT d.id, d.name, d.location, d.type, d.kb_id, d.parser_id, d.parser_config
                FROM document d
                WHERE d.id = %s
            """
            cursor.execute(query, (doc_id,))
            doc = cursor.fetchone()
            
            if not doc:
                raise Exception("文档不存在")
            
            # 更新文档状态为处理中
            update_query = """
                UPDATE document 
                SET status = '2', run = '1', progress = 0.0, progress_msg = '开始解析'
                WHERE id = %s
            """
            cursor.execute(update_query, (doc_id,))
            conn.commit()

            # 获取文件ID和桶ID
            f2d_query = "SELECT file_id FROM file2document WHERE document_id = %s"
            cursor.execute(f2d_query, (doc_id,))
            f2d_result = cursor.fetchone()
            
            if not f2d_result:
                raise Exception("无法找到文件到文档的映射关系")
                
            file_id = f2d_result['file_id']
            
            file_query = "SELECT parent_id FROM file WHERE id = %s"
            cursor.execute(file_query, (file_id,))
            file_result = cursor.fetchone()
            
            if not file_result:
                raise Exception("无法找到文件记录")
                
            bucket_name = file_result['parent_id']
            
            # 创建 MinIO 客户端
            minio_client = get_minio_client()
            
            # 检查桶是否存在
            if not minio_client.bucket_exists(bucket_name):
                raise Exception(f"存储桶不存在: {bucket_name}")
            
            # 进度更新函数
            def update_progress(prog=None, msg=None):
                if prog is not None:
                    progress_query = "UPDATE document SET progress = %s WHERE id = %s"
                    cursor.execute(progress_query, (float(prog), doc_id))
                    conn.commit()
                
                if msg is not None:
                    msg_query = "UPDATE document SET progress_msg = %s WHERE id = %s"
                    cursor.execute(msg_query, (msg, doc_id))
                    conn.commit()
                
                if callback:
                    callback(prog, msg, doc_id)
            
            # 从 MinIO 获取文件内容
            file_location = doc['location']
            try:
                update_progress(0.1, f"正在从存储中获取文件: {file_location}")
                response = minio_client.get_object(bucket_name, file_location)
                file_content = response.read()
                response.close()
                update_progress(0.2, "文件获取成功，准备解析")
            except Exception as e:
                raise Exception(f"无法从存储中获取文件: {file_location}, 错误: {str(e)}")
            
            # 解析配置
            parser_config = json.loads(doc['parser_config']) if isinstance(doc['parser_config'], str) else doc['parser_config']
            
            # 根据文件类型选择解析器
            file_type = doc['type'].lower()
            chunks = []
            
            update_progress(0.2, "正在识别文档类型")
            
            # 使用magic_pdf进行解析
            if file_type.endswith('pdf'):
                update_progress(0.3, "使用Magic PDF解析器")
            
                # 创建临时文件保存PDF内容(路径：C:\Users\username\AppData\Local\Temp)
                temp_dir = tempfile.gettempdir()
                temp_pdf_path = os.path.join(temp_dir, f"{doc_id}.pdf")
                with open(temp_pdf_path, 'wb') as f:
                    f.write(file_content)
                
                try:
                    # 使用您的脚本中的方法处理PDF
                    def magic_callback(prog, msg):
                        # 将进度映射到20%-90%范围
                        actual_prog = 0.2 + prog * 0.7
                        update_progress(actual_prog, msg)
                    
                    # 初始化数据读取器
                    reader = FileBasedDataReader("")
                    pdf_bytes = reader.read(temp_pdf_path)
                    
                    # 创建PDF数据集实例
                    ds = PymuDocDataset(pdf_bytes)
                    
                    # 根据PDF类型选择处理方法
                    update_progress(0.3, "分析PDF类型")
                    if ds.classify() == SupportedPdfParseMethod.OCR:
                        update_progress(0.4, "使用OCR模式处理PDF")
                        infer_result = ds.apply(doc_analyze, ocr=True)
                        
                        # 设置临时输出目录
                        temp_image_dir = os.path.join(temp_dir, f"images_{doc_id}")
                        os.makedirs(temp_image_dir, exist_ok=True)
                        image_writer = FileBasedDataWriter(temp_image_dir)
                        
                        update_progress(0.6, "处理OCR结果")
                        pipe_result = infer_result.pipe_ocr_mode(image_writer)
                    else:
                        update_progress(0.4, "使用文本模式处理PDF")
                        infer_result = ds.apply(doc_analyze, ocr=False)
                        
                        # 设置临时输出目录
                        temp_image_dir = os.path.join(temp_dir, f"images_{doc_id}")
                        os.makedirs(temp_image_dir, exist_ok=True)
                        image_writer = FileBasedDataWriter(temp_image_dir)
                        
                        update_progress(0.6, "处理文本结果")
                        pipe_result = infer_result.pipe_txt_mode(image_writer)
                    
                    # 获取内容列表
                    update_progress(0.8, "提取内容")
                    content_list = pipe_result.get_content_list(os.path.basename(temp_image_dir))
                    
                    print(f"开始保存解析结果到MinIO，文档ID: {doc_id}")
                    # 处理内容列表
                    update_progress(0.95, "保存解析结果")
                    
                    # 获取或创建MinIO桶
                    kb_id = doc['kb_id']
                    minio_client = get_minio_client()
                    if not minio_client.bucket_exists(kb_id):
                        minio_client.make_bucket(kb_id)
                        print(f"创建MinIO桶: {kb_id}")

                    # 使用content_list而不是chunks变量
                    print(f"解析得到内容块数量: {len(content_list)}")
                    
                    # 处理内容列表并创建文档块
                    document_info = {
                        "doc_id": doc_id,
                        "doc_name": doc['name'],
                        "kb_id": kb_id
                    }
                    
                    # TODO: 对于块的预处理
                    # 合并内容块
                    # chunk_token_num = parser_config.get("chunk_token_num", 512)
                    # delimiter = parser_config.get("delimiter", "\n!?;。；！？")
                    # merged_chunks = merge_chunks(content_list, chunk_token_num, delimiter)
                    
                    # 处理文档块
                    # processed_chunks = process_document_chunks(merged_chunks, document_info)
                    
                    # 直接使用原始内容列表，不进行合并和处理
                    # processed_chunks = []
                    print(f"[DEBUG] 开始处理内容列表，共 {len(content_list)} 个原始内容块")
                    
                    # for i, content in enumerate(content_list):
                    #     if not content.strip():
                    #         continue
                            
                    #     chunk_data = document_info.copy()
                    #     chunk_data["content"] = content
                    #     chunk_data["tokens"] = tokenize_text(content)
                    #     processed_chunks.append(chunk_data)

                    print(f"[DEBUG] 开始上传到MinIO，目标桶: {kb_id}")
                    
    
                    # 处理内容块并上传到MinIO
                    chunk_count = 0
                    chunk_ids_list = []
                    for chunk_idx, chunk_data in enumerate(content_list):
                        if chunk_data["type"] == "text":
                            content = chunk_data["text"]
                            if not content.strip():
                                print(f"[DEBUG] 跳过空文本块 {chunk_idx}")
                                continue
                                
                            chunk_id = generate_uuid()
                            
                            try:
                                minio_client.put_object(
                                    bucket_name=kb_id,
                                    object_name=chunk_id,
                                    data=BytesIO(content.encode('utf-8')),
                                    length=len(content)
                                )
                                chunk_count += 1
                                chunk_ids_list.append(chunk_id)
                                print(f"成功上传文本块 {chunk_count}/{len(content_list)}")
                            except Exception as e:
                                print(f"上传文本块失败: {str(e)}")
                                continue
                                
                        elif chunk_data["type"] == "image":
                            print(f"[INFO] 跳过图像块处理: {chunk_data['img_path']}")
                            continue
                        
                    # 更新文档状态和块数量
                    final_update = """
                        UPDATE document
                        SET status = '1', run = '3', progress = 1.0, 
                            progress_msg = '解析完成', chunk_num = %s,
                            process_duation = %s
                        WHERE id = %s
                    """
                    cursor.execute(final_update, (chunk_count, 0.0, doc_id))
                    conn.commit()
                    print(f"[INFO] document表更新完成，文档ID: {doc_id}")

                    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # 更新知识库文档数量
                    kb_update = """
                        UPDATE knowledgebase 
                        SET chunk_num = chunk_num + %s,
                            update_date = %s
                        WHERE id = %s
                    """
                    cursor.execute(kb_update, (chunk_count, current_date, kb_id))
                    conn.commit()
                    print(f"[INFO] knowledgebase表更新完成，文档ID: {doc_id}")

                    # 生成task记录
                    task_id = generate_uuid()
                    # 获取当前时间
                    current_datetime = datetime.now()
                    current_timestamp = int(current_datetime.timestamp() * 1000)  # 毫秒级时间戳
                    current_time = current_datetime.strftime("%Y-%m-%d %H:%M:%S")  # 格式化日期时间
                    current_date_only = current_datetime.strftime("%Y-%m-%d")  # 仅日期
                    digest = f"{doc_id}_{0}_{1}"
                    
                    # 将chunk_ids列表转为JSON字符串
                    chunk_ids_str = ' '.join(chunk_ids_list)

                    task_insert = """
                        INSERT INTO task (
                            id, create_time, create_date, update_time, update_date,
                            doc_id, from_page, to_page, begin_at, process_duation,
                            progress, progress_msg, retry_count, digest, chunk_ids, task_type
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s
                        )
                    """
                    
                    task_params = [
                        task_id, current_timestamp, current_date_only, current_timestamp, current_date_only,
                        doc_id, 0, 1, None, 0.0,
                        1.0, "MinerU解析完成", 1, digest, chunk_ids_str, ""
                    ]
                             
                    cursor.execute(task_insert, task_params)
                    conn.commit()

                    update_progress(1.0, "解析完成")
                    print(f"[INFO] 解析完成，文档ID: {doc_id}")
                    cursor.close()
                    conn.close()

                    # 清理临时文件
                    try:
                        os.remove(temp_pdf_path)
                        shutil.rmtree(temp_image_dir, ignore_errors=True)
                    except:
                        pass
                    
                    return {
                        "success": True,
                        "chunk_count": chunk_count
                    }
                
                except Exception as e:
                    print(f"出现异常: {str(e)}")
   
        except Exception as e:
            print(f"文档解析失败: {str(e)}")
            # 更新文档状态为失败
            try:
                error_update = """
                    UPDATE document 
                    SET status = '1', run = '0', progress_msg = %s
                    WHERE id = %s
                """
                cursor.execute(error_update, (f"解析失败: {str(e)}", doc_id))
                conn.commit()
                cursor.close()
                conn.close()
            except:
                pass
                
            raise Exception(f"文档解析失败: {str(e)}")

    @classmethod
    def async_parse_document(cls, doc_id):
        """异步解析文档"""
        try:
            # 先立即返回响应，表示任务已开始
            thread = threading.Thread(target=cls.parse_document, args=(doc_id,))
            thread.daemon = True
            thread.start()
            
            return {
                "task_id": doc_id,
                "status": "processing",
                "message": "文档解析已开始"
            }
        except Exception as e:
            current_app.logger.error(f"启动解析任务失败: {str(e)}")
            raise Exception(f"启动解析任务失败: {str(e)}")

    @classmethod 
    def get_document_parse_progress(cls, doc_id):
        """获取文档解析进度 - 添加缓存机制"""
            
        # 正常数据库查询
        conn = cls._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT progress, progress_msg, status, run
            FROM document
            WHERE id = %s
        """
        cursor.execute(query, (doc_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not result:
            return {"error": "文档不存在"}
            
        
        return {
            "progress": float(result["progress"]),
            "message": result["progress_msg"],
            "status": result["status"],
            "running": result["run"] == "1"
        }
        """获取文档解析进度
        
        Args:
            doc_id: 文档ID
            
        Returns:
            解析进度信息
        """
        conn = cls._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT progress, progress_msg, status, run
            FROM document
            WHERE id = %s
        """
        cursor.execute(query, (doc_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not result:
            return {"error": "文档不存在"}
            
        return {
            "progress": float(result["progress"]),
            "message": result["progress_msg"],
            "status": result["status"],
            "running": result["run"] == "1"
        }