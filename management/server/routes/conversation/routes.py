from flask import jsonify, request
from services.conversation.service import get_conversations_by_user_id, get_messages_by_conversation_id
from .. import conversation_bp


@conversation_bp.route("", methods=["GET"])
def get_conversations():
    """获取对话列表的API端点，支持分页和条件查询"""
    try:
        # 获取查询参数
        user_id = request.args.get("user_id")
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 20))
        sort_by = request.args.get("sort_by", "update_time")
        sort_order = request.args.get("sort_order", "desc")

        # 参数验证
        if not user_id:
            return jsonify({"code": 400, "message": "用户ID不能为空"}), 400

        # 调用服务函数获取分页和筛选后的对话数据
        conversations, total = get_conversations_by_user_id(user_id, page, size, sort_by, sort_order)

        # 返回符合前端期望格式的数据
        return jsonify({"code": 0, "data": {"list": conversations, "total": total}, "message": "获取对话列表成功"})
    except Exception as e:
        # 错误处理
        return jsonify({"code": 500, "message": f"获取对话列表失败: {str(e)}"}), 500


@conversation_bp.route("/<conversation_id>/messages", methods=["GET"])
def get_messages(conversation_id):
    """获取特定对话的消息列表"""
    try:
        # 获取查询参数
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 30))

        # 调用服务函数获取消息数据
        messages, total = get_messages_by_conversation_id(conversation_id, page, size)

        # 返回符合前端期望格式的数据
        return jsonify({"code": 0, "data": {"list": messages, "total": total}, "message": "获取消息列表成功"})
    except Exception as e:
        # 错误处理
        return jsonify({"code": 500, "message": f"获取消息列表失败: {str(e)}"}), 500
