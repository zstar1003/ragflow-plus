from io import BytesIO

from flask import current_app, jsonify, request, send_file
from services.files.service import batch_delete_files, delete_file, download_file_from_minio, get_file_info, get_files_list, handle_chunk_upload, merge_chunks, upload_files_to_server
from services.files.utils import FileType
from services.auth import get_current_user_from_token, is_admin

from .. import files_bp

UPLOAD_FOLDER = "/data/uploads"
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "doc", "docx", "xls", "xlsx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@files_bp.route("/upload", methods=["POST"])
def upload_file():
    if "files" not in request.files:
        return jsonify({"code": 400, "message": "未选择文件", "data": None}), 400

    # 获取当前用户信息
    current_user = get_current_user_from_token()
    user_id = current_user.get('user_id') if current_user else None

    files = request.files.getlist("files")
    upload_result = upload_files_to_server(files, user_id=user_id)

    # 返回标准格式
    return jsonify({"code": 0, "message": "上传成功", "data": upload_result["data"]})


@files_bp.route("", methods=["GET", "OPTIONS"])
def get_files():
    """获取文件列表的API端点"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        # 获取当前用户信息
        current_user = get_current_user_from_token()
        
        current_page = int(request.args.get("currentPage", 1))
        page_size = int(request.args.get("size", 10))
        name_filter = request.args.get("name", "")
        sort_by = request.args.get("sort_by", "create_time")
        sort_order = request.args.get("sort_order", "desc")

        # 根据用户角色过滤文件
        # 超级管理员可以看到所有文件，团队负责人只能看到自己上传的文件
        user_id = None
        if current_user and not is_admin(current_user):
            user_id = current_user.get('user_id')

        result, total = get_files_list(current_page, page_size, name_filter, sort_by, sort_order, user_id)

        return jsonify({"code": 0, "data": {"list": result, "total": total}, "message": "获取文件列表成功"})

    except Exception as e:
        return jsonify({"code": 500, "message": f"获取文件列表失败: {str(e)}"}), 500


@files_bp.route("/<string:file_id>/download", methods=["GET", "OPTIONS"])
def download_file(file_id):
    try:
        current_app.logger.info(f"开始处理文件下载请求: {file_id}")

        # 获取文件信息
        file = get_file_info(file_id)

        if not file:
            current_app.logger.error(f"文件不存在: {file_id}")
            return jsonify({"code": 404, "message": f"文件 {file_id} 不存在", "details": "文件记录不存在或已被删除"}), 404

        if file["type"] == FileType.FOLDER.value:
            current_app.logger.error(f"不能下载文件夹: {file_id}")
            return jsonify({"code": 400, "message": "不能下载文件夹", "details": "请选择一个文件进行下载"}), 400

        current_app.logger.info(f"文件信息获取成功: {file_id}, 存储位置: {file['parent_id']}/{file['location']}")

        try:
            # 从MinIO下载文件
            file_data, filename = download_file_from_minio(file_id)

            # 创建内存文件对象
            file_stream = BytesIO(file_data)

            # 返回文件
            return send_file(file_stream, download_name=filename, as_attachment=True, mimetype="application/octet-stream")

        except Exception as e:
            current_app.logger.error(f"下载文件失败: {str(e)}")
            return jsonify({"code": 500, "message": "下载文件失败", "details": str(e)}), 500

    except Exception as e:
        current_app.logger.error(f"处理下载请求时出错: {str(e)}")
        return jsonify({"code": 500, "message": "处理下载请求时出错", "details": str(e)}), 500


@files_bp.route("/<string:file_id>", methods=["DELETE", "OPTIONS"])
def delete_file_route(file_id):
    """删除文件的API端点"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        success = delete_file(file_id)

        if success:
            return jsonify({"code": 0, "message": "文件删除成功"})
        else:
            return jsonify({"code": 404, "message": f"文件 {file_id} 不存在"}), 404

    except Exception as e:
        return jsonify({"code": 500, "message": f"删除文件失败: {str(e)}"}), 500


@files_bp.route("/batch", methods=["DELETE", "OPTIONS"])
def batch_delete_files_route():
    """批量删除文件的API端点"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.json
        file_ids = data.get("ids", [])

        if not file_ids:
            return jsonify({"code": 400, "message": "未提供要删除的文件ID"}), 400

        success_count = batch_delete_files(file_ids)

        return jsonify({"code": 0, "message": f"成功删除 {success_count}/{len(file_ids)} 个文件"})

    except Exception as e:
        return jsonify({"code": 500, "message": f"批量删除文件失败: {str(e)}"}), 500


@files_bp.route("/upload/chunk", methods=["POST"])
def upload_chunk():
    """
    处理文件分块上传
    """
    if "chunk" not in request.files:
        return jsonify({"code": 400, "message": "未选择文件分块", "data": None}), 400

    chunk = request.files["chunk"]
    chunk_index = request.form.get("chunkIndex")
    total_chunks = request.form.get("totalChunks")
    upload_id = request.form.get("uploadId")
    file_name = request.form.get("fileName")
    parent_id = request.form.get("parent_id")

    if not all([chunk_index, total_chunks, upload_id, file_name]):
        return jsonify({"code": 400, "message": "缺少必要参数", "data": None}), 400

    result = handle_chunk_upload(chunk, chunk_index, total_chunks, upload_id, file_name, parent_id)

    # 检查结果中是否有错误信息
    if result.get("code", 0) != 0:
        # 如果有错误，返回相应的HTTP状态码
        return jsonify(result), result.get("code", 500)

    return jsonify(result)


@files_bp.route("/upload/merge", methods=["POST"])
def merge_upload():
    """
    合并已上传的文件分块
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "message": "请求数据为空", "data": None}), 400

    upload_id = data.get("uploadId")
    file_name = data.get("fileName")
    total_chunks = data.get("totalChunks")
    parent_id = data.get("parentId")

    if not all([upload_id, file_name, total_chunks]):
        return jsonify({"code": 400, "message": "缺少必要参数", "data": None}), 400

    result = merge_chunks(upload_id, file_name, total_chunks, parent_id)

    # 检查结果中是否有错误信息
    if result.get("code", 0) != 0:
        # 如果有错误，返回相应的HTTP状态码
        return jsonify(result), result.get("code", 500)

    return jsonify(result)
