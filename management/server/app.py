import logging
import os
from datetime import datetime, timedelta

import jwt
from dotenv import load_dotenv
from flask import Flask, request
from flask_cors import CORS
from routes import register_routes
from services.users.service import authenticate_user

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docker", ".env"))

app = Flask(__name__)
# 启用CORS，允许前端访问
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

# 注册所有路由
register_routes(app)

# 从环境变量获取配置
ADMIN_USERNAME = os.getenv("MANAGEMENT_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("MANAGEMENT_ADMIN_PASSWORD", "12345678")
JWT_SECRET = os.getenv("MANAGEMENT_JWT_SECRET", "your-secret-key")


# 设置日志目录和文件名
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "parser.log")

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),  # 同时也输出到控制台
    ],
)


# 生成token
def generate_token(user_info):
    # 设置令牌过期时间（例如1小时后过期）
    expire_time = datetime.utcnow() + timedelta(hours=1)

    # 生成令牌，包含用户ID、用户名、角色和租户ID
    payload = {
        "user_id": user_info['id'],
        "username": user_info['username'],
        "role": user_info['role'],
        "tenant_id": user_info.get('tenant_id'),
        "exp": expire_time
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    return token


# 登录路由保留在主文件中
@app.route("/api/v1/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return {"code": 1, "message": "用户名和密码不能为空"}, 400

    # 从数据库验证用户，只允许超级管理员和团队负责人登录
    success, user_info, error_message = authenticate_user(username, password)

    if not success:
        return {"code": 1, "message": error_message}, 400

    # 生成token
    token = generate_token(user_info)

    return {"code": 0, "data": {"token": token}, "message": "登录成功"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
