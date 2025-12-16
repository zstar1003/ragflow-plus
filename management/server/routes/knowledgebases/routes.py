import traceback

from flask import request
from services.knowledgebases.service import KnowledgebaseService
from services.auth import get_current_user_from_token, is_admin
from utils import error_response, success_response

from .. import knowledgebase_bp


@knowledgebase_bp.route("", methods=["GET"])
def get_knowledgebase_list():
    """获取知识库列表"""
    try:
        # 获取当前用户信息
        current_user = get_current_user_from_token()
        
        params = {
            "page": int(request.args.get("currentPage", 1)),
            "size": int(request.args.get("size", 10)),
            "name": request.args.get("name", ""),
            "sort_by": request.args.get("sort_by", "create_time"),
            "sort_order": request.args.get("sort_order", "desc"),
        }
        
        # 如果是团队负责人，只返回其租户的知识库
        if current_user and not is_admin(current_user):
            params["tenant_id"] = current_user.get("tenant_id")
        
        result = KnowledgebaseService.get_knowledgebase_list(**params)
        return success_response(result)
    except ValueError:
        return error_response("参数类型错误", code=400)
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/<string:kb_id>", methods=["GET"])
def get_knowledgebase_detail(kb_id):
    """获取知识库详情"""
    try:
        knowledgebase = KnowledgebaseService.get_knowledgebase_detail(kb_id=kb_id)
        if not knowledgebase:
            return error_response("知识库不存在", code=404)
        return success_response(knowledgebase)
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("", methods=["POST"])
def create_knowledgebase():
    """创建知识库"""
    try:
        data = request.json
        if not data.get("name"):
            return error_response("知识库名称不能为空", code=400)

        # 移除 created_by 参数
        kb = KnowledgebaseService.create_knowledgebase(**data)
        return success_response(kb, "创建成功", code=0)
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/<string:kb_id>", methods=["PUT"])
def update_knowledgebase(kb_id):
    """更新知识库"""
    try:
        data = request.json
        kb = KnowledgebaseService.update_knowledgebase(kb_id=kb_id, **data)
        if not kb:
            return error_response("知识库不存在", code=404)
        return success_response(kb)
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/<string:kb_id>", methods=["DELETE"])
def delete_knowledgebase(kb_id):
    """删除知识库"""
    try:
        result = KnowledgebaseService.delete_knowledgebase(kb_id=kb_id)
        if not result:
            return error_response("知识库不存在", code=404)
        return success_response(message="删除成功")
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/batch", methods=["DELETE"])
def batch_delete_knowledgebase():
    """批量删除知识库"""
    try:
        data = request.json
        if not data or not data.get("ids"):
            return error_response("请选择要删除的知识库", code=400)

        result = KnowledgebaseService.batch_delete_knowledgebase(kb_ids=data["ids"])
        return success_response(message=f"成功删除 {result} 个知识库")
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/<string:kb_id>/documents", methods=["GET"])
def get_knowledgebase_documents(kb_id):
    """获取知识库下的文档列表"""
    try:
        params = {
            "kb_id": kb_id,
            "page": int(request.args.get("currentPage", 1)),
            "size": int(request.args.get("size", 10)),
            "name": request.args.get("name", ""),
            "sort_by": request.args.get("sort_by", "create_time"),
            "sort_order": request.args.get("sort_order", "desc"),
        }
        result = KnowledgebaseService.get_knowledgebase_documents(**params)
        return success_response(result)
    except ValueError:
        return error_response("参数类型错误", code=400)
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/<string:kb_id>/documents", methods=["POST"])
def add_documents_to_knowledgebase(kb_id):
    """添加文档到知识库"""
    try:
        print(f"[DEBUG] 接收到添加文档请求，kb_id: {kb_id}")
        data = request.json
        if not data:
            print("[ERROR] 请求数据为空")
            return error_response("请求数据不能为空", code=400)

        file_ids = data.get("file_ids", [])
        print(f"[DEBUG] 接收到的file_ids: {file_ids}, 类型: {type(file_ids)}")

        try:
            result = KnowledgebaseService.add_documents_to_knowledgebase(kb_id=kb_id, file_ids=file_ids)
            print(f"[DEBUG] 服务层处理成功，结果: {result}")
            return success_response(data=result, message="添加成功", code=201)
        except Exception as service_error:
            print(f"[ERROR] 服务层错误详情: {str(service_error)}")

            traceback.print_exc()
            return error_response(str(service_error), code=500)

    except Exception as e:
        print(f"[ERROR] 路由层错误详情: {str(e)}")
        traceback.print_exc()
        return error_response(str(e), code=500)


@knowledgebase_bp.route("/documents/<string:doc_id>", methods=["DELETE", "OPTIONS"])
def delete_document(doc_id):
    """删除文档"""
    # 处理 OPTIONS 预检请求
    if request.method == "OPTIONS":
        response = success_response({})
        # 添加 CORS 相关头
        response.headers.add("Access-Control-Allow-Methods", "DELETE")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        return response

    try:
        KnowledgebaseService.delete_document(doc_id)
        return success_response(message="删除成功")
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/documents/<doc_id>/parse/progress", methods=["GET"])
def get_parse_progress(doc_id):
    """获取文档解析进度"""
    # 处理 OPTIONS 预检请求
    if request.method == "OPTIONS":
        response = success_response({})
        # 添加 CORS 相关头
        response.headers.add("Access-Control-Allow-Methods", "GET")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        return response

    try:
        result = KnowledgebaseService.get_document_parse_progress(doc_id)
        if isinstance(result, dict) and "error" in result:
            return error_response(result["error"], code=404)
        return success_response(data=result)
    except Exception as e:
        print(f"获取解析进度失败: {str(e)}")
        return error_response("解析进行中，请稍后重试", code=202)


# 获取系统 Embedding 配置路由
@knowledgebase_bp.route("/system_embedding_config", methods=["GET"])
def get_system_embedding_config_route():
    """获取系统级 Embedding 配置的API端点"""
    try:
        config_data = KnowledgebaseService.get_system_embedding_config()
        return success_response(data=config_data)
    except Exception as e:
        print(f"获取系统 Embedding 配置失败: {str(e)}")
        return error_response(message=f"获取配置失败: {str(e)}", code=500)  # 返回通用错误信息


# 设置系统 Embedding 配置路由
@knowledgebase_bp.route("/system_embedding_config", methods=["POST"])
def set_system_embedding_config_route():
    """设置系统级 Embedding 配置的API端点"""
    try:
        data = request.json
        if not data:
            return error_response("请求数据不能为空", code=400)

        llm_name = data.get("llm_name", "").strip()
        api_base = data.get("api_base", "").strip()
        api_key = data.get("api_key", "").strip()  # 允许空

        if not llm_name or not api_base:
            return error_response("模型名称和 API 地址不能为空", code=400)

        # 调用服务层进行处理（包括连接测试和数据库操作）
        success, message = KnowledgebaseService.set_system_embedding_config(llm_name=llm_name, api_base=api_base, api_key=api_key)

        if success:
            return success_response(message=message)
        else:
            # 如果服务层返回失败（例如连接测试失败或数据库错误），将消息返回给前端
            return error_response(message=message, code=400)  # 使用 400 表示操作失败

    except Exception as e:
        # 捕获路由层或未预料的服务层异常
        print(f"设置系统 Embedding 配置失败: {str(e)}")
        return error_response(message=f"设置配置时发生内部错误: {str(e)}", code=500)


@knowledgebase_bp.route("/documents/<doc_id>/parse", methods=["POST"])
def parse_document(doc_id):
    """开始解析文档"""
    if request.method == "OPTIONS":
        response = success_response({})
        response.headers.add("Access-Control-Allow-Methods", "POST")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        return response

    try:
        result = KnowledgebaseService.parse_document(doc_id)
        if result.get("success"):
            return success_response(data={"message": f"文档 {doc_id} 同步解析完成。", "details": result})
        else:
            return error_response(result.get("message", "解析失败"), code=500)

    except Exception as e:
        return error_response(str(e), code=500)


# 启动顺序批量解析路由
@knowledgebase_bp.route("/<string:kb_id>/batch_parse_sequential/start", methods=["POST"])
def start_sequential_batch_parse_route(kb_id):
    """异步启动知识库的顺序批量解析任务"""
    if request.method == "OPTIONS":
        response = success_response({})
        response.headers.add("Access-Control-Allow-Methods", "POST")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        return response

    try:
        result = KnowledgebaseService.start_sequential_batch_parse_async(kb_id)
        if result.get("success"):
            return success_response(data={"message": result.get("message")})
        else:
            # 如果任务已在运行或启动失败，返回错误信息
            return error_response(result.get("message", "启动失败"), code=409 if "已在运行中" in result.get("message", "") else 500)
    except Exception as e:
        print(f"启动顺序批量解析路由处理失败 (KB ID: {kb_id}): {str(e)}")
        traceback.print_exc()
        return error_response(f"启动顺序批量解析失败: {str(e)}", code=500)


# 获取顺序批量解析进度路由
@knowledgebase_bp.route("/<string:kb_id>/batch_parse_sequential/progress", methods=["GET"])
def get_sequential_batch_parse_progress_route(kb_id):
    """获取知识库的顺序批量解析任务进度"""
    if request.method == "OPTIONS":
        response = success_response({})
        response.headers.add("Access-Control-Allow-Methods", "GET")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        return response

    try:
        result = KnowledgebaseService.get_sequential_batch_parse_progress(kb_id)
        # 直接返回从 service 获取的状态信息
        return success_response(data=result)
    except Exception as e:
        print(f"获取顺序批量解析进度路由处理失败 (KB ID: {kb_id}): {str(e)}")
        traceback.print_exc()
        return error_response(f"获取进度失败: {str(e)}", code=500)
    
@knowledgebase_bp.route('/embedding_models/<string:kb_id>', methods=['GET'])
def get_tenant_embedding_models(kb_id):
    """获取租户的嵌入模型配置"""
    try:
        # 调用服务函数获取嵌入模型配置
        result = KnowledgebaseService.get_tenant_embedding(kb_id)
        return success_response(data=result)
    except Exception as e:
        return error_response(f"获取租户嵌入模型配置失败: {str(e)}", code=500)
    
@knowledgebase_bp.route('/embedding_config', methods=['GET'])
def get_knowledgebase_embedding_config():
    """获取知识库的嵌入模型配置"""
    try:
        kb_id= request.args.get('kb_id', '')
        # 调用服务函数获取嵌入模型配置
        result = KnowledgebaseService.get_kb_embedding_config(kb_id)
        return success_response(data=result)
    except Exception as e:
        return error_response(f"获取知识库嵌入模型配置失败: {str(e)}", code=500)