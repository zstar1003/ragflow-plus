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
import datetime
import xxhash
import re
from flask import request
from flask_login import login_required, current_user
from rag.app.qa import rmPrefix, beAdoc
from rag.nlp import search, rag_tokenizer
from rag.settings import PAGERANK_FLD
from rag.utils import rmSpace
from api.db import LLMType, ParserType
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMBundle
from api.db.services.user_service import UserTenantService
from api.utils.api_utils import server_error_response, get_data_error_result, validate_request
from api.db.services.document_service import DocumentService
from api import settings
from api.utils.api_utils import get_json_result


@manager.route("/list", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id")  # 验证请求中必须包含 doc_id 参数
def list_chunk():
    req = request.json
    doc_id = req["doc_id"]
    page = int(req.get("page", 1))
    size = int(req.get("size", 30))
    question = req.get("keywords", "")
    try:
        tenant_id = DocumentService.get_tenant_id(req["doc_id"])
        if not tenant_id:
            return get_data_error_result(message="Tenant not found!")
        e, doc = DocumentService.get_by_id(doc_id)
        if not e:
            return get_data_error_result(message="Document not found!")
        kb_ids = KnowledgebaseService.get_kb_ids(tenant_id)
        query = {"doc_ids": [doc_id], "page": page, "size": size, "question": question, "sort": True}
        if "available_int" in req:
            query["available_int"] = int(req["available_int"])
        sres = settings.retrievaler.search(query, search.index_name(tenant_id), kb_ids, highlight=True)
        res = {"total": sres.total, "chunks": [], "doc": doc.to_dict()}
        for id in sres.ids:
            d = {
                "chunk_id": id,
                "content_with_weight": rmSpace(sres.highlight[id]) if question and id in sres.highlight else sres.field[id].get("content_with_weight", ""),
                "doc_id": sres.field[id]["doc_id"],
                "docnm_kwd": sres.field[id]["docnm_kwd"],
                "important_kwd": sres.field[id].get("important_kwd", []),
                "question_kwd": sres.field[id].get("question_kwd", []),
                "image_id": sres.field[id].get("img_id", ""),
                "available_int": int(sres.field[id].get("available_int", 1)),
                "positions": sres.field[id].get("position_int", []),
            }
            assert isinstance(d["positions"], list)
            assert len(d["positions"]) == 0 or (isinstance(d["positions"][0], list) and len(d["positions"][0]) == 5)
            res["chunks"].append(d)
        return get_json_result(data=res)
    except Exception as e:
        if str(e).find("not_found") > 0:
            return get_json_result(data=False, message="No chunk found!", code=settings.RetCode.DATA_ERROR)
        return server_error_response(e)


@manager.route("/get", methods=["GET"])  # noqa: F821
@login_required
def get():
    chunk_id = request.args["chunk_id"]
    try:
        tenants = UserTenantService.query(user_id=current_user.id)
        if not tenants:
            return get_data_error_result(message="Tenant not found!")
        for tenant in tenants:
            kb_ids = KnowledgebaseService.get_kb_ids(tenant.tenant_id)
            chunk = settings.docStoreConn.get(chunk_id, search.index_name(tenant.tenant_id), kb_ids)
            if chunk:
                break
        if chunk is None:
            return server_error_response(Exception("Chunk not found"))

        k = []
        for n in chunk.keys():
            if re.search(r"(_vec$|_sm_|_tks|_ltks)", n):
                k.append(n)
        for n in k:
            del chunk[n]

        return get_json_result(data=chunk)
    except Exception as e:
        if str(e).find("NotFoundError") >= 0:
            return get_json_result(data=False, message="Chunk not found!", code=settings.RetCode.DATA_ERROR)
        return server_error_response(e)


@manager.route("/set", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id", "chunk_id", "content_with_weight")
def set():
    req = request.json
    d = {"id": req["chunk_id"], "content_with_weight": req["content_with_weight"]}
    d["content_ltks"] = rag_tokenizer.tokenize(req["content_with_weight"])
    d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])
    if "important_kwd" in req:
        d["important_kwd"] = req["important_kwd"]
        d["important_tks"] = rag_tokenizer.tokenize(" ".join(req["important_kwd"]))
    if "question_kwd" in req:
        d["question_kwd"] = req["question_kwd"]
        d["question_tks"] = rag_tokenizer.tokenize("\n".join(req["question_kwd"]))
    if "tag_kwd" in req:
        d["tag_kwd"] = req["tag_kwd"]
    if "tag_feas" in req:
        d["tag_feas"] = req["tag_feas"]
    if "available_int" in req:
        d["available_int"] = req["available_int"]
    if "img_id" in req:
        d["img_id"] = req["img_id"]

    try:
        tenant_id = DocumentService.get_tenant_id(req["doc_id"])
        if not tenant_id:
            return get_data_error_result(message="Tenant not found!")

        e, doc = DocumentService.get_by_id(req["doc_id"])
        if not e:
            return get_data_error_result(message="Document not found!")

        # 检查是否只是更新img_id，如果是则跳过嵌入计算
        only_img_update = (
            len(req) == 4  # doc_id, chunk_id, content_with_weight, img_id
            and "img_id" in req
            and all(key in ["doc_id", "chunk_id", "content_with_weight", "img_id"] for key in req.keys())
        )

        print(f"[DEBUG] Request keys: {list(req.keys())}, only_img_update: {only_img_update}")

        if only_img_update:
            # 只更新img_id，不需要重新计算嵌入
            print(f"[DEBUG] Updating only img_id: {req['img_id']} for chunk: {req['chunk_id']}")
            update_data = {"id": req["chunk_id"], "img_id": req["img_id"]}
            settings.docStoreConn.update({"id": req["chunk_id"]}, update_data, search.index_name(tenant_id), doc.kb_id)
            return get_json_result(data=True)

        # 正常的更新流程，需要重新计算嵌入
        embd_id = DocumentService.get_embd_id(req["doc_id"])
        embd_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING, embd_id)

        if doc.parser_id == ParserType.QA:
            arr = [t for t in re.split(r"[\n\t]", req["content_with_weight"]) if len(t) > 1]
            q, a = rmPrefix(arr[0]), rmPrefix("\n".join(arr[1:]))
            d = beAdoc(d, q, a, not any([rag_tokenizer.is_chinese(t) for t in q + a]))

        v, c = embd_mdl.encode([doc.name, req["content_with_weight"] if not d.get("question_kwd") else "\n".join(d["question_kwd"])])
        v = 0.1 * v[0] + 0.9 * v[1] if doc.parser_id != ParserType.QA else v[1]
        d["q_%d_vec" % len(v)] = v.tolist()
        settings.docStoreConn.update({"id": req["chunk_id"]}, d, search.index_name(tenant_id), doc.kb_id)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/switch", methods=["POST"])  # noqa: F821
@login_required
@validate_request("chunk_ids", "available_int", "doc_id")
def switch():
    req = request.json
    try:
        e, doc = DocumentService.get_by_id(req["doc_id"])
        if not e:
            return get_data_error_result(message="Document not found!")
        for cid in req["chunk_ids"]:
            if not settings.docStoreConn.update({"id": cid}, {"available_int": int(req["available_int"])}, search.index_name(DocumentService.get_tenant_id(req["doc_id"])), doc.kb_id):
                return get_data_error_result(message="Index updating failure")
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/rm", methods=["POST"])  # noqa: F821
@login_required
@validate_request("chunk_ids", "doc_id")
def rm():
    from rag.utils.storage_factory import STORAGE_IMPL

    req = request.json
    try:
        e, doc = DocumentService.get_by_id(req["doc_id"])
        if not e:
            return get_data_error_result(message="Document not found!")
        if not settings.docStoreConn.delete({"id": req["chunk_ids"]}, search.index_name(current_user.id), doc.kb_id):
            return get_data_error_result(message="Index updating failure")
        deleted_chunk_ids = req["chunk_ids"]
        chunk_number = len(deleted_chunk_ids)
        DocumentService.decrement_chunk_num(doc.id, doc.kb_id, 1, chunk_number, 0)
        for cid in deleted_chunk_ids:
            if STORAGE_IMPL.obj_exist(doc.kb_id, cid):
                STORAGE_IMPL.rm(doc.kb_id, cid)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/create", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id", "content_with_weight")
def create():
    req = request.json
    chunck_id = xxhash.xxh64((req["content_with_weight"] + req["doc_id"]).encode("utf-8")).hexdigest()
    d = {"id": chunck_id, "content_ltks": rag_tokenizer.tokenize(req["content_with_weight"]), "content_with_weight": req["content_with_weight"]}
    d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])
    d["important_kwd"] = req.get("important_kwd", [])
    d["important_tks"] = rag_tokenizer.tokenize(" ".join(req.get("important_kwd", [])))
    d["question_kwd"] = req.get("question_kwd", [])
    d["question_tks"] = rag_tokenizer.tokenize("\n".join(req.get("question_kwd", [])))
    d["create_time"] = str(datetime.datetime.now()).replace("T", " ")[:19]
    d["create_timestamp_flt"] = datetime.datetime.now().timestamp()

    try:
        e, doc = DocumentService.get_by_id(req["doc_id"])
        if not e:
            return get_data_error_result(message="Document not found!")
        d["kb_id"] = [doc.kb_id]
        d["docnm_kwd"] = doc.name
        d["title_tks"] = rag_tokenizer.tokenize(doc.name)
        d["doc_id"] = doc.id

        tenant_id = DocumentService.get_tenant_id(req["doc_id"])
        if not tenant_id:
            return get_data_error_result(message="Tenant not found!")

        e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
        if not e:
            return get_data_error_result(message="Knowledgebase not found!")
        if kb.pagerank:
            d[PAGERANK_FLD] = kb.pagerank

        embd_id = DocumentService.get_embd_id(req["doc_id"])
        embd_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING.value, embd_id)

        v, c = embd_mdl.encode([doc.name, req["content_with_weight"] if not d["question_kwd"] else "\n".join(d["question_kwd"])])
        v = 0.1 * v[0] + 0.9 * v[1]
        d["q_%d_vec" % len(v)] = v.tolist()
        settings.docStoreConn.insert([d], search.index_name(tenant_id), doc.kb_id)

        DocumentService.increment_chunk_num(doc.id, doc.kb_id, c, 1, 0)
        return get_json_result(data={"chunk_id": chunck_id})
    except Exception as e:
        return server_error_response(e)


@manager.route("/retrieval_test", methods=["POST"])  # noqa: F821
@login_required
@validate_request("kb_id", "question")
def retrieval_test():
    req = request.json
    page = int(req.get("page", 1))
    size = int(req.get("size", 30))
    question = req["question"]
    kb_ids = req["kb_id"]
    # 如果kb_ids是字符串，将其转换为列表
    if isinstance(kb_ids, str):
        kb_ids = [kb_ids]
    doc_ids = req.get("doc_ids", [])
    similarity_threshold = float(req.get("similarity_threshold", 0.0))
    vector_similarity_weight = float(req.get("vector_similarity_weight", 0.3))
    top = int(req.get("top_k", 1024))  # 此参数前端请求不会携带，默认即1024
    # langs = req.get("cross_languages", [])  # 获取跨语言设定
    tenant_ids = []

    try:
        # 查询当前用户所属的租户
        tenants = UserTenantService.query(user_id=current_user.id)

        # 验证知识库权限
        for kb_id in kb_ids:
            for tenant in tenants:
                if KnowledgebaseService.query(tenant_id=tenant.tenant_id, id=kb_id):
                    tenant_ids.append(tenant.tenant_id)
                    break
            else:
                return get_json_result(data=False, message="Only owner of knowledgebase authorized for this operation.", code=settings.RetCode.OPERATING_ERROR)

        # 获取知识库信息
        e, kb = KnowledgebaseService.get_by_id(kb_ids[0])
        if not e:
            return get_data_error_result(message="Knowledgebase not found!")

        # if langs:
        # question = cross_languages(kb.tenant_id, None, question, langs) # 跨语言处理

        # 加载嵌入模型
        embd_mdl = LLMBundle(kb.tenant_id, LLMType.EMBEDDING.value, llm_name=kb.embd_id)

        # 加载重排序模型（如果指定）
        rerank_mdl = None
        if req.get("rerank_id"):
            rerank_mdl = LLMBundle(kb.tenant_id, LLMType.RERANK.value, llm_name=req["rerank_id"])

        # 对问题进行标签化
        # labels = label_question(question, [kb])
        labels = None

        # 执行检索操作
        ranks = settings.retrievaler.retrieval(
            question, embd_mdl, tenant_ids, kb_ids, page, size, similarity_threshold, vector_similarity_weight, top, doc_ids, rerank_mdl=rerank_mdl, highlight=req.get("highlight"), rank_feature=labels
        )

        # 移除不必要的向量信息
        for c in ranks["chunks"]:
            c.pop("vector", None)
        ranks["labels"] = labels

        return get_json_result(data=ranks)
    except Exception as e:
        if str(e).find("not_found") > 0:
            return get_json_result(data=False, message="No chunk found! Check the chunk status please!", code=settings.RetCode.DATA_ERROR)
        return server_error_response(e)
