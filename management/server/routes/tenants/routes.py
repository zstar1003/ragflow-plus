from flask import jsonify, request
from services.tenants.service import get_tenants_with_pagination, update_tenant
from .. import tenants_bp

@tenants_bp.route('', methods=['GET'])
def get_tenants():
    """获取租户列表的API端点，支持分页和条件查询"""
    try:
        # 获取查询参数
        current_page = int(request.args.get('currentPage', 1))
        page_size = int(request.args.get('size', 10))
        username = request.args.get('username', '')
        
        # 调用服务函数获取分页和筛选后的租户数据
        tenants, total = get_tenants_with_pagination(current_page, page_size, username)
        
        # 返回符合前端期望格式的数据
        return jsonify({
            "code": 0,
            "data": {
                "list": tenants,
                "total": total
            },
            "message": "获取租户列表成功"
        })
    except Exception as e:
        # 错误处理
        return jsonify({
            "code": 500,
            "message": f"获取租户列表失败: {str(e)}"
        }), 500

@tenants_bp.route('/<string:tenant_id>', methods=['PUT'])
def update_tenant_route(tenant_id):
    """更新租户的API端点"""
    try:
        data = request.json
        success = update_tenant(tenant_id=tenant_id, tenant_data=data)
        if success:
            return jsonify({
                "code": 0,
                "message": f"租户 {tenant_id} 更新成功"
            })
        else:
            return jsonify({
                "code": 404,
                "message": f"租户 {tenant_id} 不存在或更新失败"
            }), 404
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"更新租户失败: {str(e)}"
        }), 500