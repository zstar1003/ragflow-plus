from flask import jsonify, request
from services.teams.service import get_teams_with_pagination, get_team_by_id, delete_team, get_team_members, add_team_member, remove_team_member
from .. import teams_bp

@teams_bp.route('', methods=['GET'])
def get_teams():
    """팀 목록 API 엔드포인트 (페이지네이션 및 조건 검색 지원)"""
    try:
        # 쿼리 파라미터 가져오기
        current_page = int(request.args.get('currentPage', 1))
        page_size = int(request.args.get('size', 10))
        team_name = request.args.get('name', '')
        sort_by = request.args.get("sort_by", "create_time")
        sort_order = request.args.get("sort_order", "desc")
        
        # 서비스 함수 호출하여 페이지네이션 및 필터링된 팀 데이터 가져오기
        teams, total = get_teams_with_pagination(current_page, page_size, team_name, sort_by, sort_order)
        
        # 프론트엔드 기대 포맷으로 데이터 반환
        return jsonify({
            "code": 0,
            "data": {
                "list": teams,
                "total": total
            },
            "message": "팀 목록 가져오기 성공"
        })
    except Exception as e:
        # 오류 처리
        return jsonify({
            "code": 500,
            "message": f"팀 목록 가져오기 실패: {str(e)}"
        }), 500

@teams_bp.route('/<string:team_id>', methods=['GET'])
def get_team(team_id):
    """단일 팀 상세 정보 API 엔드포인트"""
    try:
        team = get_team_by_id(team_id)
        if team:
            return jsonify({
                "code": 0,
                "data": team,
                "message": "팀 상세 정보 가져오기 성공"
            })
        else:
            return jsonify({
                "code": 404,
                "message": f"팀 {team_id} 이(가) 존재하지 않습니다"
            }), 404
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"팀 상세 정보 가져오기 실패: {str(e)}"
        }), 500


@teams_bp.route('/<string:team_id>', methods=['DELETE'])
def delete_team_route(team_id):
    """팀 삭제 API 엔드포인트"""
    try:
        success = delete_team(team_id)
        if success:
            return jsonify({
                "code": 0,
                "message": f"팀 {team_id} 삭제 성공"
            })
        else:
            return jsonify({
                "code": 404,
                "message": f"팀 {team_id} 이(가) 존재하지 않거나 삭제 실패"
            }), 404
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"팀 삭제 실패: {str(e)}"
        }), 500

@teams_bp.route('/<string:team_id>/members', methods=['GET'])
def get_team_members_route(team_id):
    """팀 멤버 조회 API 엔드포인트"""
    try:
        print(f"팀 {team_id} 멤버를 조회 중입니다")
        members = get_team_members(team_id)
        print(f"조회 결과: {len(members)}명의 멤버를 찾았습니다")
        return jsonify({
            "code": 0,
            "data": members,
            "message": "팀 멤버 조회 성공"
        })
    except Exception as e:
        print(f"팀 멤버 조회 예외: {str(e)}")
        return jsonify({
            "code": 500,
            "message": f"팀 멤버 조회 실패: {str(e)}"
        }), 500

@teams_bp.route('/<string:team_id>/members', methods=['POST'])
def add_team_member_route(team_id):
    """팀 멤버 추가 API 엔드포인트"""
    try:
        data = request.json
        user_id = data.get('userId')
        role = data.get('role', 'member')
        success = add_team_member(team_id, user_id, role)
        if success:
            return jsonify({
                "code": 0,
                "message": "팀 멤버 추가 성공"
            })
        else:
            return jsonify({
                "code": 400,
                "message": "팀 멤버 추가 실패"
            }), 400
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"팀 멤버 추가 실패: {str(e)}"
        }), 500

@teams_bp.route('/<string:team_id>/members/<string:user_id>', methods=['DELETE'])
def remove_team_member_route(team_id, user_id):
    """팀 멤버 제거 API 엔드포인트"""
    try:
        success = remove_team_member(team_id, user_id)
        if success:
            return jsonify({
                "code": 0,
                "message": "팀 멤버 제거 성공"
            })
        else:
            return jsonify({
                "code": 400,
                "message": "팀 멤버 제거 실패"
            }), 400
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"팀 멤버 제거 실패: {str(e)}"
        }), 500