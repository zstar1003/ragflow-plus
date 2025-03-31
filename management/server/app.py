from flask import Flask, jsonify, request
from flask_cors import CORS
import database

app = Flask(__name__)
# 启用CORS，允许前端访问
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# 添加 v1 前缀
@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    # 实现登录逻辑
    return {"code": 0, "data": {"token": "your-token"}, "message": "登录成功"}
    

@app.route('/api/v1/users/me', methods=['GET'])
def get_current_user():
    return jsonify({
        "code": 0,
        "data": {
            "username": "admin",
            "roles": ["admin"]
        },
        "message": "获取用户信息成功"
    })


@app.route('/api/v1/users', methods=['GET'])
def get_users():
    """获取用户的API端点,支持分页和条件查询"""
    try:
        # 获取查询参数
        current_page = int(request.args.get('currentPage', 1))
        page_size = int(request.args.get('size', 10))
        username = request.args.get('username', '')
        email = request.args.get('email', '')
        
        # 调用数据库函数获取分页和筛选后的用户数据
        users, total = database.get_users_with_pagination(current_page, page_size, username, email)
        
        # 返回符合前端期望格式的数据
        return jsonify({
            "code": 0,  # 成功状态码
            "data": {
                "list": users,
                "total": total
            },
            "message": "获取用户列表成功"
        })
    except Exception as e:
        # 错误处理
        return jsonify({
            "code": 500,
            "message": f"获取用户列表失败: {str(e)}"
        }), 500

@app.route('/api/v1/users/<string:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """删除用户的API端点"""
    database.delete_user(user_id)
    return jsonify({
        "code": 0,
        "message": f"用户 {user_id} 删除成功"
    })

@app.route('/api/v1/users', methods=['POST'])
def create_user():
    """创建用户的API端点"""
    data = request.json
    # 创建用户
    database.create_user(user_data=data)
    return jsonify({
        "code": 0,
        "message": "用户创建成功"
    })

@app.route('/api/v1/users/<string:user_id>', methods=['PUT'])
def update_user(user_id):
    """更新用户的API端点"""
    data = request.json
    user_id = data.get('id')
    database.update_user(user_id=user_id, user_data=data)
    return jsonify({
        "code": 0,
        "message": f"用户 {user_id} 更新成功"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)