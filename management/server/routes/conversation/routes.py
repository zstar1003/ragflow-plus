from flask import jsonify, request
from services.conversation.service import get_conversations_by_user_id, get_messages_by_conversation_id
from .. import conversation_bp


@conversation_bp.route("", methods=["GET"])
def get_conversations():
    """대화 목록 API 엔드포인트, 페이징 및 조건 조회 지원"""
    try:
        # 쿼리 파라미터 가져오기
        user_id = request.args.get("user_id")
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 20))
        sort_by = request.args.get("sort_by", "update_time")
        sort_order = request.args.get("sort_order", "desc")

        # 파라미터 검증
        if not user_id:
            return jsonify({"code": 400, "message": "사용자 ID는 비워둘 수 없습니다."}), 400

        # 서비스 함수 호출로 페이징 및 필터링된 대화 데이터 가져오기
        conversations, total = get_conversations_by_user_id(user_id, page, size, sort_by, sort_order)

        # 프론트엔드 기대 포맷으로 반환
        return jsonify({"code": 0, "data": {"list": conversations, "total": total}, "message": "대화 목록을 성공적으로 가져왔습니다."})
    except Exception as e:
        # 오류 처리
        return jsonify({"code": 500, "message": f"대화 목록 조회 실패: {str(e)}"}), 500


@conversation_bp.route("/<conversation_id>/messages", methods=["GET"])
def get_messages(conversation_id):
    """특정 대화의 메시지 목록 조회"""
    try:
        # 쿼리 파라미터 가져오기
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 30))

        # 서비스 함수 호출로 메시지 데이터 가져오기
        messages, total = get_messages_by_conversation_id(conversation_id, page, size)

        # 프론트엔드 기대 포맷으로 반환
        return jsonify({"code": 0, "data": {"list": messages, "total": total}, "message": "메시지 목록을 성공적으로 가져왔습니다."})
    except Exception as e:
        # 오류 처리
        return jsonify({"code": 500, "message": f"메시지 목록 조회 실패: {str(e)}"}), 500
