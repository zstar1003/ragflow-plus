import os
from flask import jsonify, request, send_file, current_app
from io import BytesIO
from .. import files_bp
from flask import request, jsonify
from werkzeug.utils import secure_filename


from services.files.service import (
    get_files_list, 
    get_file_info, 
    download_file_from_minio, 
    delete_file, 
    batch_delete_files,
    get_minio_client,
    upload_files_to_server
)

UPLOAD_FOLDER = '/data/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@files_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        return jsonify({'code': 400, 'message': '未选择文件'}), 400
    
    files = request.files.getlist('files')
    upload_result = upload_files_to_server(files)
    
    return jsonify(upload_result)


@files_bp.route('', methods=['GET', 'OPTIONS'])
def get_files():
    """获取文件列表的API端点"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        current_page = int(request.args.get('currentPage', 1))
        page_size = int(request.args.get('size', 10))
        name_filter = request.args.get('name', '')
        
        result, total = get_files_list(current_page, page_size, name_filter)
        
        return jsonify({
            "code": 0,
            "data": {
                "list": result,
                "total": total
            },
            "message": "获取文件列表成功"
        })
    
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"获取文件列表失败: {str(e)}"
        }), 500

@files_bp.route('/<string:file_id>/download', methods=['GET', 'OPTIONS'])
def download_file(file_id):
    try:
        current_app.logger.info(f"开始处理文件下载请求: {file_id}")
        document, _, storage_bucket, storage_location = get_file_info(file_id)
        
        if not document:
            current_app.logger.error(f"文件不存在: {file_id}")
            return jsonify({
                "code": 404, 
                "message": f"文件 {file_id} 不存在",
                "details": "文件记录不存在或已被删除"
            }), 404
            
        current_app.logger.info(f"文件信息获取成功: {file_id}, 存储位置: {storage_bucket}/{storage_location}")
        
        try:
            minio_client = get_minio_client()
            current_app.logger.info(f"MinIO客户端创建成功, 准备检查文件: {storage_bucket}/{storage_location}")
            
            obj = minio_client.stat_object(storage_bucket, storage_location)
            if not obj:
                current_app.logger.error(f"文件对象为空: {storage_bucket}/{storage_location}")
                return jsonify({
                    "code": 404,
                    "message": "文件内容为空",
                    "details": "MinIO存储桶中存在文件记录但内容为空"
                }), 404
                
            if obj.size == 0:
                current_app.logger.error(f"文件大小为0: {storage_bucket}/{storage_location}")
                return jsonify({
                    "code": 404,
                    "message": "文件内容为空",
                    "details": "MinIO存储桶中文件大小为0"
                }), 404
                
            current_app.logger.info(f"文件检查成功, 大小: {obj.size} 字节, 准备下载")
            
            response = minio_client.get_object(storage_bucket, storage_location)
            file_data = response.read()
            
            current_app.logger.info(f"文件读取成功, 大小: {len(file_data)} 字节, 准备发送")
            
            return send_file(
                BytesIO(file_data),
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name=document['name']
            )
            
        except Exception as e:
            current_app.logger.error(f"MinIO操作异常: {str(e)}", exc_info=True)
            # 检查是否是连接错误
            if "connection" in str(e).lower():
                return jsonify({
                    "code": 503,
                    "message": "存储服务连接失败",
                    "details": f"无法连接到MinIO服务: {str(e)}"
                }), 503
            # 检查是否是权限错误
            elif "access denied" in str(e).lower() or "permission" in str(e).lower():
                return jsonify({
                    "code": 403,
                    "message": "存储服务访问被拒绝",
                    "details": f"MinIO访问权限错误: {str(e)}"
                }), 403
            # 其他错误
            else:
                return jsonify({
                    "code": 500,
                    "message": "存储服务异常",
                    "details": str(e)
                }), 500
     
    except Exception as e:
        current_app.logger.error(f"文件下载异常: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": "文件下载失败",
            "details": str(e)
        }), 500

@files_bp.route('/<string:file_id>', methods=['DELETE', 'OPTIONS'])
def delete_file_route(file_id):
    """删除文件的API端点"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        success = delete_file(file_id)
        
        if success:
            return jsonify({
                "code": 0,
                "message": "文件删除成功"
            })
        else:
            return jsonify({
                "code": 404,
                "message": f"文件 {file_id} 不存在"
            }), 404
    
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"删除文件失败: {str(e)}"
        }), 500

@files_bp.route('/batch', methods=['DELETE', 'OPTIONS'])
def batch_delete_files_route():
    """批量删除文件的API端点"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.json
        file_ids = data.get('ids', [])
        
        if not file_ids:
            return jsonify({
                "code": 400,
                "message": "未提供要删除的文件ID"
            }), 400
        
        success_count = batch_delete_files(file_ids)
        
        return jsonify({
            "code": 0,
            "message": f"成功删除 {success_count}/{len(file_ids)} 个文件"
        })
    
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"批量删除文件失败: {str(e)}"
        }), 500