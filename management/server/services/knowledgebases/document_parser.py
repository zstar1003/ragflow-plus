#  Copyright 2025 zstar1003. All Rights Reserved.
#  Project source code: https://github.com/zstar1003/ragflow-plus

import json
import os
import re
import shutil
import tempfile
import time
from datetime import datetime
from urllib.parse import urlparse

import requests
from database import MINIO_CONFIG, get_db_connection, get_es_client, get_minio_client
from magic_pdf.config.enums import SupportedPdfParseMethod
from magic_pdf.data.data_reader_writer import FileBasedDataReader, FileBasedDataWriter
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.data.read_api import read_local_images, read_local_office
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze

from . import logger
from .excel_parser import parse_excel_file
from .rag_tokenizer import RagTokenizer
from .utils import _create_task_record, _update_document_progress, _update_kb_chunk_count, generate_uuid, get_bbox_from_block

tknzr = RagTokenizer()


def tokenize_text(text):
    """使用分词器对文本进行分词"""
    return tknzr.tokenize(text)


def perform_parse(doc_id, doc_info, file_info, embedding_config, kb_info):
    """
    执行文档解析的核心逻辑

    Args:
        doc_id (str): 文档ID.
        doc_info (dict): 包含文档信息的字典 (name, location, type, kb_id, parser_config, created_by).
        file_info (dict): 包含文件信息的字典 (parent_id/bucket_name).
        kb_info (dict): 包含知识库信息的字典 (created_by).

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

    embedding_api_base = embedding_config.get("api_base") if embedding_config and embedding_config.get("api_base") else "http://localhost:11434"  # 默认基础 URL

    # 如果 API 基础地址为空字符串，设置为硅基流动的 API 地址
    if embedding_api_base == "":
        embedding_api_base = "https://api.siliconflow.cn/v1/embeddings"
        logger.info(f"[Parser-INFO] API 基础地址为空，已设置为硅基流动的 API 地址: {embedding_api_base}")

    embedding_api_key = embedding_config.get("api_key") if embedding_config else None  # 可能为 None 或空字符串

    # 构建完整的 Embedding API URL
    embedding_url = None  # 默认为 None
    if embedding_api_base:
        # 确保 embedding_api_base 包含协议头 (http:// 或 https://)
        if not embedding_api_base.startswith(("http://", "https://")):
            embedding_api_base = "http://" + embedding_api_base

        # 移除末尾斜杠以方便判断
        normalized_base_url = embedding_api_base.rstrip("/")

        # 如果请求url端口号为11434，则认为是ollama模型，采用ollama特定的api
        is_ollama = "11434" in normalized_base_url
        if is_ollama:
            # Ollama 的特殊接口路径
            embedding_url = normalized_base_url + "/api/embeddings"
        elif normalized_base_url.endswith("/v1"):
            embedding_url = normalized_base_url + "/embeddings"
        elif normalized_base_url.endswith("/embeddings"):
            embedding_url = normalized_base_url
        else:
            embedding_url = normalized_base_url + "/v1/embeddings"

    logger.info(f"[Parser-INFO] 使用 Embedding 配置: URL='{embedding_url}', Model='{embedding_model_name}', Key={embedding_api_key}")

    try:
        kb_id = doc_info["kb_id"]
        file_location = doc_info["location"]
        # 从文件路径中提取原始后缀名
        _, file_extension = os.path.splitext(file_location)
        file_type = doc_info["type"].lower()
        bucket_name = file_info["parent_id"]  # 文件存储的桶是 parent_id
        tenant_id = kb_info["created_by"]  # 知识库创建者作为 tenant_id

        # 进度更新回调 (直接调用内部更新函数)
        def update_progress(prog=None, msg=None):
            _update_document_progress(doc_id, progress=prog, message=msg)
            logger.info(f"[Parser-PROGRESS] Doc: {doc_id}, Progress: {prog}, Message: {msg}")

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
            update_progress(0.4, f"使用{mode_msg}处理PDF，处理中，具体进度可查看容器日志")

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

            logger.info(f"[Parser-INFO] 临时文件路径: {temp_file_path}")
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
        elif file_type.endswith("excel"):
            update_progress(0.3, "使用MinerU解析器")
            # 创建临时文件保存文件内容
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, f"{doc_id}{file_extension}")
            with open(temp_file_path, "wb") as f:
                f.write(file_content)

            logger.info(f"[Parser-INFO] 临时文件路径: {temp_file_path}")

            update_progress(0.8, "提取内容")
            # 处理内容列表
            content_list = parse_excel_file(temp_file_path)

        elif file_type.endswith("visual"):
            update_progress(0.3, "使用MinerU解析器")

            # 创建临时文件保存文件内容
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, f"{doc_id}{file_extension}")
            with open(temp_file_path, "wb") as f:
                f.write(file_content)

            logger.info(f"[Parser-INFO] 临时文件路径: {temp_file_path}")
            # 使用MinerU处理
            ds = read_local_images(temp_file_path)[0]
            infer_result = ds.apply(doc_analyze, ocr=True)

            update_progress(0.3, "分析PDF类型")
            is_ocr = ds.classify() == SupportedPdfParseMethod.OCR
            mode_msg = "OCR模式" if is_ocr else "文本模式"
            update_progress(0.4, f"使用{mode_msg}处理PDF，处理中，具体进度可查看日志")

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
                    logger.warning(f"[Parser-WARNING] middle_json_content 不是预期的字典格式，实际类型: {type(middle_json_content)}。")
                # 提取信息
                for page_idx, page_data in enumerate(middle_data.get("pdf_info", [])):
                    for block in page_data.get("preproc_blocks", []):
                        block_bbox = get_bbox_from_block(block)
                        # 仅提取包含文本且有 bbox 的块
                        if block_bbox != [0, 0, 0, 0]:
                            block_info_list.append({"page_idx": page_idx, "bbox": block_bbox})
                        else:
                            logger.warning("[Parser-WARNING] 块的 bbox 格式无效，跳过。")

                    logger.info(f"[Parser-INFO] 从 middle_data 提取了 {len(block_info_list)} 个块的信息。")

            except json.JSONDecodeError:
                logger.error("[Parser-ERROR] 解析 middle_json_content 失败。")
                raise Exception("[Parser-ERROR] 解析 middle_json_content 失败。")
            except Exception as e:
                logger.error(f"[Parser-ERROR] 处理 middle_json_content 时出错: {e}")
                raise Exception(f"[Parser-ERROR] 处理 middle_json_content 时出错: {e}")

        # 3. 处理解析结果 (上传到MinIO, 存储到ES)
        update_progress(0.95, "保存解析结果")
        es_client = get_es_client()
        # 注意：MinIO的桶应该是知识库ID (kb_id)，而不是文件的 parent_id
        output_bucket = kb_id
        if not minio_client.bucket_exists(output_bucket):
            minio_client.make_bucket(output_bucket)
            logger.info(f"[Parser-INFO] 创建MinIO桶: {output_bucket}")

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
            logger.info(f"[Parser-INFO] 创建Elasticsearch索引: {index_name}")

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
                    logger.info(f"[Parser-WARNING] Chunk {chunk_idx} 对应的 bbox 格式无效: {bbox}，将使用默认值。")
                    bbox = [0, 0, 0, 0]
            else:
                # 如果 block_info_list 的长度小于 content_list，打印警告
                # 仅在第一次索引越界时打印一次警告，避免刷屏
                if chunk_idx == len(block_info_list):
                    logger.warning(f"[Parser-WARNING] block_info_list 的长度 ({len(block_info_list)}) 小于 content_list 的长度 ({len(content_list)})。后续块将使用默认 page_idx 和 bbox。")

            if chunk_data["type"] == "text" or chunk_data["type"] == "table" or chunk_data["type"] == "equation":
                if chunk_data["type"] == "text":
                    content = chunk_data["text"]
                    if not content or not content.strip():
                        continue
                    # 过滤 markdown 特殊符号
                    content = re.sub(r"[!#\\$/]", "", content)
                elif chunk_data["type"] == "equation":
                    content = chunk_data["text"]
                    if not content or not content.strip():
                        continue
                elif chunk_data["type"] == "table":
                    caption_list = chunk_data.get("table_caption", [])  # 获取列表，默认为空列表
                    table_body = chunk_data.get("table_body", "")  # 获取表格主体，默认为空字符串

                    # 如果表格主体为空，说明无实际内容，跳过该表格块
                    if not table_body.strip():
                        continue

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

                    if is_ollama:
                        embedding_resp = requests.post(
                            embedding_url,  # 使用动态构建的 URL
                            headers=headers,  # 添加 headers (包含可能的 API Key)
                            json={
                                "model": embedding_model_name,  # 使用动态获取或默认的模型名
                                "prompt": content,
                            },
                            timeout=15,  # 稍微增加超时时间
                        )
                    else:
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

                    # 对ollama嵌入模型的接口返回值进行特殊处理
                    if is_ollama:
                        q_1024_vec = embedding_data.get("embedding")
                    else:
                        q_1024_vec = embedding_data["data"][0]["embedding"]
                    # logger.info(f"[Parser-INFO] 获取embedding成功，长度: {len(q_1024_vec)}")

                    # 检查向量维度是否为1024
                    if len(q_1024_vec) != 1024:
                        error_msg = f"[Parser-ERROR] Embedding向量维度不是1024，实际维度: {len(q_1024_vec)}, 建议使用bge-m3模型"
                        logger.error(error_msg)
                        update_progress(-5, error_msg)
                        raise ValueError(error_msg)
                except Exception as e:
                    logger.error(f"[Parser-ERROR] 获取embedding失败: {e}")
                    raise Exception(f"[Parser-ERROR] 获取embedding失败: {e}")

                chunk_id = generate_uuid()

                try:
                    # 准备ES文档
                    current_time_es = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    current_timestamp_es = datetime.now().timestamp()

                    # 转换坐标格式
                    x1, y1, x2, y2 = bbox
                    bbox_reordered = [x1, x2, y1, y2]

                    es_doc = {
                        "doc_id": doc_id,
                        "kb_id": kb_id,
                        "docnm_kwd": doc_info["name"],
                        "title_tks": tokenize_text(doc_info["name"]),
                        "title_sm_tks": tokenize_text(doc_info["name"]),
                        "content_with_weight": content,
                        "content_ltks": tokenize_text(content),
                        "content_sm_ltks": tokenize_text(content),
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
                    logger.error(f"[Parser-ERROR] 处理文本块 {chunk_idx} (page: {page_idx}, bbox: {bbox}) 失败: {e}")
                    raise Exception(f"[Parser-ERROR] 处理文本块 {chunk_idx} (page: {page_idx}, bbox: {bbox}) 失败: {e}")

            elif chunk_data["type"] == "image":
                img_path_relative = chunk_data.get("img_path")
                if not img_path_relative or not temp_image_dir:
                    continue

                img_path_abs = os.path.join(temp_image_dir, os.path.basename(img_path_relative))
                if not os.path.exists(img_path_abs):
                    logger.warning(f"[Parser-WARNING] 图片文件不存在: {img_path_abs}")
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

                    logger.info(f"成功上传图片: {img_key}")
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

                    logger.info(f"图片访问链接: {img_url}")

                except Exception as e:
                    logger.error(f"[Parser-ERROR] 上传图片 {img_path_abs} 失败: {e}")
                    raise Exception(f"[Parser-ERROR] 上传图片 {img_path_abs} 失败: {e}")

        # 打印匹配总结信息
        logger.info(f"[Parser-INFO] 共处理 {chunk_count} 个文本块。")

        # 4. 更新文本块的图像信息
        if image_info_list and chunk_ids_list:
            conn = None
            cursor = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                # 为每个文本块找到最近的图片
                for i, chunk_id in enumerate(chunk_ids_list):
                    # 找到与当前文本块最近的图片
                    nearest_image = None

                    for img_info in image_info_list:
                        # 计算文本块与图片的"距离"
                        distance = abs(i - img_info["position"])  # 使用位置差作为距离度量
                        # 如果文本块与图片的距离间隔小于5个块,则认为块与图片是相关的
                        if distance < 5:
                            nearest_image = img_info

                    # 如果找到了最近的图片，则更新文本块的img_id
                    if nearest_image:
                        # 存储相对路径部分
                        parsed_url = urlparse(nearest_image["url"])
                        relative_path = parsed_url.path.lstrip("/")  # 去掉开头的斜杠
                        # 更新ES中的文档
                        direct_update = {"doc": {"img_id": relative_path}}
                        es_client.update(index=index_name, id=chunk_id, body=direct_update, refresh=True)
                        index_name = f"ragflow_{tenant_id}"
                        logger.info(f"[Parser-INFO] 更新文本块 {chunk_id} 的图片关联: {relative_path}")

            except Exception as e:
                logger.error(f"[Parser-ERROR] 更新文本块图片关联失败: {e}")
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
        logger.info(f"[Parser-INFO] 解析完成，文档ID: {doc_id}, 耗时: {process_duration:.2f}s, 块数: {chunk_count}")

        return {"success": True, "chunk_count": chunk_count}

    except Exception as e:
        process_duration = time.time() - start_time
        # error_message = f"解析失败: {str(e)}"
        logger.error(f"[Parser-ERROR] 文档 {doc_id} 解析失败: {e}")
        error_message = f"解析失败: {e}"
        # 更新文档状态为失败
        _update_document_progress(doc_id, status="1", run="0", message=error_message, process_duration=process_duration)  # status=1表示完成，run=0表示失败
        return {"success": False, "error": error_message}

    finally:
        # 清理临时文件
        try:
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            if temp_image_dir and os.path.exists(temp_image_dir):
                shutil.rmtree(temp_image_dir, ignore_errors=True)
        except Exception as clean_e:
            logger.error(f"[Parser-WARNING] 清理临时文件失败: {clean_e}")
