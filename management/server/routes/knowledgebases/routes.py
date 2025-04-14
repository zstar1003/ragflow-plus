from flask import Blueprint, request
from services.knowledgebases.service import KnowledgebaseService
from utils import success_response, error_response
from .. import knowledgebase_bp

@knowledgebase_bp.route('', methods=['GET'])
def get_knowledgebase_list():
    """获取知识库列表"""
    try:
        params = {
            'page': int(request.args.get('currentPage', 1)),
            'size': int(request.args.get('size', 10)),
            'name': request.args.get('name', '')
        }
        result = KnowledgebaseService.get_knowledgebase_list(**params)
        return success_response(result)
    except ValueError as e:
        return error_response("参数类型错误", code=400)
    except Exception as e:
        return error_response(str(e))

@knowledgebase_bp.route('/<string:kb_id>', methods=['GET'])
def get_knowledgebase_detail(kb_id):
    """获取知识库详情"""
    try:
        knowledgebase = KnowledgebaseService.get_knowledgebase_detail(
            kb_id=kb_id
        )
        if not knowledgebase:
            return error_response('知识库不存在', code=404)
        return success_response(knowledgebase)
    except Exception as e:
        return error_response(str(e))

@knowledgebase_bp.route('', methods=['POST'])
def create_knowledgebase():
    """创建知识库"""
    try:
        data = request.json
        if not data.get('name'):
            return error_response('知识库名称不能为空', code=400)
            
        # 移除 created_by 参数
        kb = KnowledgebaseService.create_knowledgebase(**data)
        return success_response(kb, "创建成功", code=0)
    except Exception as e:
        return error_response(str(e))

@knowledgebase_bp.route('/<string:kb_id>', methods=['PUT'])
def update_knowledgebase(kb_id):
    """更新知识库"""
    try:
        data = request.json
        kb = KnowledgebaseService.update_knowledgebase(
            kb_id=kb_id,
            **data
        )
        if not kb:
            return error_response('知识库不存在', code=404)
        return success_response(kb)
    except Exception as e:
        return error_response(str(e))

@knowledgebase_bp.route('/<string:kb_id>', methods=['DELETE'])
def delete_knowledgebase(kb_id):
    """删除知识库"""
    try:
        result = KnowledgebaseService.delete_knowledgebase(
            kb_id=kb_id
        )
        if not result:
            return error_response('知识库不存在', code=404)
        return success_response(message='删除成功')
    except Exception as e:
        return error_response(str(e))

@knowledgebase_bp.route('/batch', methods=['DELETE'])
def batch_delete_knowledgebase():
    """批量删除知识库"""
    try:
        data = request.json
        if not data or not data.get('ids'):
            return error_response('请选择要删除的知识库', code=400)
            
        result = KnowledgebaseService.batch_delete_knowledgebase(
            kb_ids=data['ids']
        )
        return success_response(message=f'成功删除 {result} 个知识库')
    except Exception as e:
        return error_response(str(e))

@knowledgebase_bp.route('/<string:kb_id>/documents', methods=['GET'])
def get_knowledgebase_documents(kb_id):
    """获取知识库下的文档列表"""
    try:
        params = {
            'kb_id': kb_id,
            'page': int(request.args.get('currentPage', 1)),
            'size': int(request.args.get('size', 10)),
            'name': request.args.get('name', '')
        }
        result = KnowledgebaseService.get_knowledgebase_documents(**params)
        return success_response(result)
    except ValueError as e:
        return error_response("参数类型错误", code=400)
    except Exception as e:
        return error_response(str(e))

@knowledgebase_bp.route('/<string:kb_id>/documents', methods=['POST'])
def add_documents_to_knowledgebase(kb_id):
    """添加文档到知识库"""
    try:
        print(f"[DEBUG] 接收到添加文档请求，kb_id: {kb_id}")
        data = request.json
        if not data:
            print("[ERROR] 请求数据为空")
            return error_response('请求数据不能为空', code=400)
            
        file_ids = data.get('file_ids', [])
        print(f"[DEBUG] 接收到的file_ids: {file_ids}, 类型: {type(file_ids)}")
        
        try:
            result = KnowledgebaseService.add_documents_to_knowledgebase(
                kb_id=kb_id,
                file_ids=file_ids
            )
            print(f"[DEBUG] 服务层处理成功，结果: {result}")
            return success_response(
                data=result,
                message="添加成功",
                code=201
            )
        except Exception as service_error:
            print(f"[ERROR] 服务层错误详情: {str(service_error)}")
            import traceback
            traceback.print_exc()
            return error_response(str(service_error), code=500)
            
    except Exception as e:
        print(f"[ERROR] 路由层错误详情: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(str(e), code=500)

@knowledgebase_bp.route('/documents/<string:doc_id>', methods=['DELETE', 'OPTIONS'])
def delete_document(doc_id):
    """删除文档"""
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        response = success_response({})
        # 添加 CORS 相关头
        response.headers.add('Access-Control-Allow-Methods', 'DELETE')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        return response
        
    try:
        KnowledgebaseService.delete_document(doc_id)
        return success_response(message="删除成功")
    except Exception as e:
        return error_response(str(e))