import jwt
import os
from flask import Flask, request
from flask_cors import CORS
from datetime import datetime, timedelta
from routes import register_routes
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docker', '.env'))

app = Flask(__name__)
# 启用CORS，允许前端访问
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# 注册所有路由
register_routes(app)

# 从环境变量获取配置
ADMIN_USERNAME = os.getenv('MANAGEMENT_ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('MANAGEMENT_ADMIN_PASSWORD', '12345678')
JWT_SECRET = os.getenv('MANAGEMENT_JWT_SECRET', 'your-secret-key')

# 生成token
def generate_token(username):
    # 设置令牌过期时间（例如1小时后过期）
    expire_time = datetime.utcnow() + timedelta(hours=1)
    
    # 生成令牌
    token = jwt.encode({
        'username': username,
        'exp': expire_time
    }, JWT_SECRET, algorithm='HS256') 
    
    return token

# 登录路由保留在主文件中
@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # 创建用户名和密码的映射
    valid_users = {
        ADMIN_USERNAME: ADMIN_PASSWORD
    }
    
    # 验证用户名是否存在
    if not username or username not in valid_users:
        return {"code": 1, "message": "用户名不存在"}, 400
    
    # 验证密码是否正确
    if not password or password != valid_users[username]:
        return {"code": 1, "message": "密码错误"}, 400
    
    # 生成token
    token = generate_token(username)
    
    return {"code": 0, "data": {"token": token}, "message": "登录成功"}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)