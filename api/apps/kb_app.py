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
import json
import os

from flask import request
from flask_login import current_user, login_required

from api import settings
from api.constants import DATASET_NAME_LIMIT
from api.db import FileSource, StatusEnum
from api.db.db_models import File
from api.db.services import duplicate_name
from api.db.services.document_service import DocumentService
from api.db.services.file2document_service import File2DocumentService
from api.db.services.file_service import FileService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.user_service import TenantService, UserTenantService
from api.utils import get_uuid
from api.utils.api_utils import get_data_error_result, get_json_result, not_allowed_parameters, server_error_response, validate_request
from rag.nlp import search
from rag.settings import PAGERANK_FLD


@manager.route("/create", methods=["post"])  # noqa: F821
@login_required
@validate_request("name")
def create():
    req = request.json
    dataset_name = req["name"]
    if not isinstance(dataset_name, str):
        return get_data_error_result(message="Dataset name must be string.")
    if dataset_name == "":
        return get_data_error_result(message="Dataset name can't be empty.")
    if len(dataset_name) >= DATASET_NAME_LIMIT:
        return get_data_error_result(message=f"Dataset name length is {len(dataset_name)} which is large than {DATASET_NAME_LIMIT}")

    dataset_name = dataset_name.strip()
    dataset_name = duplicate_name(KnowledgebaseService.query, name=dataset_name, tenant_id=current_user.id, status=StatusEnum.VALID.value)
    try:
        req["id"] = get_uuid()
        req["tenant_id"] = current_user.id
        req["created_by"] = current_user.id
        e, t = TenantService.get_by_id(current_user.id)
        if not e:
            return get_data_error_result(message="Tenant not found.")
        req["embd_id"] = t.embd_id
        if not KnowledgebaseService.save(**req):
            return get_data_error_result()
        return get_json_result(data={"kb_id": req["id"]})
    except Exception as e:
        return server_error_response(e)


@manager.route("/update", methods=["post"])  # noqa: F821
@login_required
@validate_request("kb_id", "name", "description", "permission", "parser_id")
@not_allowed_parameters("id", "tenant_id", "created_by", "create_time", "update_time", "create_date", "update_date", "created_by")
def update():
    req = request.json
    req["name"] = req["name"].strip()
    if not KnowledgebaseService.accessible4deletion(req["kb_id"], current_user.id):
        return get_json_result(data=False, message="No authorization.", code=settings.RetCode.AUTHENTICATION_ERROR)
    try:
        if not KnowledgebaseService.query(created_by=current_user.id, id=req["kb_id"]):
            return get_json_result(data=False, message="Only owner of knowledgebase authorized for this operation.", code=settings.RetCode.OPERATING_ERROR)

        e, kb = KnowledgebaseService.get_by_id(req["kb_id"])
        if not e:
            return get_data_error_result(message="Can't find this knowledgebase!")

        if req.get("parser_id", "") == "tag" and os.environ.get("DOC_ENGINE", "elasticsearch") == "infinity":
            return get_json_result(data=False, message="The chunk method Tag has not been supported by Infinity yet.", code=settings.RetCode.OPERATING_ERROR)

        if req["name"].lower() != kb.name.lower() and len(KnowledgebaseService.query(name=req["name"], tenant_id=current_user.id, status=StatusEnum.VALID.value)) > 1:
            return get_data_error_result(message="Duplicated knowledgebase name.")

        del req["kb_id"]
        if not KnowledgebaseService.update_by_id(kb.id, req):
            return get_data_error_result()

        if kb.pagerank != req.get("pagerank", 0):
            if req.get("pagerank", 0) > 0:
                settings.docStoreConn.update({"kb_id": kb.id}, {PAGERANK_FLD: req["pagerank"]}, search.index_name(kb.tenant_id), kb.id)
            else:
                # Elasticsearch requires PAGERANK_FLD be non-zero!
                settings.docStoreConn.update({"exists": PAGERANK_FLD}, {"remove": PAGERANK_FLD}, search.index_name(kb.tenant_id), kb.id)

        e, kb = KnowledgebaseService.get_by_id(kb.id)
        if not e:
            return get_data_error_result(message="Database error (Knowledgebase rename)!")
        kb = kb.to_dict()
        kb.update(req)

        return get_json_result(data=kb)
    except Exception as e:
        return server_error_response(e)


@manager.route("/detail", methods=["GET"])  # noqa: F821
@login_required
def detail():
    kb_id = request.args["kb_id"]
    try:
        tenants = UserTenantService.query(user_id=current_user.id)
        for tenant in tenants:
            if KnowledgebaseService.query(tenant_id=tenant.tenant_id, id=kb_id):
                break
        else:
            return get_json_result(data=False, message="Only owner of knowledgebase authorized for this operation.", code=settings.RetCode.OPERATING_ERROR)
        kb = KnowledgebaseService.get_detail(kb_id)
        if not kb:
            return get_data_error_result(message="Can't find this knowledgebase!")
        return get_json_result(data=kb)
    except Exception as e:
        return server_error_response(e)


@manager.route("/list", methods=["GET"])  # noqa: F821
@login_required
def list_kbs():
    keywords = request.args.get("keywords", "")
    page_number = int(request.args.get("page", 1))
    items_per_page = int(request.args.get("page_size", 150))
    parser_id = request.args.get("parser_id")
    orderby = request.args.get("orderby", "create_time")
    desc = request.args.get("desc", True)
    try:
        tenants = TenantService.get_joined_tenants_by_user_id(current_user.id)
        kbs, total = KnowledgebaseService.get_by_tenant_ids([m["tenant_id"] for m in tenants], current_user.id, page_number, items_per_page, orderby, desc, keywords, parser_id)
        return get_json_result(data={"kbs": kbs, "total": total})
    except Exception as e:
        return server_error_response(e)


@manager.route("/rm", methods=["post"])  # noqa: F821
@login_required
@validate_request("kb_id")
def rm():
    req = request.json
    if not KnowledgebaseService.accessible4deletion(req["kb_id"], current_user.id):
        return get_json_result(data=False, message="No authorization.", code=settings.RetCode.AUTHENTICATION_ERROR)
    try:
        kbs = KnowledgebaseService.query(created_by=current_user.id, id=req["kb_id"])
        if not kbs:
            return get_json_result(data=False, message="Only owner of knowledgebase authorized for this operation.", code=settings.RetCode.OPERATING_ERROR)

        for doc in DocumentService.query(kb_id=req["kb_id"]):
            if not DocumentService.remove_document(doc, kbs[0].tenant_id):
                return get_data_error_result(message="Database error (Document removal)!")
            f2d = File2DocumentService.get_by_document_id(doc.id)
            if f2d:
                FileService.filter_delete([File.source_type == FileSource.KNOWLEDGEBASE, File.id == f2d[0].file_id])
            File2DocumentService.delete_by_document_id(doc.id)
        FileService.filter_delete([File.source_type == FileSource.KNOWLEDGEBASE, File.type == "folder", File.name == kbs[0].name])
        if not KnowledgebaseService.delete_by_id(req["kb_id"]):
            return get_data_error_result(message="Database error (Knowledgebase removal)!")
        for kb in kbs:
            settings.docStoreConn.delete({"kb_id": kb.id}, search.index_name(kb.tenant_id), kb.id)
            settings.docStoreConn.deleteIdx(search.index_name(kb.tenant_id), kb.id)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<kb_id>/tags", methods=["GET"])  # noqa: F821
@login_required
def list_tags(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(data=False, message="No authorization.", code=settings.RetCode.AUTHENTICATION_ERROR)

    tags = settings.retrievaler.all_tags(current_user.id, [kb_id])
    return get_json_result(data=tags)


@manager.route("/tags", methods=["GET"])  # noqa: F821
@login_required
def list_tags_from_kbs():
    kb_ids = request.args.get("kb_ids", "").split(",")
    for kb_id in kb_ids:
        if not KnowledgebaseService.accessible(kb_id, current_user.id):
            return get_json_result(data=False, message="No authorization.", code=settings.RetCode.AUTHENTICATION_ERROR)

    tags = settings.retrievaler.all_tags(current_user.id, kb_ids)
    return get_json_result(data=tags)


@manager.route("/<kb_id>/rm_tags", methods=["POST"])  # noqa: F821
@login_required
def rm_tags(kb_id):
    req = request.json
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(data=False, message="No authorization.", code=settings.RetCode.AUTHENTICATION_ERROR)
    e, kb = KnowledgebaseService.get_by_id(kb_id)

    for t in req["tags"]:
        settings.docStoreConn.update({"tag_kwd": t, "kb_id": [kb_id]}, {"remove": {"tag_kwd": t}}, search.index_name(kb.tenant_id), kb_id)
    return get_json_result(data=True)


@manager.route("/<kb_id>/rename_tag", methods=["POST"])  # noqa: F821
@login_required
def rename_tags(kb_id):
    req = request.json
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(data=False, message="No authorization.", code=settings.RetCode.AUTHENTICATION_ERROR)
    e, kb = KnowledgebaseService.get_by_id(kb_id)

    settings.docStoreConn.update(
        {"tag_kwd": req["from_tag"], "kb_id": [kb_id]}, {"remove": {"tag_kwd": req["from_tag"].strip()}, "add": {"tag_kwd": req["to_tag"]}}, search.index_name(kb.tenant_id), kb_id
    )
    return get_json_result(data=True)


@manager.route("/<kb_id>/knowledge_graph", methods=["GET"])  # noqa: F821
@login_required
def knowledge_graph(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(data=False, message="No authorization.", code=settings.RetCode.AUTHENTICATION_ERROR)
    _, kb = KnowledgebaseService.get_by_id(kb_id)
    req = {"kb_id": [kb_id], "knowledge_graph_kwd": ["graph"]}

    obj = {"graph": {}, "mind_map": {}}
    if not settings.docStoreConn.indexExist(search.index_name(kb.tenant_id), kb_id):
        return get_json_result(data=obj)
    sres = settings.retrievaler.search(req, search.index_name(kb.tenant_id), [kb_id])
    if not len(sres.ids):
        return get_json_result(data=obj)

    for id in sres.ids[:1]:
        ty = sres.field[id]["knowledge_graph_kwd"]
        try:
            content_json = json.loads(sres.field[id]["content_with_weight"])
        except Exception:
            continue

        obj[ty] = content_json

    if "nodes" in obj["graph"]:
        obj["graph"]["nodes"] = sorted(obj["graph"]["nodes"], key=lambda x: x.get("pagerank", 0), reverse=True)[:256]
        if "edges" in obj["graph"]:
            node_id_set = {o["id"] for o in obj["graph"]["nodes"]}
            filtered_edges = [o for o in obj["graph"]["edges"] if o["source"] != o["target"] and o["source"] in node_id_set and o["target"] in node_id_set]
            obj["graph"]["edges"] = sorted(filtered_edges, key=lambda x: x.get("weight", 0), reverse=True)[:128]
    return get_json_result(data=obj)


@manager.route("/images", methods=["GET"])  # noqa: F821
@login_required
def get_kb_images():
    kb_id = request.args.get("kb_id")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    search_text = request.args.get("search", "")

    if not kb_id:
        return get_json_result(data=False, message="Knowledge base ID is required.", code=settings.RetCode.ARGUMENT_ERROR)

    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(data=False, message="No authorization.", code=settings.RetCode.AUTHENTICATION_ERROR)

    try:
        _, kb = KnowledgebaseService.get_by_id(kb_id)

        # 获取知识库下的所有文档
        from api.db.services.document_service import DocumentService

        docs = DocumentService.get_by_kb_id(kb_id, 1, 10000, "create_time", False, "")  # 获取所有文档

        all_images = []

        # 遍历每个文档，获取其chunks
        for doc in docs[0]:  # docs返回(documents, total)
            try:
                # 使用chunk_list方法获取文档的所有chunks
                chunks = settings.retrievaler.chunk_list(doc_id=doc["id"], tenant_id=kb.tenant_id, kb_ids=[kb_id], fields=["docnm_kwd", "content_with_weight", "img_id", "doc_id"])

                # 筛选有图片的chunks
                for chunk in chunks:
                    if chunk.get("img_id") and chunk["img_id"].strip():
                        # 如果有搜索条件，进行内容过滤
                        if search_text and search_text.lower() not in chunk.get("content_with_weight", "").lower():
                            continue

                        print(f"Found chunk with image: {chunk['id']}, img_id: {chunk['img_id']}")  # 调试信息

                        all_images.append(
                            {
                                "img_id": chunk["img_id"],
                                "doc_id": chunk["doc_id"],
                                "doc_name": chunk["docnm_kwd"],
                                "chunk_id": chunk["id"],
                                "content": chunk["content_with_weight"][:200] + "..." if len(chunk["content_with_weight"]) > 200 else chunk["content_with_weight"],
                            }
                        )
            except Exception as e:
                print(f"Error processing document {doc['id']}: {e}")
                continue

        # 分页处理
        total_images = len(all_images)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_images = all_images[start_idx:end_idx]

        result = {"images": paginated_images, "total": total_images, "page": page, "page_size": page_size}

        print(f"Total images found: {total_images}")
        print(f"Returning {len(paginated_images)} images for page {page}")

        result = {"images": paginated_images, "total": total_images, "page": page, "page_size": page_size}
        print(f"API result: {result}")

        return get_json_result(data=result)

    except Exception as e:
        return server_error_response(e)
