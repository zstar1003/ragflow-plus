import traceback

from flask import request
from services.knowledgebases.service import KnowledgebaseService
from utils import error_response, success_response

from .. import knowledgebase_bp


@knowledgebase_bp.route("", methods=["GET"])
def get_knowledgebase_list():
    """지식베이스 목록 가져오기"""
    try:
        params = {
            "page": int(request.args.get("currentPage", 1)),
            "size": int(request.args.get("size", 10)),
            "name": request.args.get("name", ""),
            "sort_by": request.args.get("sort_by", "create_time"),
            "sort_order": request.args.get("sort_order", "desc"),
        }
        result = KnowledgebaseService.get_knowledgebase_list(**params)
        return success_response(result)
    except ValueError:
        return error_response("파라미터 타입 오류", code=400)
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/<string:kb_id>", methods=["GET"])
def get_knowledgebase_detail(kb_id):
    """지식베이스 상세 정보 가져오기"""
    try:
        knowledgebase = KnowledgebaseService.get_knowledgebase_detail(kb_id=kb_id)
        if not knowledgebase:
            return error_response("지식베이스가 존재하지 않습니다", code=404)
        return success_response(knowledgebase)
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("", methods=["POST"])
def create_knowledgebase():
    """지식베이스 생성"""
    try:
        data = request.json
        if not data.get("name"):
            return error_response("지식베이스 이름은 비워둘 수 없습니다", code=400)

        # created_by 파라미터 제거
        kb = KnowledgebaseService.create_knowledgebase(**data)
        return success_response(kb, "생성 성공", code=0)
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/<string:kb_id>", methods=["PUT"])
def update_knowledgebase(kb_id):
    """지식베이스 업데이트"""
    try:
        data = request.json
        kb = KnowledgebaseService.update_knowledgebase(kb_id=kb_id, **data)
        if not kb:
            return error_response("지식베이스가 존재하지 않습니다", code=404)
        return success_response(kb)
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/<string:kb_id>", methods=["DELETE"])
def delete_knowledgebase(kb_id):
    """지식베이스 삭제"""
    try:
        result = KnowledgebaseService.delete_knowledgebase(kb_id=kb_id)
        if not result:
            return error_response("지식베이스가 존재하지 않습니다", code=404)
        return success_response(message="삭제 성공")
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/batch", methods=["DELETE"])
def batch_delete_knowledgebase():
    """지식베이스 일괄 삭제"""
    try:
        data = request.json
        if not data or not data.get("ids"):
            return error_response("삭제할 지식베이스를 선택하세요", code=400)

        result = KnowledgebaseService.batch_delete_knowledgebase(kb_ids=data["ids"])
        return success_response(message=f"{result}개의 지식베이스를 성공적으로 삭제했습니다")
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/<string:kb_id>/documents", methods=["GET"])
def get_knowledgebase_documents(kb_id):
    """지식베이스 내 문서 목록 가져오기"""
    try:
        params = {
            "kb_id": kb_id,
            "page": int(request.args.get("currentPage", 1)),
            "size": int(request.args.get("size", 10)),
            "name": request.args.get("name", ""),
            "sort_by": request.args.get("sort_by", "create_time"),
            "sort_order": request.args.get("sort_order", "desc"),
        }
        result = KnowledgebaseService.get_knowledgebase_documents(**params)
        return success_response(result)
    except ValueError:
        return error_response("파라미터 타입 오류", code=400)
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/<string:kb_id>/documents", methods=["POST"])
def add_documents_to_knowledgebase(kb_id):
    """지식베이스에 문서 추가"""
    try:
        print(f"[DEBUG] 문서 추가 요청 수신, kb_id: {kb_id}")
        data = request.json
        if not data:
            print("[ERROR] 요청 데이터가 비어 있음")
            return error_response("요청 데이터는 비워둘 수 없습니다", code=400)

        file_ids = data.get("file_ids", [])
        print(f"[DEBUG] 수신된 file_ids: {file_ids}, 타입: {type(file_ids)}")

        try:
            result = KnowledgebaseService.add_documents_to_knowledgebase(kb_id=kb_id, file_ids=file_ids)
            print(f"[DEBUG] 서비스 계층 처리 성공, 결과: {result}")
            return success_response(data=result, message="추가 성공", code=201)
        except Exception as service_error:
            print(f"[ERROR] 서비스 계층 오류 상세: {str(service_error)}")
            traceback.print_exc()
            return error_response(str(service_error), code=500)

    except Exception as e:
        print(f"[ERROR] 라우터 계층 오류 상세: {str(e)}")
        traceback.print_exc()
        return error_response(str(e), code=500)


@knowledgebase_bp.route("/documents/<string:doc_id>", methods=["DELETE", "OPTIONS"])
def delete_document(doc_id):
    """문서 삭제"""
    # OPTIONS 사전 요청 처리
    if request.method == "OPTIONS":
        response = success_response({})
        # CORS 관련 헤더 추가
        response.headers.add("Access-Control-Allow-Methods", "DELETE")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        return response

    try:
        KnowledgebaseService.delete_document(doc_id)
        return success_response(message="삭제 성공")
    except Exception as e:
        return error_response(str(e))


@knowledgebase_bp.route("/documents/<doc_id>/parse/progress", methods=["GET"])
def get_parse_progress(doc_id):
    """문서 파싱 진행 상황 가져오기"""
    # OPTIONS 사전 요청 처리
    if request.method == "OPTIONS":
        response = success_response({})
        # CORS 관련 헤더 추가
        response.headers.add("Access-Control-Allow-Methods", "GET")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        return response

    try:
        result = KnowledgebaseService.get_document_parse_progress(doc_id)
        if isinstance(result, dict) and "error" in result:
            return error_response(result["error"], code=404)
        return success_response(data=result)
    except Exception as e:
        print(f"파싱 진행 상황 가져오기 실패: {str(e)}")
        return error_response("파싱이 진행 중입니다. 잠시 후 다시 시도해 주세요", code=202)


# 시스템 임베딩 설정 라우트 가져오기
@knowledgebase_bp.route("/system_embedding_config", methods=["GET"])
def get_system_embedding_config_route():
    """시스템 임베딩 설정 API 엔드포인트 가져오기"""
    try:
        config_data = KnowledgebaseService.get_system_embedding_config()
        return success_response(data=config_data)
    except Exception as e:
        print(f"시스템 임베딩 설정 가져오기 실패: {str(e)}")
        return error_response(message=f"설정 가져오기 실패: {str(e)}", code=500)  # 일반 오류 메시지 반환


# 시스템 임베딩 설정 라우트 설정
@knowledgebase_bp.route("/system_embedding_config", methods=["POST"])
def set_system_embedding_config_route():
    """시스템 임베딩 설정 API 엔드포인트 설정"""
    try:
        data = request.json
        if not data:
            return error_response("요청 데이터는 비워둘 수 없습니다", code=400)

        llm_name = data.get("llm_name", "").strip()
        api_base = data.get("api_base", "").strip()
        api_key = data.get("api_key", "").strip()  # 允许空

        if not llm_name or not api_base:
            return error_response("모델 이름과 API 주소는 비워둘 수 없습니다", code=400)

        # 서비스 계층 호출(연결 테스트 및 DB 작업 포함)
        success, message = KnowledgebaseService.set_system_embedding_config(llm_name=llm_name, api_base=api_base, api_key=api_key)

        if success:
            return success_response(message=message)
        else:
            # 서비스 계층에서 실패(예: 연결 테스트 실패 또는 DB 오류) 시 메시지를 프론트엔드에 반환
            return error_response(message=message, code=400)  # 400은 작업 실패를 의미

    except Exception as e:
        # 라우터 계층 또는 예기치 않은 서비스 계층 예외 포착
        print(f"시스템 임베딩 설정 실패: {str(e)}")
        return error_response(message=f"설정 중 내부 오류 발생: {str(e)}", code=500)


@knowledgebase_bp.route("/documents/<doc_id>/parse", methods=["POST"])
def parse_document(doc_id):
    """문서 파싱 시작"""
    if request.method == "OPTIONS":
        response = success_response({})
        response.headers.add("Access-Control-Allow-Methods", "POST")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        return response

    try:
        result = KnowledgebaseService.parse_document(doc_id)
        if result.get("success"):
            return success_response(data={"message": f"문서 {doc_id} 동기 파싱 완료.", "details": result})
        else:
            return error_response(result.get("message", "파싱 실패"), code=500)

    except Exception as e:
        return error_response(str(e), code=500)


# 순차적 일괄 파싱 라우트 시작
@knowledgebase_bp.route("/<string:kb_id>/batch_parse_sequential/start", methods=["POST"])
def start_sequential_batch_parse_route(kb_id):
    """지식베이스의 순차적 일괄 파싱 작업 비동기 시작"""
    if request.method == "OPTIONS":
        response = success_response({})
        response.headers.add("Access-Control-Allow-Methods", "POST")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        return response

    try:
        result = KnowledgebaseService.start_sequential_batch_parse_async(kb_id)
        if result.get("success"):
            return success_response(data={"message": result.get("message")})
        else:
            # 작업이 이미 실행 중이거나 시작에 실패한 경우 오류 메시지 반환
            return error_response(result.get("message", "시작 실패"), code=409 if "已在运行中" in result.get("message", "") else 500)
    except Exception as e:
        print(f"순차적 일괄 파싱 라우트 처리 실패 (KB ID: {kb_id}): {str(e)}")
        traceback.print_exc()
        return error_response(f"순차적 일괄 파싱 시작 실패: {str(e)}", code=500)


# 순차적 일괄 파싱 진행 상황 라우트 가져오기
@knowledgebase_bp.route("/<string:kb_id>/batch_parse_sequential/progress", methods=["GET"])
def get_sequential_batch_parse_progress_route(kb_id):
    """지식베이스의 순차적 일괄 파싱 작업 진행 상황 가져오기"""
    if request.method == "OPTIONS":
        response = success_response({})
        response.headers.add("Access-Control-Allow-Methods", "GET")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        return response

    try:
        result = KnowledgebaseService.get_sequential_batch_parse_progress(kb_id)
        # 서비스에서 가져온 상태 정보 바로 반환
        return success_response(data=result)
    except Exception as e:
        print(f"순차적 일괄 파싱 진행 상황 라우트 처리 실패 (KB ID: {kb_id}): {str(e)}")
        traceback.print_exc()
        return error_response(f"진행 상황 가져오기 실패: {str(e)}", code=500)
    
@knowledgebase_bp.route('/embedding_models/<string:kb_id>', methods=['GET'])
def get_tenant_embedding_models(kb_id):
    """테넌트의 임베딩 모델 설정 가져오기"""
    try:
        # 서비스 함수 호출하여 임베딩 모델 설정 가져오기
        result = KnowledgebaseService.get_tenant_embedding(kb_id)
        return success_response(data=result)
    except Exception as e:
        return error_response(f"테넌트 임베딩 모델 설정 가져오기 실패: {str(e)}", code=500)
    
@knowledgebase_bp.route('/embedding_config', methods=['GET'])
def get_knowledgebase_embedding_config():
    """지식베이스의 임베딩 모델 설정 가져오기"""
    try:
        kb_id= request.args.get('kb_id', '')
        # 서비스 함수 호출하여 임베딩 모델 설정 가져오기
        result = KnowledgebaseService.get_kb_embedding_config(kb_id)
        return success_response(data=result)
    except Exception as e:
        return error_response(f"지식베이스 임베딩 모델 설정 가져오기 실패: {str(e)}", code=500)