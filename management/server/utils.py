import base64
import uuid

from Cryptodome.Cipher import PKCS1_v1_5
from Cryptodome.PublicKey import RSA
from flask import jsonify
from werkzeug.security import generate_password_hash


# 랜덤 UUID를 id로 생성
def generate_uuid():
    return str(uuid.uuid4()).replace("-", "")


# RSA로 비밀번호 암호화
def rsa_psw(password: str) -> str:
    pub_key = """-----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArq9XTUSeYr2+N1h3Afl/z8Dse/2yD0ZGrKwx+EEEcdsBLca9Ynmx3nIB5obmLlSfmskLpBo0UACBmB5rEjBp2Q2f3AG3Hjd4B+gNCG6BDaawuDlgANIhGnaTLrIqWrrcm4EMzJOnAOI1fgzJRsOOUEfaS318Eq9OVO3apEyCCt0lOQK6PuksduOjVxtltDav+guVAA068NrPYmRNabVKRNLJpL8w4D44sfth5RvZ3q9t+6RTArpEtc5sh5ChzvqPOzKGMXW83C95TxmXqpbK6olN4RevSfVjEAgCydH6HN6OhtOQEcnrU97r9H0iZOWwbw3pVrZiUkuRD1R56Wzs2wIDAQAB
    -----END PUBLIC KEY-----"""

    rsa_key = RSA.import_key(pub_key)
    cipher = PKCS1_v1_5.new(rsa_key)
    encrypted_data = cipher.encrypt(base64.b64encode(password.encode()))
    return base64.b64encode(encrypted_data).decode()


# 비밀번호 암호화
def encrypt_password(raw_password: str) -> str:
    base64_password = base64.b64encode(raw_password.encode()).decode()
    return generate_password_hash(base64_password)


# 표준 응답 포맷
def success_response(data=None, message="작업 성공", code=0):
    return jsonify({"code": code, "message": message, "data": data})


# 오류 응답 포맷
def error_response(message="작업 실패", code=500, details=None):
    """표준 오류 응답 포맷"""
    response = {"code": code, "message": message}
    if details:
        response["details"] = details
    return jsonify(response), code if code >= 400 else 500
