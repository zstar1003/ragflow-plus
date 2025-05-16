import os
import tempfile
import shutil
import json
from bs4 import BeautifulSoup
import mysql.connector
import time
import traceback
import re
import requests
from io import BytesIO
from datetime import datetime
from database import MINIO_CONFIG, DB_CONFIG, get_minio_client, get_es_client
from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod
from magic_pdf.data.read_api import read_local_office, read_local_images
from utils import generate_uuid


# 自定义tokenizer和文本处理函数，替代rag.nlp中的功能
def tokenize_text(text):
    """将文本分词，替代rag_tokenizer功能"""
    # 简单实现，未来可能需要改成更复杂的分词逻辑
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


def _get_db_connection():
    """创建数据库连接"""
    return mysql.connector.connect(**DB_CONFIG)


def _update_document_progress(doc_id, progress=None, message=None, status=None, run=None, chunk_count=None, process_duration=None):
    """更新数据库中文档的进度和状态"""
    conn = None
    cursor = None
    try:
        conn = _get_db_connection()
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
        print(f"[Parser-ERROR] 更新文档 {doc_id} 进度失败: {e}")
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
        conn = _get_db_connection()
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
        print(f"[Parser-ERROR] 更新知识库 {kb_id} 块数量失败: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def _create_task_record(doc_id, chunk_ids_list):
    """创建task记录"""
    conn = None
    cursor = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        task_id = generate_uuid()
        current_datetime = datetime.now()
        current_timestamp = int(current_datetime.timestamp() * 1000)
        current_date_only = current_datetime.strftime("%Y-%m-%d")
        digest = f"{doc_id}_{0}_{1}"  # 假设 from_page=0, to_page=1
        chunk_ids_str = " ".join(chunk_ids_list)

        task_insert = """
            INSERT INTO task (
                id, create_time, create_date, update_time, update_date,
                doc_id, from_page, to_page, begin_at, process_duation,
                progress, progress_msg, retry_count, digest, chunk_ids, task_type, priority
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        task_params = [
            task_id,
            current_timestamp,
            current_date_only,
            current_timestamp,
            current_date_only,
            doc_id,
            0,
            1,
            None,
            0.0,
            1.0,
            "MinerU解析完成",
            1,
            digest,
            chunk_ids_str,
            "", 
            0
        ]
        cursor.execute(task_insert, task_params)
        conn.commit()
        print(f"[Parser-INFO] Task记录创建成功，Task ID: {task_id}")
    except Exception as e:
        print(f"[Parser-ERROR] 创建Task记录失败: {e}")
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
            print(f"[Parser-WARNING] 块的 bbox 格式无效: {bbox}，将使用默认值。")
    # 如果 block 不是字典或没有 bbox 键，或 bbox 格式无效，返回默认值
    return [0, 0, 0, 0]


def process_table_content(content_list):
    """
    处理表格内容，将每一行分开存储
    
    Args:
        content_list: 原始内容列表
        
    Returns:
        处理后的内容列表
    """
    new_content_list = []
    
    for item in content_list:
        if 'table_body' in item and item['table_body']:
            # 使用BeautifulSoup解析HTML表格
            soup = BeautifulSoup(item['table_body'], 'html.parser')
            table = soup.find('table')
            
            if table:
                rows = table.find_all('tr')
                # 获取表头（第一行）
                header_row = rows[0] if rows else None
                
                # 处理每一行，从第二行开始（跳过表头）
                for i, row in enumerate(rows):
                    # 创建新的内容项
                    new_item = item.copy()
                    
                    # 创建只包含当前行的表格
                    new_table = soup.new_tag('table')
                    
                    # 如果有表头，添加表头
                    if header_row and i > 0:
                        new_table.append(header_row)
                    
                    # 添加当前行
                    new_table.append(row)
                    
                    # 创建新的HTML结构
                    new_html = f"<html><body>{str(new_table)}</body></html>"
                    new_item['table_body'] = f"\n\n{new_html}\n\n"
                    
                    # 添加到新的内容列表
                    new_content_list.append(new_item)
            else:
                new_content_list.append(item)
        else:
            new_content_list.append(item)
    
    return new_content_list

def perform_parse(doc_id, doc_info, file_info, embedding_config):
    """
    执行文档解析的核心逻辑

    Args:
        doc_id (str): 文档ID.
        doc_info (dict): 包含文档信息的字典 (name, location, type, kb_id, parser_config, created_by).
        file_info (dict): 包含文件信息的字典 (parent_id/bucket_name).

    Returns:
        dict: 包含解析结果的字典 (success, chunk_count).
    """
    temp_pdf_path = None
    temp_image_dir = None
    start_time = time.time()
    middle_json_content = None  # 初始化 middle_json_content
    image_info_list = []  # 图片信息列表

    # 默认值处理
    embedding_model_name = embedding_config.get("llm_name") if embedding_config and embedding_config.get("llm_name") else "bge-m3"  # 默认模型
    # 对模型名称进行处理
    if embedding_model_name and "___" in embedding_model_name:
        embedding_model_name = embedding_model_name.split("___")[0]

    # 替换特定模型名称(对硅基流动平台进行特异性处理)
    if embedding_model_name == "netease-youdao/bce-embedding-base_v1":
        embedding_model_name = "BAAI/bge-m3"

    embedding_api_base = embedding_config.get("api_base") if embedding_config and embedding_config.get("api_base") else "http://localhost:8000"  # 默认基础 URL

    # 如果 API 基础地址为空字符串，设置为硅基流动的 API 地址
    if embedding_api_base == "":
        embedding_api_base = "https://api.siliconflow.cn/v1/embeddings"
        print(f"[Parser-INFO] API 基础地址为空，已设置为硅基流动的 API 地址: {embedding_api_base}")

    embedding_api_key = embedding_config.get("api_key") if embedding_config else None  # 可能为 None 或空字符串

    # 构建完整的 Embedding API URL
    embedding_url = None  # 默认为 None
    if embedding_api_base:
        # 确保 embedding_api_base 包含协议头 (http:// 或 https://)
        if not embedding_api_base.startswith(("http://", "https://")):
            embedding_api_base = "http://" + embedding_api_base

        # --- URL 拼接优化 (处理 /v1) ---
        endpoint_segment = "embeddings"
        full_endpoint_path = "v1/embeddings"
        # 移除末尾斜杠以方便判断
        normalized_base_url = embedding_api_base.rstrip("/")

        if normalized_base_url.endswith("/v1"):
            # 如果 base_url 已经是 http://host/v1 形式
            embedding_url = normalized_base_url + "/" + endpoint_segment
        elif normalized_base_url.endswith('/embeddings'):
            # 如果 base_url 已经是 http://host/embeddings 形式(比如硅基流动API，无需再进行处理)
            embedding_url = normalized_base_url
        else:
            # 如果 base_url 是 http://host 或 http://host/api 等其他形式
            embedding_url = normalized_base_url + "/" + full_endpoint_path

    print(f"[Parser-INFO] 使用 Embedding 配置: URL='{embedding_url}', Model='{embedding_model_name}', Key={embedding_api_key}")

    try:
        kb_id = doc_info["kb_id"]
        file_location = doc_info["location"]
        # 从文件路径中提取原始后缀名
        _, file_extension = os.path.splitext(file_location)
        file_type = doc_info["type"].lower()
        bucket_name = file_info["parent_id"]  # 文件存储的桶是 parent_id
        tenant_id = doc_info["created_by"]  # 文档创建者作为 tenant_id

        # 进度更新回调 (直接调用内部更新函数)
        def update_progress(prog=None, msg=None):
            _update_document_progress(doc_id, progress=prog, message=msg)
            print(f"[Parser-PROGRESS] Doc: {doc_id}, Progress: {prog}, Message: {msg}")

        # 1. 从 MinIO 获取文件内容
        minio_client = get_minio_client()
        if not minio_client.bucket_exists(bucket_name):
            raise Exception(f"存储桶不存在: {bucket_name}")

        update_progress(0.1, f"正在从存储中获取文件: {file_location}")
        response = minio_client.get_object(bucket_name, file_location)
        file_content = response.read()
        response.close()
        update_progress(0.2, "文件获取成功，准备解析")

        # 2. 根据文件类型选择解析器
        content_list = []
        if file_type.endswith("pdf"):
            update_progress(0.3, "使用MinerU解析器")

            # 创建临时文件保存PDF内容
            temp_dir = tempfile.gettempdir()
            temp_pdf_path = os.path.join(temp_dir, f"{doc_id}.pdf")
            with open(temp_pdf_path, "wb") as f:
                f.write(file_content)

            # 使用MinerU处理
            reader = FileBasedDataReader("")
            pdf_bytes = reader.read(temp_pdf_path)
            ds = PymuDocDataset(pdf_bytes)

            update_progress(0.3, "分析PDF类型")
            is_ocr = ds.classify() == SupportedPdfParseMethod.OCR
            mode_msg = "OCR模式" if is_ocr else "文本模式"
            update_progress(0.4, f"使用{mode_msg}处理PDF")

            infer_result = ds.apply(doc_analyze, ocr=is_ocr)

            # 设置临时输出目录
            temp_image_dir = os.path.join(temp_dir, f"images_{doc_id}")
            os.makedirs(temp_image_dir, exist_ok=True)
            image_writer = FileBasedDataWriter(temp_image_dir)

            update_progress(0.6, f"处理{mode_msg}结果")
            pipe_result = infer_result.pipe_ocr_mode(image_writer) if is_ocr else infer_result.pipe_txt_mode(image_writer)

            update_progress(0.8, "提取内容")
            content_list = pipe_result.get_content_list(os.path.basename(temp_image_dir))
            # 获取内容列表（JSON格式）
            middle_content = pipe_result.get_middle_json()
            middle_json_content = json.loads(middle_content)

        elif file_type.endswith("word") or file_type.endswith("ppt") or file_type.endswith("txt") or file_type.endswith("md") or file_type.endswith("html"):
            update_progress(0.3, "使用MinerU解析器")
            # 创建临时文件保存文件内容
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, f"{doc_id}{file_extension}")
            with open(temp_file_path, "wb") as f:
                f.write(file_content)

            print(f"[Parser-INFO] 临时文件路径: {temp_file_path}")
            # 使用MinerU处理
            ds = read_local_office(temp_file_path)[0]
            infer_result = ds.apply(doc_analyze, ocr=True)

            # 设置临时输出目录
            temp_image_dir = os.path.join(temp_dir, f"images_{doc_id}")
            os.makedirs(temp_image_dir, exist_ok=True)
            image_writer = FileBasedDataWriter(temp_image_dir)

            update_progress(0.6, "处理文件结果")
            pipe_result = infer_result.pipe_txt_mode(image_writer)

            update_progress(0.8, "提取内容")
            content_list = pipe_result.get_content_list(os.path.basename(temp_image_dir))
            # 获取内容列表（JSON格式）
            middle_content = pipe_result.get_middle_json()
            middle_json_content = json.loads(middle_content)
        # 对excel文件单独进行处理
        elif file_type.endswith("excel") :
            update_progress(0.3, "使用MinerU解析器")
            # 创建临时文件保存文件内容
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, f"{doc_id}{file_extension}")
            with open(temp_file_path, "wb") as f:
                f.write(file_content)

            print(f"[Parser-INFO] 临时文件路径: {temp_file_path}")
            # 使用MinerU处理
            ds = read_local_office(temp_file_path)[0]
            infer_result = ds.apply(doc_analyze, ocr=True)

            # 设置临时输出目录
            temp_image_dir = os.path.join(temp_dir, f"images_{doc_id}")
            os.makedirs(temp_image_dir, exist_ok=True)
            image_writer = FileBasedDataWriter(temp_image_dir)

            update_progress(0.6, "处理文件结果")
            pipe_result = infer_result.pipe_txt_mode(image_writer)

            update_progress(0.8, "提取内容")
            origin_content_list = pipe_result.get_content_list(os.path.basename(temp_image_dir))
            # 处理内容列表
            content_list = process_table_content(origin_content_list)
        elif file_type.endswith("visual"):
            update_progress(0.3, "使用MinerU解析器")

            # 创建临时文件保存文件内容
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, f"{doc_id}{file_extension}")
            with open(temp_file_path, "wb") as f:
                f.write(file_content)

            print(f"[Parser-INFO] 临时文件路径: {temp_file_path}")
            # 使用MinerU处理
            ds = read_local_images(temp_file_path)[0]
            infer_result = ds.apply(doc_analyze, ocr=True)
            
            update_progress(0.3, "分析PDF类型")
            is_ocr = ds.classify() == SupportedPdfParseMethod.OCR
            mode_msg = "OCR模式" if is_ocr else "文本模式"
            update_progress(0.4, f"使用{mode_msg}处理PDF")

            infer_result = ds.apply(doc_analyze, ocr=is_ocr)

            # 设置临时输出目录
            temp_image_dir = os.path.join(temp_dir, f"images_{doc_id}")
            os.makedirs(temp_image_dir, exist_ok=True)
            image_writer = FileBasedDataWriter(temp_image_dir)

            update_progress(0.6, f"处理{mode_msg}结果")
            pipe_result = infer_result.pipe_ocr_mode(image_writer) if is_ocr else infer_result.pipe_txt_mode(image_writer)

            update_progress(0.8, "提取内容")
            content_list = pipe_result.get_content_list(os.path.basename(temp_image_dir))
            # 获取内容列表（JSON格式）
            middle_content = pipe_result.get_middle_json()
            middle_json_content = json.loads(middle_content)
        else:
            update_progress(0.3, f"暂不支持的文件类型: {file_type}")
            raise NotImplementedError(f"文件类型 '{file_type}' 的解析器尚未实现")

        # 解析 middle_json_content 并提取块信息
        block_info_list = []
        if middle_json_content:
            try:
                if isinstance(middle_json_content, dict):
                    middle_data = middle_json_content  # 直接赋值
                else:
                    middle_data = None
                    print(f"[Parser-WARNING] middle_json_content 不是预期的字典格式，实际类型: {type(middle_json_content)}。")
                # 提取信息
                for page_idx, page_data in enumerate(middle_data.get("pdf_info", [])):
                    for block in page_data.get("preproc_blocks", []):
                        block_bbox = get_bbox_from_block(block)
                        # 仅提取包含文本且有 bbox 的块
                        if block_bbox != [0, 0, 0, 0]:
                            block_info_list.append({"page_idx": page_idx, "bbox": block_bbox})
                        else:
                            print("[Parser-WARNING] 块的 bbox 格式无效，跳过。")

                    print(f"[Parser-INFO] 从 middle_data 提取了 {len(block_info_list)} 个块的信息。")

            except json.JSONDecodeError:
                print("[Parser-ERROR] 解析 middle_json_content 失败。")
                raise Exception("[Parser-ERROR] 解析 middle_json_content 失败。")
            except Exception as e:
                print(f"[Parser-ERROR] 处理 middle_json_content 时出错: {e}")
                raise Exception(f"[Parser-ERROR] 处理 middle_json_content 时出错: {e}")

        # 3. 处理解析结果 (上传到MinIO, 存储到ES)
        update_progress(0.95, "保存解析结果")
        es_client = get_es_client()
        # 注意：MinIO的桶应该是知识库ID (kb_id)，而不是文件的 parent_id
        output_bucket = kb_id
        if not minio_client.bucket_exists(output_bucket):
            minio_client.make_bucket(output_bucket)
            print(f"[Parser-INFO] 创建MinIO桶: {output_bucket}")

        index_name = f"ragflow_{tenant_id}"
        if not es_client.indices.exists(index=index_name):
            # 创建索引
            es_client.indices.create(
                index=index_name,
                body={
                    "settings": {"number_of_replicas": 0},
                    "mappings": {
                        "properties": {"doc_id": {"type": "keyword"}, "kb_id": {"type": "keyword"}, "content_with_weight": {"type": "text"}, "q_1024_vec": {"type": "dense_vector", "dims": 1024}}
                    },
                },
            )
            print(f"[Parser-INFO] 创建Elasticsearch索引: {index_name}")

        chunk_count = 0
        chunk_ids_list = []

        for chunk_idx, chunk_data in enumerate(content_list):
            page_idx = 0  # 默认页面索引
            bbox = [0, 0, 0, 0]  # 默认 bbox

            # 尝试使用 chunk_idx 直接从 block_info_list 获取对应的块信息
            if chunk_idx < len(block_info_list):
                block_info = block_info_list[chunk_idx]
                page_idx = block_info.get("page_idx", 0)
                bbox = block_info.get("bbox", [0, 0, 0, 0])
                # 验证 bbox 是否有效，如果无效则重置为默认值 (可选，取决于是否需要严格验证)
                if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(n, (int, float)) for n in bbox)):
                    print(f"[Parser-WARNING] Chunk {chunk_idx} 对应的 bbox 格式无效: {bbox}，将使用默认值。")
                    bbox = [0, 0, 0, 0]
            else:
                # 如果 block_info_list 的长度小于 content_list，打印警告
                # 仅在第一次索引越界时打印一次警告，避免刷屏
                if chunk_idx == len(block_info_list):
                    print(f"[Parser-WARNING] block_info_list 的长度 ({len(block_info_list)}) 小于 content_list 的长度 ({len(content_list)})。后续块将使用默认 page_idx 和 bbox。")

            if chunk_data["type"] == "text" or chunk_data["type"] == "table":
                if chunk_data["type"] == "text":
                    content = chunk_data["text"]
                    if not content or not content.strip():
                        continue
                    # 过滤 markdown 特殊符号
                    content = re.sub(r"[!#\\$/]", "", content)
                elif chunk_data["type"] == "table":
                    caption_list = chunk_data.get("table_caption", [])  # 获取列表，默认为空列表
                    table_body = chunk_data.get("table_body", "")  # 获取表格主体，默认为空字符串
                    # 检查 caption_list 是否为列表，并且包含字符串元素
                    if isinstance(caption_list, list) and all(isinstance(item, str) for item in caption_list):
                        # 使用空格将列表中的所有字符串拼接起来
                        caption_str = " ".join(caption_list)
                    elif isinstance(caption_list, str):
                        # 如果 caption 本身就是字符串，直接使用
                        caption_str = caption_list
                    else:
                        # 其他情况（如空列表、None 或非字符串列表），使用空字符串
                        caption_str = ""
                    # 将处理后的标题字符串和表格主体拼接
                    content = caption_str + table_body

                q_1024_vec = []  # 初始化为空列表
                # 获取embedding向量
                try:
                    # embedding_resp = requests.post(
                    #     "http://localhost:8000/v1/embeddings",
                    #     json={
                    #         "model": "bge-m3",  # 你的embedding模型名
                    #         "input": content
                    #     },
                    #     timeout=10
                    # )
                    headers = {"Content-Type": "application/json"}
                    if embedding_api_key:
                        headers["Authorization"] = f"Bearer {embedding_api_key}"

                    embedding_resp = requests.post(
                        embedding_url,  # 使用动态构建的 URL
                        headers=headers,  # 添加 headers (包含可能的 API Key)
                        json={
                            "model": embedding_model_name,  # 使用动态获取或默认的模型名
                            "input": content,
                        },
                        timeout=15,  # 稍微增加超时时间
                    )

                    embedding_resp.raise_for_status()
                    embedding_data = embedding_resp.json()
                    q_1024_vec = embedding_data["data"][0]["embedding"]
                    print(f"[Parser-INFO] 获取embedding成功，长度: {len(q_1024_vec)}")
                    # 检查向量维度是否为1024
                    if len(q_1024_vec) != 1024:
                        error_msg = f"[Parser-ERROR] Embedding向量维度不是1024，实际维度: {len(q_1024_vec)}, 建议使用bge-m3模型"
                        print(error_msg)
                        update_progress(-1, error_msg)
                        raise ValueError(error_msg)
                except Exception as e:
                    print(f"[Parser-ERROR] 获取embedding失败: {e}")
                    raise Exception(f"[Parser-ERROR] 获取embedding失败: {e}")

                chunk_id = generate_uuid()

                try:
                    # 上传文本块到 MinIO
                    minio_client.put_object(
                        bucket_name=output_bucket,
                        object_name=chunk_id,
                        data=BytesIO(content.encode("utf-8")),
                        length=len(content.encode("utf-8")),  # 使用字节长度
                    )

                    # 准备ES文档
                    content_tokens = tokenize_text(content)  # 分词
                    current_time_es = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    current_timestamp_es = datetime.now().timestamp()

                    # 转换坐标格式
                    x1, y1, x2, y2 = bbox
                    bbox_reordered = [x1, x2, y1, y2]

                    es_doc = {
                        "doc_id": doc_id,
                        "kb_id": kb_id,
                        "docnm_kwd": doc_info["name"],
                        "title_tks": doc_info["name"],
                        "title_sm_tks": doc_info["name"],
                        "content_with_weight": content,
                        "content_ltks": " ".join(content_tokens),  # 字符串类型
                        "content_sm_ltks": " ".join(content_tokens),  # 字符串类型
                        "page_num_int": [page_idx + 1],
                        "position_int": [[page_idx + 1] + bbox_reordered],  # 格式: [[page, x1, x2, y1, y2]]
                        "top_int": [1],
                        "create_time": current_time_es,
                        "create_timestamp_flt": current_timestamp_es,
                        "img_id": "",
                        "q_1024_vec": q_1024_vec,
                    }

                    # 存储到Elasticsearch
                    es_client.index(index=index_name, id=chunk_id, document=es_doc)  # 使用 document 参数

                    chunk_count += 1
                    chunk_ids_list.append(chunk_id)

                except Exception as e:
                    print(f"[Parser-ERROR] 处理文本块 {chunk_idx} (page: {page_idx}, bbox: {bbox}) 失败: {e}")
                    traceback.print_exc()  # 打印更详细的错误
                    raise Exception(f"[Parser-ERROR] 处理文本块 {chunk_idx} (page: {page_idx}, bbox: {bbox}) 失败: {e}")

            elif chunk_data["type"] == "image":
                img_path_relative = chunk_data.get("img_path")
                if not img_path_relative or not temp_image_dir:
                    continue

                img_path_abs = os.path.join(temp_image_dir, os.path.basename(img_path_relative))
                if not os.path.exists(img_path_abs):
                    print(f"[Parser-WARNING] 图片文件不存在: {img_path_abs}")
                    continue

                img_id = generate_uuid()
                img_ext = os.path.splitext(img_path_abs)[1]
                img_key = f"images/{img_id}{img_ext}"  # MinIO中的对象名
                content_type = f"image/{img_ext[1:].lower()}"
                if content_type == "image/jpg":
                    content_type = "image/jpeg"

                try:
                    # 上传图片到MinIO (桶为kb_id)
                    minio_client.fput_object(bucket_name=output_bucket, object_name=img_key, file_path=img_path_abs, content_type=content_type)

                    # 设置图片的公共访问权限
                    policy = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"AWS": "*"}, "Action": ["s3:GetObject"], "Resource": [f"arn:aws:s3:::{kb_id}/images/*"]}]}
                    minio_client.set_bucket_policy(kb_id, json.dumps(policy))

                    print(f"成功上传图片: {img_key}")
                    minio_endpoint = MINIO_CONFIG["endpoint"]
                    use_ssl = MINIO_CONFIG.get("secure", False)
                    protocol = "https" if use_ssl else "http"
                    img_url = f"{protocol}://{minio_endpoint}/{output_bucket}/{img_key}"

                    # 记录图片信息，包括URL和位置信息
                    image_info = {
                        "url": img_url,
                        "position": chunk_count,  # 使用当前处理的文本块数作为位置参考
                    }
                    image_info_list.append(image_info)

                    print(f"图片访问链接: {img_url}")

                except Exception as e:
                    print(f"[Parser-ERROR] 上传图片 {img_path_abs} 失败: {e}")
                    raise Exception(f"[Parser-ERROR] 上传图片 {img_path_abs} 失败: {e}")

        # 打印匹配总结信息
        print(f"[Parser-INFO] 共处理 {chunk_count} 个文本块。")

        # 4. 更新文本块的图像信息
        if image_info_list and chunk_ids_list:
            conn = None
            cursor = None
            try:
                conn = _get_db_connection()
                cursor = conn.cursor()

                # 为每个文本块找到最近的图片
                for i, chunk_id in enumerate(chunk_ids_list):
                    # 找到与当前文本块最近的图片
                    nearest_image = None

                    for img_info in image_info_list:
                        # 计算文本块与图片的"距离"
                        distance = abs(i - img_info["position"])  # 使用位置差作为距离度量
                        # 如果文本块与图片的距离间隔小于10个块,则认为块与图片是相关的
                        if distance < 10:
                            nearest_image = img_info

                    # 如果找到了最近的图片，则更新文本块的img_id
                    if nearest_image:
                        # 更新ES中的文档
                        direct_update = {"doc": {"img_id": nearest_image["url"]}}
                        es_client.update(index=index_name, id=chunk_id, body=direct_update, refresh=True)

                        index_name = f"ragflow_{tenant_id}"

                        print(f"[Parser-INFO] 更新文本块 {chunk_id} 的图片关联: {nearest_image['url']}")

            except Exception as e:
                print(f"[Parser-ERROR] 更新文本块图片关联失败: {e}")
                raise Exception(f"[Parser-ERROR] 更新文本块图片关联失败: {e}")
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

        # 5. 更新最终状态
        process_duration = time.time() - start_time
        _update_document_progress(doc_id, progress=1.0, message="解析完成", status="1", run="3", chunk_count=chunk_count, process_duration=process_duration)
        _update_kb_chunk_count(kb_id, chunk_count)  # 更新知识库总块数
        _create_task_record(doc_id, chunk_ids_list)  # 创建task记录

        update_progress(1.0, "解析完成")
        print(f"[Parser-INFO] 解析完成，文档ID: {doc_id}, 耗时: {process_duration:.2f}s, 块数: {chunk_count}")

        return {"success": True, "chunk_count": chunk_count}

    except Exception as e:
        process_duration = time.time() - start_time
        # error_message = f"解析失败: {str(e)}"
        print(f"[Parser-ERROR] 文档 {doc_id} 解析失败: {e}")
        error_message = f"解析失败: {e}"
        traceback.print_exc()  # 打印详细错误堆栈
        # 更新文档状态为失败
        _update_document_progress(doc_id, status="1", run="0", message=error_message, process_duration=process_duration)  # status=1表示完成，run=0表示失败
        # 不抛出异常，让调用者知道任务已结束（但失败）
        return {"success": False, "error": error_message}

    finally:
        # 清理临时文件
        try:
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            if temp_image_dir and os.path.exists(temp_image_dir):
                shutil.rmtree(temp_image_dir, ignore_errors=True)
        except Exception as clean_e:
            print(f"[Parser-WARNING] 清理临时文件失败: {clean_e}")
