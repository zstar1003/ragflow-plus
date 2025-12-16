from flask import jsonify, request
from services.teams.service import get_teams_with_pagination, get_team_by_id, delete_team, get_team_members, add_team_member, remove_team_member
from services.auth import get_current_user_from_token, is_admin
from .. import teams_bp

@teams_bp.route('', methods=['GET'])
def get_teams():
    """获取团队列表的API端点，支持分页和条件查询"""
    try:
        # 获取当前用户信息
        current_user = get_current_user_from_token()
        
        # 获取查询参数
        current_page = int(request.args.get('currentPage', 1))
        page_size = int(request.args.get('size', 10))
        team_name = request.args.get('name', '')
        sort_by = request.args.get("sort_by", "create_time")
        sort_order = request.args.get("sort_order", "desc")
        
        # 如果是团队负责人，只返回其自己的团队
        tenant_id = None
        if current_user and not is_admin(current_user):
            tenant_id = current_user.get("tenant_id")
        
        # 调用服务函数获取分页和筛选后的团队数据
        teams, total = get_teams_with_pagination(current_page, page_size, team_name, sort_by, sort_order, tenant_id)
        
        # 返回符合前端期望格式的数据
        return jsonify({
            "code": 0,
            "data": {
                "list": teams,
                "total": total
            },
            "message": "获取团队列表成功"
        })
    except Exception as e:
        # 错误处理
        return jsonify({
            "code": 500,
            "message": f"获取团队列表失败: {str(e)}"
        }), 500

@teams_bp.route('/<string:team_id>', methods=['GET'])
def get_team(team_id):
    """获取单个团队详情的API端点"""
    try:
        team = get_team_by_id(team_id)
        if team:
            return jsonify({
                "code": 0,
                "data": team,
                "message": "获取团队详情成功"
            })
        else:
            return jsonify({
                "code": 404,
                "message": f"团队 {team_id} 不存在"
            }), 404
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"获取团队详情失败: {str(e)}"
        }), 500


@teams_bp.route('/<string:team_id>', methods=['DELETE'])
def delete_team_route(team_id):
    """删除团队的API端点"""
    try:
        success = delete_team(team_id)
        if success:
            return jsonify({
                "code": 0,
                "message": f"团队 {team_id} 删除成功"
            })
        else:
            return jsonify({
                "code": 404,
                "message": f"团队 {team_id} 不存在或删除失败"
            }), 404
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"删除团队失败: {str(e)}"
        }), 500

@teams_bp.route('/<string:team_id>/members', methods=['GET'])
def get_team_members_route(team_id):
    """获取团队成员的API端点"""
    try:
        print(f"正在查询团队 {team_id} 的成员")
        members = get_team_members(team_id)
        print(f"查询结果: 找到 {len(members)} 个成员")
        
        return jsonify({
            "code": 0,
            "data": members,
            "message": "获取团队成员成功"
        })
    except Exception as e:
        print(f"获取团队成员异常: {str(e)}")
        return jsonify({
            "code": 500,
            "message": f"获取团队成员失败: {str(e)}"
        }), 500

@teams_bp.route('/<string:team_id>/members', methods=['POST'])
def add_team_member_route(team_id):
    """添加团队成员的API端点"""
    try:
        data = request.json
        user_id = data.get('userId')
        role = data.get('role', 'member')
        success = add_team_member(team_id, user_id, role)
        if success:
            return jsonify({
                "code": 0,
                "message": "添加团队成员成功"
            })
        else:
            return jsonify({
                "code": 400,
                "message": "添加团队成员失败"
            }), 400
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"添加团队成员失败: {str(e)}"
        }), 500

@teams_bp.route('/<string:team_id>/members/<string:user_id>', methods=['DELETE'])
def remove_team_member_route(team_id, user_id):
    """移除团队成员的API端点"""
    try:
        success = remove_team_member(team_id, user_id)
        if success:
            return jsonify({
                "code": 0,
                "message": "移除团队成员成功"
            })
        else:
            return jsonify({
                "code": 400,
                "message": "移除团队成员失败"
            }), 400
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"移除团队成员失败: {str(e)}"
        }), 500