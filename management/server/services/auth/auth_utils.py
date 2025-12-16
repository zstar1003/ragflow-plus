import os
import jwt
from flask import request

JWT_SECRET = os.getenv("MANAGEMENT_JWT_SECRET", "your-secret-key")


def get_current_user_from_token():
    """
    从请求头的JWT token中获取当前用户信息
    返回: dict 包含 user_id, username, role, tenant_id 或 None
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            return {
                'user_id': payload.get('user_id'),
                'username': payload.get('username'),
                'role': payload.get('role'),
                'tenant_id': payload.get('tenant_id')
            }
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    except Exception:
        return None


def is_admin(user_info):
    """检查用户是否是超级管理员"""
    if not user_info:
        return False
    return user_info.get('role') == 'admin'


def is_team_owner(user_info):
    """检查用户是否是团队负责人"""
    if not user_info:
        return False
    return user_info.get('role') == 'team_owner'
