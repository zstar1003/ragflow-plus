import logging
import os
from datetime import datetime, timedelta

import jwt
from dotenv import load_dotenv
from flask import Flask, request
from flask_cors import CORS
from routes import register_routes

# 환경 변수 로드
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docker", ".env"))

app = Flask(__name__)
# CORS 활성화, 프론트엔드 접근 허용
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

# 모든 라우트 등록
register_routes(app)

# 환경 변수에서 설정 가져오기
ADMIN_USERNAME = os.getenv("MANAGEMENT_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("MANAGEMENT_ADMIN_PASSWORD", "12345678")
JWT_SECRET = os.getenv("MANAGEMENT_JWT_SECRET", "your-secret-key")


# 로그 디렉토리 및 파일명 설정
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "parser.log")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),  # 동시에 콘솔에도 출력
    ],
)


# 토큰 생성
def generate_token(username):
    # 토큰 만료 시간 설정 (예: 1시간 후 만료)
    expire_time = datetime.utcnow() + timedelta(hours=1)

    # 토큰 생성
    token = jwt.encode({"username": username, "exp": expire_time}, JWT_SECRET, algorithm="HS256")

    return token


# 로그인 라우트는 메인 파일에 유지
@app.route("/api/v1/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    # 사용자명과 비밀번호 매핑 생성
    valid_users = {ADMIN_USERNAME: ADMIN_PASSWORD}

    # 사용자명 존재 여부 확인
    if not username or username not in valid_users:
        return {"code": 1, "message": "用户名不存在"}, 400

    # 비밀번호가 올바른지 확인
    if not password or password != valid_users[username]:
        return {"code": 1, "message": "密码错误"}, 400

    # 토큰 생성
    token = generate_token(username)

    return {"code": 0, "data": {"token": token}, "message": "로그인 성공"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
