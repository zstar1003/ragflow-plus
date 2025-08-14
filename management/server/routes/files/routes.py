from io import BytesIO

from flask import current_app, jsonify, request, send_file
from services.files.service import batch_delete_files, delete_file, download_file_from_minio, get_file_info, get_files_list, handle_chunk_upload, merge_chunks, upload_files_to_server
from services.files.utils import FileType

from .. import files_bp

UPLOAD_FOLDER = "/data/uploads"
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "doc", "docx", "xls", "xlsx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@files_bp.route("/upload", methods=["POST"])
def upload_file():
    if "files" not in request.files:
        return jsonify({"code": 400, "message": "파일이 선택되지 않았습니다.", "data": None}), 400

    files = request.files.getlist("files")
    upload_result = upload_files_to_server(files)

    # 표준 포맷 반환
    return jsonify({"code": 0, "message": "업로드 성공", "data": upload_result["data"]})


@files_bp.route("", methods=["GET", "OPTIONS"])
def get_files():
    """파일 목록 API 엔드포인트"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        current_page = int(request.args.get("currentPage", 1))
        page_size = int(request.args.get("size", 10))
        name_filter = request.args.get("name", "")
        sort_by = request.args.get("sort_by", "create_time")
        sort_order = request.args.get("sort_order", "desc")

        result, total = get_files_list(current_page, page_size, name_filter, sort_by, sort_order)

        return jsonify({"code": 0, "data": {"list": result, "total": total}, "message": "파일 목록을 성공적으로 가져왔습니다."})

    except Exception as e:
        return jsonify({"code": 500, "message": f"파일 목록 조회 실패: {str(e)}"}), 500


@files_bp.route("/<string:file_id>/download", methods=["GET", "OPTIONS"])
def download_file(file_id):
    try:
        current_app.logger.info(f"파일 다운로드 요청 처리 시작: {file_id}")

        # 파일 정보 가져오기
        file = get_file_info(file_id)

        if not file:
            current_app.logger.error(f"파일이 존재하지 않음: {file_id}")
            return jsonify({"code": 404, "message": f"파일 {file_id} 이(가) 존재하지 않음", "details": "파일 레코드가 없거나 삭제됨"}), 404

        if file["type"] == FileType.FOLDER.value:
            current_app.logger.error(f"폴더는 다운로드할 수 없음: {file_id}")
            return jsonify({"code": 400, "message": "폴더는 다운로드할 수 없습니다.", "details": "다운로드할 파일을 선택하세요."}), 400

        current_app.logger.info(f"파일 정보 가져오기 성공: {file_id}, 저장 위치: {file['parent_id']}/{file['location']}")

        try:
            # MinIO에서 파일 다운로드
            file_data, filename = download_file_from_minio(file_id)

            # 메모리 파일 객체 생성
            file_stream = BytesIO(file_data)

            # 파일 반환
            return send_file(file_stream, download_name=filename, as_attachment=True, mimetype="application/octet-stream")

        except Exception as e:
            current_app.logger.error(f"파일 다운로드 실패: {str(e)}")
            return jsonify({"code": 500, "message": "파일 다운로드 실패", "details": str(e)}), 500

    except Exception as e:
        current_app.logger.error(f"다운로드 요청 처리 중 오류 발생: {str(e)}")
        return jsonify({"code": 500, "message": "다운로드 요청 처리 중 오류 발생", "details": str(e)}), 500


@files_bp.route("/<string:file_id>", methods=["DELETE", "OPTIONS"])
def delete_file_route(file_id):
    """파일 삭제 API 엔드포인트"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        success = delete_file(file_id)

        if success:
            return jsonify({"code": 0, "message": "파일 삭제 성공"})
        else:
            return jsonify({"code": 404, "message": f"파일 {file_id} 이(가) 존재하지 않음"}), 404

    except Exception as e:
        return jsonify({"code": 500, "message": f"파일 삭제 실패: {str(e)}"}), 500


@files_bp.route("/batch", methods=["DELETE", "OPTIONS"])
def batch_delete_files_route():
    """파일 일괄 삭제 API 엔드포인트"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.json
        file_ids = data.get("ids", [])

        if not file_ids:
            return jsonify({"code": 400, "message": "삭제할 파일 ID가 제공되지 않았습니다."}), 400

        success_count = batch_delete_files(file_ids)

        return jsonify({"code": 0, "message": f"{success_count}/{len(file_ids)}개 파일 삭제 성공"})

    except Exception as e:
        return jsonify({"code": 500, "message": f"파일 일괄 삭제 실패: {str(e)}"}), 500


@files_bp.route("/upload/chunk", methods=["POST"])
def upload_chunk():
    """
    파일 청크 업로드 처리
    """
    if "chunk" not in request.files:
        return jsonify({"code": 400, "message": "파일 청크가 선택되지 않았습니다.", "data": None}), 400

    chunk = request.files["chunk"]
    chunk_index = request.form.get("chunkIndex")
    total_chunks = request.form.get("totalChunks")
    upload_id = request.form.get("uploadId")
    file_name = request.form.get("fileName")
    parent_id = request.form.get("parent_id")

    if not all([chunk_index, total_chunks, upload_id, file_name]):
        return jsonify({"code": 400, "message": "필수 파라미터가 부족합니다.", "data": None}), 400

    result = handle_chunk_upload(chunk, chunk_index, total_chunks, upload_id, file_name, parent_id)

    # 결과에 오류 정보가 있는지 확인
    if result.get("code", 0) != 0:
        # 오류가 있으면 해당 HTTP 상태코드 반환
        return jsonify(result), result.get("code", 500)

    return jsonify(result)


@files_bp.route("/upload/merge", methods=["POST"])
def merge_upload():
    """
    업로드된 파일 청크 병합
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "message": "요청 데이터가 비어 있습니다.", "data": None}), 400

    upload_id = data.get("uploadId")
    file_name = data.get("fileName")
    total_chunks = data.get("totalChunks")
    parent_id = data.get("parentId")

    if not all([upload_id, file_name, total_chunks]):
        return jsonify({"code": 400, "message": "필수 파라미터가 부족합니다.", "data": None}), 400

    result = merge_chunks(upload_id, file_name, total_chunks, parent_id)

    # 결과에 오류 정보가 있는지 확인
    if result.get("code", 0) != 0:
        # 오류가 있으면 해당 HTTP 상태코드 반환
        return jsonify(result), result.get("code", 500)

    return jsonify(result)
