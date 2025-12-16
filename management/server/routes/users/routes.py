import os
import jwt
from flask import jsonify, request
from services.users.service import get_users_with_pagination, delete_user, create_user, update_user, reset_user_password, get_user_info_by_id
from .. import users_bp

JWT_SECRET = os.getenv("MANAGEMENT_JWT_SECRET", "your-secret-key")

@users_bp.route('', methods=['GET'])
def get_users():
    """获取用户的API端点,支持分页和条件查询"""
    try:
        # 获取查询参数
        current_page = int(request.args.get('currentPage', 1))
        page_size = int(request.args.get('size', 10))
        username = request.args.get('username', '')
        email = request.args.get('email', '')
        sort_by = request.args.get("sort_by", "create_time")
        sort_order = request.args.get("sort_order", "desc")
        
        # 调用服务函数获取分页和筛选后的用户数据
        users, total = get_users_with_pagination(current_page, page_size, username, email, sort_by, sort_order)
        
        # 返回符合前端期望格式的数据
        return jsonify({
            "code": 0,  # 成功状态码
            "data": {
                "list": users,
                "total": total
            },
            "message": "获取用户列表成功"
        })
    except Exception as e:
        # 错误处理
        return jsonify({
            "code": 500,
            "message": f"获取用户列表失败: {str(e)}"
        }), 500

@users_bp.route('/<string:user_id>', methods=['DELETE'])
def delete_user_route(user_id):
    """删除用户的API端点"""
    delete_user(user_id)
    return jsonify({
        "code": 0,
        "message": f"用户 {user_id} 删除成功"
    })

@users_bp.route('', methods=['POST'])
def create_user_route():
    """创建用户的API端点"""
    data = request.json
    # 创建用户
    try:
        success = create_user(user_data=data)
        if success:
            return jsonify({
                "code": 0,
                "message": "用户创建成功"
            })
        else:
            return jsonify({
                "code": 400,
                "message": "用户创建失败"
            }), 400
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"用户创建失败: {str(e)}"
        }), 500

@users_bp.route('/<string:user_id>', methods=['PUT'])
def update_user_route(user_id):
    """更新用户的API端点"""
    data = request.json
    user_id = data.get('id')
    update_user(user_id=user_id, user_data=data)
    return jsonify({
        "code": 0,
        "message": f"用户 {user_id} 更新成功"
    })

@users_bp.route('/me', methods=['GET'])
def get_current_user():
    """获取当前登录用户信息"""
    try:
        # 从请求头获取token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"code": 401, "message": "未提供有效的认证令牌"}), 401
        
        token = auth_header.split(' ')[1]
        
        # 解析token
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"code": 401, "message": "令牌已过期"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"code": 401, "message": "无效的令牌"}), 401
        
        user_id = payload.get('user_id')
        
        # 从数据库获取用户信息
        user_info = get_user_info_by_id(user_id)
        
        if not user_info:
            return jsonify({"code": 401, "message": "用户不存在或无权限"}), 401
        
        return jsonify({
            "code": 0,
            "data": {
                "username": user_info['username'],
                "roles": user_info['roles'],
                "role": user_info['role'],
                "tenant_id": user_info.get('tenant_id')
            },
            "message": "获取用户信息成功"
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"获取用户信息失败: {str(e)}"
        }), 500

@users_bp.route('/<string:user_id>/reset-password', methods=['PUT'])
def reset_password_route(user_id):
    """
    重置用户密码的API端点
    Args:
        user_id (str): 需要重置密码的用户ID
    Returns:
        Response: JSON响应
    """
    try:
        data = request.json
        new_password = data.get('password')

        # 校验密码是否存在
        if not new_password:
            return jsonify({"code": 400, "message": "缺少新密码参数 'password'"}), 400

        # 调用 service 函数重置密码
        success = reset_user_password(user_id=user_id, new_password=new_password)

        if success:
            return jsonify({
                "code": 0,
                "message": "用户密码重置成功"
            })
        else:
            # service 层可能因为用户不存在或其他原因返回 False
            return jsonify({"code": 404, "message": "用户未找到或密码重置失败"}), 404
    except Exception as e:
        # 统一处理异常
        return jsonify({
            "code": 500,
            "message": f"重置密码失败: {str(e)}"
        }), 500