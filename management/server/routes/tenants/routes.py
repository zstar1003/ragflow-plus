from flask import jsonify, request
from services.tenants.service import get_tenants_with_pagination, update_tenant
from .. import tenants_bp

@tenants_bp.route('', methods=['GET'])
def get_tenants():
    """테넌트 목록 API 엔드포인트 (페이지네이션 및 조건 검색 지원)"""
    try:
        # 쿼리 파라미터 가져오기
        current_page = int(request.args.get('currentPage', 1))
        page_size = int(request.args.get('size', 10))
        username = request.args.get('username', '')
        
        # 서비스 함수 호출하여 페이지네이션 및 필터링된 테넌트 데이터 가져오기
        tenants, total = get_tenants_with_pagination(current_page, page_size, username)
        
        # 프론트엔드 기대 포맷으로 데이터 반환
        return jsonify({
            "code": 0,
            "data": {
                "list": tenants,
                "total": total
            },
            "message": "테넌트 목록 가져오기 성공"
        })
    except Exception as e:
        # 오류 처리
        return jsonify({
            "code": 500,
            "message": f"테넌트 목록 가져오기 실패: {str(e)}"
        }), 500

@tenants_bp.route('/<string:tenant_id>', methods=['PUT'])
def update_tenant_route(tenant_id):
    """테넌트 정보 수정 API 엔드포인트"""
    try:
        data = request.json
        success = update_tenant(tenant_id=tenant_id, tenant_data=data)
        if success:
            return jsonify({
                "code": 0,
                "message": f"테넌트 {tenant_id} 수정 성공"
            })
        else:
            return jsonify({
                "code": 404,
                "message": f"테넌트 {tenant_id} 이(가) 존재하지 않거나 수정 실패"
            }), 404
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"테넌트 수정 실패: {str(e)}"
        }), 500