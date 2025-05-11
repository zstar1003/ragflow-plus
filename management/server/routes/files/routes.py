from flask import jsonify, request, send_file, current_app
from io import BytesIO
from .. import files_bp


from services.files.service import get_files_list, get_file_info, download_file_from_minio, delete_file, batch_delete_files, upload_files_to_server
from services.files.utils import FileType

UPLOAD_FOLDER = "/data/uploads"
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "doc", "docx", "xls", "xlsx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@files_bp.route("/upload", methods=["POST"])
def upload_file():
    if "files" not in request.files:
        return jsonify({"code": 400, "message": "未选择文件", "data": None}), 400

    files = request.files.getlist("files")
    upload_result = upload_files_to_server(files)

    # 返回标准格式
    return jsonify({"code": 0, "message": "上传成功", "data": upload_result["data"]})


@files_bp.route("", methods=["GET", "OPTIONS"])
def get_files():
    """获取文件列表的API端点"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        current_page = int(request.args.get("currentPage", 1))
        page_size = int(request.args.get("size", 10))
        name_filter = request.args.get("name", "")
        sort_by = request.args.get("sort_by", "create_time")
        sort_order = request.args.get("sort_order", "desc")

        result, total = get_files_list(current_page, page_size, name_filter, sort_by, sort_order)

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
