import mysql.connector
import uuid
import base64
import json
from datetime import datetime
from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_v1_5
from werkzeug.security import generate_password_hash

# 数据库连接配置
db_config = {
    "host": "localhost",
    "port": 5455,
    "user": "root",
    "password": "infini_rag_flow",
    "database": "rag_flow",
}

# 生成随机的 UUID 作为 id
def generate_uuid():
    return str(uuid.uuid4()).replace("-", "")

# RSA 加密密码
def rsa_psw(password: str) -> str:
    pub_key = """-----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArq9XTUSeYr2+N1h3Afl/z8Dse/2yD0ZGrKwx+EEEcdsBLca9Ynmx3nIB5obmLlSfmskLpBo0UACBmB5rEjBp2Q2f3AG3Hjd4B+gNCG6BDaawuDlgANIhGnaTLrIqWrrcm4EMzJOnAOI1fgzJRsOOUEfaS318Eq9OVO3apEyCCt0lOQK6PuksduOjVxtltDav+guVAA068NrPYmRNabVKRNLJpL8w4D44sfth5RvZ3q9t+6RTArpEtc5sh5ChzvqPOzKGMXW83C95TxmXqpbK6olN4RevSfVjEAgCydH6HN6OhtOQEcnrU97r9H0iZOWwbw3pVrZiUkuRD1R56Wzs2wIDAQAB
    -----END PUBLIC KEY-----"""

    rsa_key = RSA.import_key(pub_key)
    cipher = PKCS1_v1_5.new(rsa_key)
    encrypted_data = cipher.encrypt(base64.b64encode(password.encode()))
    return base64.b64encode(encrypted_data).decode()

# 加密密码
def encrypt_password(raw_password: str) -> str:
    base64_password = base64.b64encode(raw_password.encode()).decode()
    encrypted_password = rsa_psw(base64_password)
    return generate_password_hash(base64_password)

# 处理批量注册
def batch_register_students():
    # 从 JSON 文件加载学生数据
    with open("add.json", "r", encoding="utf-8") as json_file:
        student_groups = json.load(json_file)

    try:
        # 建立数据库连接
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        for group in student_groups:
            tenant_id = group["tenant_id"]
            student_ids = group["student_id"]

            for student_id in student_ids:
                # 生成 ID 和时间戳
                user_id = generate_uuid()
                create_time = 1741361741738
                create_date = datetime.strptime("2025-03-07 23:35:41", "%Y-%m-%d %H:%M:%S")
                update_time = 1741416354403
                update_date = datetime.strptime("2025-03-08 14:45:54", "%Y-%m-%d %H:%M:%S")

                # 用户信息
                student_email = student_id + "@xidian.cn"
                raw_password = student_id
                hash_encrypted = encrypt_password(raw_password)

                # 插入 user 表数据
                user_insert_query = """
                INSERT INTO user (
                    id, create_time, create_date, update_time, update_date, access_token,
                    nickname, password, email, avatar, language, color_schema, timezone,
                    last_login_time, is_authenticated, is_active, is_anonymous, login_channel,
                    status, is_superuser
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s
                )
                """
                user_data = (
                    user_id, create_time, create_date, update_time, update_date, None,
                    student_id, hash_encrypted, student_email, None, "Chinese", "Bright", "UTC+8 Asia/Shanghai",
                    create_date, 1, 1, 0, "password",
                    1, 0
                )
                cursor.execute(user_insert_query, user_data)

                # 插入 tenant 表数据
                tenant_insert_query = """
                INSERT INTO tenant (
                    id, create_time, create_date, update_time, update_date, name,
                    public_key, llm_id, embd_id, asr_id, img2txt_id, rerank_id, tts_id,
                    parser_ids, credit, status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                """
                tenant_data = (
                    user_id, create_time, create_date, update_time, update_date, student_id + "'s Kingdom",
                    None, "deepseek-r1:1.5b@Ollama", "BAAI/bge-large-zh-v1.5@BAAI", "", "", "", None,
                    "naive:General,qa:Q&A,resume:Resume,manual:Manual,table:Table,paper:Paper,book:Book,laws:Laws,presentation:Presentation,picture:Picture,one:One,audio:Audio,email:Email,tag:Tag",
                    512, 1
                )
                cursor.execute(tenant_insert_query, tenant_data)

                # 插入 user_tenant 表的第一条记录
                user_tenant_insert_query = """
                INSERT INTO user_tenant (
                    id, create_time, create_date, update_time, update_date, user_id,
                    tenant_id, role, invited_by, status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """
                user_tenant_data_owner = (
                    generate_uuid(), create_time, create_date, update_time, update_date, user_id,
                    user_id, "owner", user_id, 1
                )
                cursor.execute(user_tenant_insert_query, user_tenant_data_owner)

                # 插入 user_tenant 表的第二条记录
                user_tenant_data_normal = (
                    generate_uuid(), create_time, create_date, update_time, update_date, user_id,
                    tenant_id, "normal", tenant_id, 1
                )
                cursor.execute(user_tenant_insert_query, user_tenant_data_normal)

                # 插入 tenant_llm 表数据
                tenant_llm_insert_query = """
                INSERT INTO tenant_llm (
                    create_time, create_date, update_time, update_date, tenant_id,
                    llm_factory, model_type, llm_name, api_key, api_base, max_tokens, used_tokens
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                """
                tenant_llm_data = (
                    create_time, create_date, update_time, update_date, user_id,
                    "Ollama", "chat", "deepseek-r1:1.5b", "xxxxxxxxxxxxxxx", "http://10.195.140.47:11434", 88888888, 0
                )
                cursor.execute(tenant_llm_insert_query, tenant_llm_data)

        # 提交事务
        conn.commit()

        print("批量用户数据添加成功！")

    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("数据库连接已关闭。")


if __name__ == '__main__':
    batch_register_students()