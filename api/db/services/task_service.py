#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import os
import random
import xxhash
from datetime import datetime

from api.db.db_utils import bulk_insert_into_db
from peewee import JOIN
from api.db.db_models import DB, File2Document, File
from api.db import StatusEnum, FileType, TaskStatus
from api.db.db_models import Task, Document, Knowledgebase, Tenant
from api.db.services.common_service import CommonService
from api.db.services.document_service import DocumentService
from api.utils import current_timestamp, get_uuid
from rag.settings import SVR_QUEUE_NAME
from rag.utils.storage_factory import STORAGE_IMPL
from rag.utils.redis_conn import REDIS_CONN
from api import settings
from rag.nlp import search


def trim_header_by_lines(text: str, max_length) -> str:
    len_text = len(text)
    if len_text <= max_length:
        return text
    for i in range(len_text):
        if text[i] == "\n" and len_text - i <= max_length:
            return text[i + 1 :]
    return text


class TaskService(CommonService):
    model = Task

    @classmethod
    @DB.connection_context()
    def get_task(cls, task_id):
        fields = [
            cls.model.id,
            cls.model.doc_id,
            cls.model.from_page,
            cls.model.to_page,
            cls.model.retry_count,
            Document.kb_id,
            Document.parser_id,
            Document.parser_config,
            Document.name,
            Document.type,
            Document.location,
            Document.size,
            Knowledgebase.tenant_id,
            Knowledgebase.language,
            Knowledgebase.embd_id,
            Knowledgebase.pagerank,
            Knowledgebase.parser_config.alias("kb_parser_config"),
            Tenant.img2txt_id,
            Tenant.asr_id,
            Tenant.llm_id,
            cls.model.update_time,
        ]
        docs = (
            cls.model.select(*fields)
            .join(Document, on=(cls.model.doc_id == Document.id))
            .join(Knowledgebase, on=(Document.kb_id == Knowledgebase.id))
            .join(Tenant, on=(Knowledgebase.tenant_id == Tenant.id))
            .where(cls.model.id == task_id)
        )
        docs = list(docs.dicts())
        if not docs:
            return None

        msg = f"\n{datetime.now().strftime('%H:%M:%S')} Task has been received."
        prog = random.random() / 10.0
        if docs[0]["retry_count"] >= 3:
            msg = "\nERROR: Task is abandoned after 3 times attempts."
            prog = -1

        cls.model.update(
            progress_msg=cls.model.progress_msg + msg,
            progress=prog,
            retry_count=docs[0]["retry_count"] + 1,
        ).where(cls.model.id == docs[0]["id"]).execute()

        if docs[0]["retry_count"] >= 3:
            return None

        return docs[0]

    @classmethod
    @DB.connection_context()
    def get_tasks(cls, doc_id: str):
        fields = [
            cls.model.id,
            cls.model.from_page,
            cls.model.progress,
            cls.model.digest,
            cls.model.chunk_ids,
        ]
        tasks = cls.model.select(*fields).order_by(cls.model.from_page.asc(), cls.model.create_time.desc()).where(cls.model.doc_id == doc_id)
        tasks = list(tasks.dicts())
        if not tasks:
            return None
        return tasks

    @classmethod
    @DB.connection_context()
    def update_chunk_ids(cls, id: str, chunk_ids: str):
        cls.model.update(chunk_ids=chunk_ids).where(cls.model.id == id).execute()

    @classmethod
    @DB.connection_context()
    def get_ongoing_doc_name(cls):
        with DB.lock("get_task", -1):
            docs = (
                cls.model.select(*[Document.id, Document.kb_id, Document.location, File.parent_id])
                .join(Document, on=(cls.model.doc_id == Document.id))
                .join(
                    File2Document,
                    on=(File2Document.document_id == Document.id),
                    join_type=JOIN.LEFT_OUTER,
                )
                .join(
                    File,
                    on=(File2Document.file_id == File.id),
                    join_type=JOIN.LEFT_OUTER,
                )
                .where(
                    Document.status == StatusEnum.VALID.value,
                    Document.run == TaskStatus.RUNNING.value,
                    ~(Document.type == FileType.VIRTUAL.value),
                    cls.model.progress < 1,
                    cls.model.create_time >= current_timestamp() - 1000 * 600,
                )
            )
            docs = list(docs.dicts())
            if not docs:
                return []

            return list(
                set(
                    [
                        (
                            d["parent_id"] if d["parent_id"] else d["kb_id"],
                            d["location"],
                        )
                        for d in docs
                    ]
                )
            )

    @classmethod
    @DB.connection_context()
    def do_cancel(cls, id):
        task = cls.model.get_by_id(id)
        _, doc = DocumentService.get_by_id(task.doc_id)
        return doc.run == TaskStatus.CANCEL.value or doc.progress < 0

    @classmethod
    @DB.connection_context()
    def update_progress(cls, id, info):
        if os.environ.get("MACOS"):
            if info["progress_msg"]:
                task = cls.model.get_by_id(id)
                progress_msg = trim_header_by_lines(task.progress_msg + "\n" + info["progress_msg"], 3000)
                cls.model.update(progress_msg=progress_msg).where(cls.model.id == id).execute()
            if "progress" in info:
                cls.model.update(progress=info["progress"]).where(cls.model.id == id).execute()
            return

        with DB.lock("update_progress", -1):
            if info["progress_msg"]:
                task = cls.model.get_by_id(id)
                progress_msg = trim_header_by_lines(task.progress_msg + "\n" + info["progress_msg"], 3000)
                cls.model.update(progress_msg=progress_msg).where(cls.model.id == id).execute()
            if "progress" in info:
                cls.model.update(progress=info["progress"]).where(cls.model.id == id).execute()


def queue_tasks(doc: dict, bucket: str, name: str):
    """
    将文档解析任务分割并加入队列处理。

    该函数根据文档类型(PDF、表格等)将文档分割成多个子任务，计算任务摘要，
    检查是否可以重用之前的任务结果，并将未完成的任务加入Redis队列进行处理。

    参数:
        doc (dict): 文档信息字典，包含id、type、parser_id、parser_config等信息
        bucket (str): 存储桶名称
        name (str): 文件名称

    流程:
        1. 根据文档类型(PDF/表格)将文档分割成多个子任务
        2. 为每个任务生成唯一摘要(digest)
        3. 尝试重用之前任务的处理结果
        4. 清理旧任务并更新文档状态
        5. 将新任务批量插入数据库
        6. 将未完成的任务加入Redis队列
    """

    def new_task():
        """
        创建一个新的任务字典，包含基本任务信息。

        返回:
            dict: 包含任务ID、文档ID、进度和页面范围的任务字典
        """
        return {"id": get_uuid(), "doc_id": doc["id"], "progress": 0.0, "from_page": 0, "to_page": 100000000}

    # 存储所有解析任务的数组
    parse_task_array = []

    # PDF文档处理逻辑
    if doc["type"] == FileType.PDF.value:
        # 获取布局识别方式，默认为"DeepDOC"
        do_layout = doc["parser_config"].get("layout_recognize", "DeepDOC")
        # 获取PDF总页数
        pages = 1
        # 获取每个任务处理的页数，默认为12页
        page_size = doc["parser_config"].get("task_page_size", 12)
        # 对于学术论文类型，默认任务页数为22
        if doc["parser_id"] == "paper":
            page_size = doc["parser_config"].get("task_page_size", 22)
        # 对于特定解析器或非DeepDOC布局识别，将整个文档作为一个任务处理
        if doc["parser_id"] in ["one", "knowledge_graph"] or do_layout != "DeepDOC":
            page_size = 10**9
        # 获取需要处理的页面范围，默认为全部页面
        page_ranges = doc["parser_config"].get("pages") or [(1, 10**5)]
        # 根据页面范围和任务页数分割任务
        for s, e in page_ranges:
            # 调整页码（从0开始）
            s -= 1
            s = max(0, s)
            # 确保结束页不超过文档总页数
            e = min(e - 1, pages)
            # 按照任务页数分割任务
            for p in range(s, e, page_size):
                task = new_task()
                task["from_page"] = p
                task["to_page"] = min(p + page_size, e)
                parse_task_array.append(task)

    # 其他类型文档，整个文档作为一个任务处理
    else:
        parse_task_array.append(new_task())

    # 获取文档的分块配置
    chunking_config = DocumentService.get_chunking_config(doc["id"])
    # 为每个任务生成唯一摘要(digest)
    for task in parse_task_array:
        # 创建哈希对象
        hasher = xxhash.xxh64()
        # 对分块配置中的每个字段进行哈希
        for field in sorted(chunking_config.keys()):
            if field == "parser_config":
                # 移除不需要参与哈希计算的特定配置项
                for k in ["raptor", "graphrag"]:
                    if k in chunking_config[field]:
                        del chunking_config[field][k]
            # 将配置字段添加到哈希计算中
            hasher.update(str(chunking_config[field]).encode("utf-8"))
        # 将任务特定字段添加到哈希计算中
        for field in ["doc_id", "from_page", "to_page"]:
            hasher.update(str(task.get(field, "")).encode("utf-8"))
        # 生成任务摘要并设置初始进度
        task_digest = hasher.hexdigest()
        task["digest"] = task_digest
        task["progress"] = 0.0

    # 获取文档之前的任务记录
    prev_tasks = TaskService.get_tasks(doc["id"])
    # 记录重用的块数量
    ck_num = 0
    if prev_tasks:
        # 尝试重用之前任务的处理结果
        for task in parse_task_array:
            ck_num += reuse_prev_task_chunks(task, prev_tasks, chunking_config)
        # 删除文档之前的任务记录
        TaskService.filter_delete([Task.doc_id == doc["id"]])
        # 收集需要删除的块ID
        chunk_ids = []
        for task in prev_tasks:
            if task["chunk_ids"]:
                chunk_ids.extend(task["chunk_ids"].split())
        # 从文档存储中删除这些块
        if chunk_ids:
            settings.docStoreConn.delete({"id": chunk_ids}, search.index_name(chunking_config["tenant_id"]), chunking_config["kb_id"])
    # 更新文档的块数量
    DocumentService.update_by_id(doc["id"], {"chunk_num": ck_num})

    # 将新任务批量插入数据库
    bulk_insert_into_db(Task, parse_task_array, True)
    # 开始解析文档
    DocumentService.begin2parse(doc["id"])

    # 筛选出未完成的任务
    unfinished_task_array = [task for task in parse_task_array if task["progress"] < 1.0]
    # 将未完成的任务加入Redis队列
    for unfinished_task in unfinished_task_array:
        assert REDIS_CONN.queue_product(SVR_QUEUE_NAME, message=unfinished_task), "Can't access Redis. Please check the Redis' status."


def reuse_prev_task_chunks(task: dict, prev_tasks: list[dict], chunking_config: dict):
    idx = 0
    while idx < len(prev_tasks):
        prev_task = prev_tasks[idx]
        if prev_task.get("from_page", 0) == task.get("from_page", 0) and prev_task.get("digest", 0) == task.get("digest", ""):
            break
        idx += 1

    if idx >= len(prev_tasks):
        return 0
    prev_task = prev_tasks[idx]
    if prev_task["progress"] < 1.0 or not prev_task["chunk_ids"]:
        return 0
    task["chunk_ids"] = prev_task["chunk_ids"]
    task["progress"] = 1.0
    if "from_page" in task and "to_page" in task and int(task["to_page"]) - int(task["from_page"]) >= 10**6:
        task["progress_msg"] = f"Page({task['from_page']}~{task['to_page']}): "
    else:
        task["progress_msg"] = ""
    task["progress_msg"] = " ".join([datetime.now().strftime("%H:%M:%S"), task["progress_msg"], "Reused previous task's chunks."])
    prev_task["chunk_ids"] = ""

    return len(task["chunk_ids"].split())
