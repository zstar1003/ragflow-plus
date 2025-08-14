from flask import jsonify, request
from services.users.service import get_users_with_pagination, delete_user, create_user, update_user, reset_user_password
from .. import users_bp

@users_bp.route('', methods=['GET'])
def get_users():
    """사용자 목록 API 엔드포인트 (페이지네이션 및 조건 검색 지원)"""
    try:
        # 쿼리 파라미터 가져오기
        current_page = int(request.args.get('currentPage', 1))
        page_size = int(request.args.get('size', 10))
        username = request.args.get('username', '')
        email = request.args.get('email', '')
        sort_by = request.args.get("sort_by", "create_time")
        sort_order = request.args.get("sort_order", "desc")
        
        # 서비스 함수 호출하여 페이지네이션 및 필터링된 사용자 데이터 가져오기
        users, total = get_users_with_pagination(current_page, page_size, username, email, sort_by, sort_order)
        
        # 프론트엔드 기대 포맷으로 데이터 반환
        return jsonify({
            "code": 0,  # 성공 상태 코드
            "data": {
                "list": users,
                "total": total
            },
            "message": "사용자 목록 가져오기 성공"
        })
    except Exception as e:
        # 오류 처리
        return jsonify({
            "code": 500,
            "message": f"사용자 목록 가져오기 실패: {str(e)}"
        }), 500

@users_bp.route('/<string:user_id>', methods=['DELETE'])
def delete_user_route(user_id):
    """사용자 삭제 API 엔드포인트"""
    delete_user(user_id)
    return jsonify({
        "code": 0,
        "message": f"사용자 {user_id} 삭제 성공"
    })

@users_bp.route('', methods=['POST'])
def create_user_route():
    """사용자 생성 API 엔드포인트"""
    data = request.json
    # 사용자 생성
    try:
        success = create_user(user_data=data)
        if success:
            return jsonify({
                "code": 0,
                "message": "사용자 생성 성공"
            })
        else:
            return jsonify({
                "code": 400,
                "message": "사용자 생성 실패"
            }), 400
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"사용자 생성 실패: {str(e)}"
        }), 500

@users_bp.route('/<string:user_id>', methods=['PUT'])
def update_user_route(user_id):
    """사용자 정보 수정 API 엔드포인트"""
    data = request.json
    user_id = data.get('id')
    update_user(user_id=user_id, user_data=data)
    return jsonify({
        "code": 0,
        "message": f"사용자 {user_id} 수정 성공"
    })

@users_bp.route('/me', methods=['GET'])
def get_current_user():
    return jsonify({
        "code": 0,
        "data": {
            "username": "admin",
            "roles": ["admin"]
        },
        "message": "사용자 정보 가져오기 성공"
    })

@users_bp.route('/<string:user_id>/reset-password', methods=['PUT'])
def reset_password_route(user_id):
    """
    사용자 비밀번호 재설정 API 엔드포인트
    Args:
        user_id (str): 비밀번호를 재설정할 사용자 ID
    Returns:
        Response: JSON 응답
    """
    try:
        data = request.json
        new_password = data.get('password')

        # 비밀번호 존재 여부 확인
        if not new_password:
            return jsonify({"code": 400, "message": "새 비밀번호 파라미터 'password'가 없습니다"}), 400

        # 서비스 함수 호출하여 비밀번호 재설정
        success = reset_user_password(user_id=user_id, new_password=new_password)

        if success:
            return jsonify({
                "code": 0,
                "message": "사용자 비밀번호 재설정 성공"
            })
        else:
            # service 계층에서 사용자가 없거나 기타 사유로 False 반환 가능
            return jsonify({"code": 404, "message": "사용자를 찾을 수 없거나 비밀번호 재설정 실패"}), 404
    except Exception as e:
        # 예외 일괄 처리
        return jsonify({
            "code": 500,
            "message": f"비밀번호 재설정 실패: {str(e)}"
        }), 500