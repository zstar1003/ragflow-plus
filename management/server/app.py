from flask import Flask, jsonify, request
from flask_cors import CORS
import database
from routes import register_routes

app = Flask(__name__)
# 启用CORS，允许前端访问
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# 注册所有路由
register_routes(app)

# 登录路由保留在主文件中
@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    # 实现登录逻辑
    return {"code": 0, "data": {"token": "your-token"}, "message": "登录成功"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)