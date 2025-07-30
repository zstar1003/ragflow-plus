import json
import os
import tempfile
import time
from datetime import datetime

from werkzeug.utils import secure_filename

from api import settings
from api.db import LLMType, ParserType
from api.db.services.database import get_minio_client
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMBundle
from rag.app.tag import label_question
from rag.prompts import kb_prompt

from .database import MINIO_CONFIG


def write_dialog(question, kb_ids, tenant_id, similarity_threshold, keyword_similarity_weight, temperature):
    """
    处理用户搜索请求，从知识库中检索相关信息并生成回答

    参数:
        question (str): 用户的问题或查询
        kb_ids (list): 知识库ID列表，指定要搜索的知识库，可以为空
        tenant_id (str): 租户ID，用于权限控制和资源隔离

    流程:
        1. 检查是否有知识库ID
        2. 如果有知识库，执行知识库检索流程
        3. 如果没有知识库，直接使用聊天模型回答
        4. 流式返回生成的回答

    返回:
        generator: 生成器对象，产生包含回答和引用信息的字典
    """
    
    # 初始化聊天模型，用于生成回答
    chat_mdl = LLMBundle(tenant_id, LLMType.CHAT)
    
    # 如果没有提供知识库ID或知识库ID为空，直接使用聊天模型回答
    if not kb_ids or len(kb_ids) == 0:
        prompt = """
        角色：你是一个聪明的助手。  
        任务：回答用户的问题。  
        要求与限制：
        - 使用Markdown格式进行回答。
        - 使用用户提问所用的语言作答。
        - 基于你的知识回答问题，如果不确定请说明。
        """
        msg = [{"role": "user", "content": question}]
        
        answer = ""
        final_answer = ""
        for ans in chat_mdl.chat_streamly(prompt, msg, {"temperature": temperature}):
            answer = ans
            final_answer = answer
            yield {"answer": answer, "reference": {}}
        
        time.sleep(0.1)  # 增加延迟，确保缓冲区 flush 出去
        return

    # 如果有知识库ID，执行原有的知识库检索流程
    kbs = KnowledgebaseService.get_by_ids(kb_ids)
    embedding_list = list(set([kb.embd_id for kb in kbs]))

    is_knowledge_graph = all([kb.parser_id == ParserType.KG for kb in kbs])
    retriever = settings.retrievaler if not is_knowledge_graph else settings.kg_retrievaler
    # 初始化嵌入模型，用于将文本转换为向量表示
    embd_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING, embedding_list[0])
    # 获取聊天模型的最大token长度，用于控制上下文长度
    max_tokens = chat_mdl.max_length
    # 获取所有知识库的租户ID并去重
    tenant_ids = list(set([kb.tenant_id for kb in kbs]))
    # 调用检索器检索相关文档片段
    kbinfos = retriever.retrieval(question, embd_mdl, tenant_ids, kb_ids, 1, 12, similarity_threshold, 1 - keyword_similarity_weight, aggs=False, rank_feature=label_question(question, kbs))
    # 将检索结果格式化为提示词，并确保不超过模型最大token限制
    knowledges = kb_prompt(kbinfos, max_tokens)

    prompt = """
    角色：你是一个聪明的助手。  
    任务：总结知识库中的信息并回答用户的问题。  
    要求与限制：
    - 绝不要捏造内容，尤其是数字。
    - 如果知识库中的信息与用户问题无关，只需回答：对不起，未提供相关信息。
    - 使用Markdown格式进行回答。
    - 使用用户提问所用的语言作答。
    - 绝不要捏造内容，尤其是数字。

    ### 来自知识库的信息
    %s

    以上是来自知识库的信息。

    """ % "\n".join(knowledges)
    msg = [{"role": "user", "content": question}]

    answer = ""
    final_answer = ""
    for ans in chat_mdl.chat_streamly(prompt, msg, {"temperature": temperature}):
        answer = ans
        final_answer = answer
        yield {"answer": answer, "reference": {}}

    # 流式返回完毕后，追加图片
    image_markdowns = []
    image_urls = set()
    minio_endpoint = MINIO_CONFIG["visit_point"]
    use_ssl = MINIO_CONFIG.get("secure", False)
    protocol = "https" if use_ssl else "http"

    for chunk in kbinfos["chunks"]:
        img_path = chunk.get("image_id")
        if not img_path:
            continue

        img_path = img_path.strip()  # 清理前后空格
        img_url = f"{protocol}://{minio_endpoint}/{img_path}"

        if img_url not in image_urls:
            image_urls.add(img_url)
            image_markdowns.append(f'\n<img src="{img_url}" alt="{img_url}" style="max-width:500px; display:block; margin:auto;">')

    if image_markdowns:
        final_answer += "".join(image_markdowns)
        yield {"answer": final_answer, "reference": {}}

    time.sleep(0.1)  # 增加延迟，确保缓冲区 flush 出去


def upload_image(file_storage):
    allowed_exts = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed_exts:
        return None, "不支持的图片格式"

    # 生成唯一文件名，防止覆盖
    now = datetime.now().strftime("%Y%m%d%H%M%S%f")
    unique_filename = f"{now}_{filename}"

    # 保存到临时目录
    temp_dir = tempfile.gettempdir()
    temp_image_dir = os.path.join(temp_dir, "images_temp")
    os.makedirs(temp_image_dir, exist_ok=True)
    temp_path = os.path.join(temp_image_dir, unique_filename)
    file_storage.save(temp_path)

    # 上传到MinIO的public桶
    minio_client = get_minio_client()
    bucket_name = "public"
    object_name = f"images/{unique_filename}"

    # 确保bucket存在
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)

    # 获取文件扩展名和内容类型
    img_ext = os.path.splitext(unique_filename)[1]
    content_type = f"image/{img_ext[1:].lower()}"
    if content_type == "image/jpg":
        content_type = "image/jpeg"

    # 上传图片到MinIO的public桶
    minio_client.fput_object(bucket_name=bucket_name, object_name=object_name, file_path=temp_path, content_type=content_type)

    # 设置图片的公共访问权限
    policy = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"AWS": "*"}, "Action": ["s3:GetObject"], "Resource": [f"arn:aws:s3:::{bucket_name}/images/*"]}]}
    minio_client.set_bucket_policy(bucket_name, json.dumps(policy))

    # 删除本地临时文件
    os.remove(temp_path)

    # 构造可访问URL
    minio_endpoint = MINIO_CONFIG.get("visit_point", MINIO_CONFIG["endpoint"])
    use_ssl = MINIO_CONFIG.get("secure", False)
    protocol = "https" if use_ssl else "http"
    url = f"{protocol}://{minio_endpoint}/{bucket_name}/{object_name}"

    print(f"图片访问链接: {url}")
    return url, None
