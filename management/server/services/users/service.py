import os
import mysql.connector
import pytz
from datetime import datetime
from utils import generate_uuid, encrypt_password, verify_password
from database import DB_CONFIG

# 从环境变量获取超级管理员配置
ADMIN_USERNAME = os.getenv("MANAGEMENT_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("MANAGEMENT_ADMIN_PASSWORD", "12345678")


def authenticate_user(username: str, password: str):
    """
    验证用户登录：
    1. 超级管理员(admin)使用环境变量验证
    2. 团队负责人(owner)使用数据库验证
    username: 可以是email或nickname
    返回: (success: bool, user_info: dict, error_message: str)
    """
    # 首先检查是否是超级管理员（使用环境变量验证）
    if username == ADMIN_USERNAME:
        if password == ADMIN_PASSWORD:
            return True, {
                'id': 'admin',
                'username': ADMIN_USERNAME,
                'role': 'admin',
                'is_superuser': True,
                'tenant_id': None
            }, None
        else:
            return False, None, "密码错误"
    
    # 其他用户使用数据库验证
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 查询用户信息 - 支持email或nickname登录
        query = """
        SELECT id, nickname, email, password, is_superuser
        FROM user
        WHERE email = %s OR nickname = %s
        """
        cursor.execute(query, (username, username))
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            return False, None, "用户名或邮箱不存在"
        
        # 验证密码
        if not verify_password(password, user['password']):
            cursor.close()
            conn.close()
            return False, None, "密码错误"
        
        user_id = user['id']
        is_superuser = user['is_superuser']
        
        # 检查是否是数据库中标记的超级管理员
        if is_superuser:
            cursor.close()
            conn.close()
            return True, {
                'id': user_id,
                'username': user['nickname'],
                'role': 'admin',
                'is_superuser': True,
                'tenant_id': None
            }, None
        
        # 检查是否是团队负责人 (owner)
        owner_query = """
        SELECT tenant_id
        FROM user_tenant
        WHERE user_id = %s AND role = 'owner'
        """
        cursor.execute(owner_query, (user_id,))
        owner_record = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if owner_record:
            return True, {
                'id': user_id,
                'username': user['nickname'],
                'role': 'team_owner',
                'is_superuser': False,
                'tenant_id': owner_record['tenant_id']
            }, None
        
        # 既不是超级管理员也不是团队负责人
        return False, None, "无权限登录管理系统，只有超级管理员和团队负责人可以登录"
        
    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
        return False, None, f"数据库错误: {str(err)}"


def get_user_info_by_id(user_id: str):
    """
    根据用户ID获取用户信息和角色
    """
    # 如果是环境变量配置的超级管理员
    if user_id == 'admin':
        return {
            'id': 'admin',
            'username': ADMIN_USERNAME,
            'role': 'admin',
            'roles': ['admin'],
            'is_superuser': True,
            'tenant_id': None
        }
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 查询用户信息
        query = """
        SELECT id, nickname, is_superuser
        FROM user
        WHERE id = %s
        """
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            return None
        
        username = user['nickname']
        is_superuser = user['is_superuser']
        
        # 检查是否是数据库中标记的超级管理员
        if is_superuser:
            cursor.close()
            conn.close()
            return {
                'id': user_id,
                'username': username,
                'role': 'admin',
                'roles': ['admin'],
                'is_superuser': True,
                'tenant_id': None
            }
        
        # 检查是否是团队负责人
        owner_query = """
        SELECT tenant_id
        FROM user_tenant
        WHERE user_id = %s AND role = 'owner'
        """
        cursor.execute(owner_query, (user_id,))
        owner_record = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if owner_record:
            return {
                'id': user_id,
                'username': username,
                'role': 'team_owner',
                'roles': ['team_owner'],
                'is_superuser': False,
                'tenant_id': owner_record['tenant_id']
            }
        
        return None
        
    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
        return None


def get_users_with_pagination(current_page, page_size, username='', email='', sort_by="create_time",sort_order="desc"):
    """查询用户信息，支持分页和条件筛选"""
    try:
        # 建立数据库连接
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 构建WHERE子句和参数
        where_clauses = []
        params = []
        
        if username:
            where_clauses.append("nickname LIKE %s")
            params.append(f"%{username}%")
        
        if email:
            where_clauses.append("email LIKE %s")
            params.append(f"%{email}%")
        
        # 组合WHERE子句
        where_sql = "WHERE " + (" AND ".join(where_clauses) if where_clauses else "1=1")

        # 验证排序字段
        valid_sort_fields = ["name", "email", "create_time", "create_date"]
        if sort_by not in valid_sort_fields:
            sort_by = "create_time"

        # 构建排序子句
        sort_clause = f"ORDER BY {sort_by} {sort_order.upper()}"
        
        # 查询总记录数
        count_sql = f"SELECT COUNT(*) as total FROM user {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 计算分页偏移量
        offset = (current_page - 1) * page_size
        
        # 执行分页查询
        query = f"""
        SELECT id, nickname, email, create_date, update_date, status, is_superuser, create_date
        FROM user
        {where_sql}
        {sort_clause}
        LIMIT %s OFFSET %s
        """
        cursor.execute(query, params + [page_size, offset])
        results = cursor.fetchall()
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        # 格式化结果
        formatted_users = []
        for user in results:
            formatted_users.append({
                "id": user["id"],
                "username": user["nickname"],
                "email": user["email"],
                "createTime": user["create_date"].strftime("%Y-%m-%d %H:%M:%S") if user["create_date"] else "",
                "updateTime": user["update_date"].strftime("%Y-%m-%d %H:%M:%S") if user["update_date"] else "",
            })
        
        return formatted_users, total
        
    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
        return [], 0

def delete_user(user_id):
    """删除指定ID的用户"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 删除 user 表中的用户记录
        query = "DELETE FROM user WHERE id = %s"
        cursor.execute(query, (user_id,))
        
        # 删除 user_tenant 表中的关联记录
        user_tenant_query = "DELETE FROM user_tenant WHERE user_id = %s"
        cursor.execute(user_tenant_query, (user_id,))

        # 删除 tenant 表中的关联记录
        tenant_query = "DELETE FROM tenant WHERE id = %s"
        cursor.execute(tenant_query, (user_id,))
    
        # 删除 tenant_llm 表中的关联记录
        tenant_llm_query = "DELETE FROM tenant_llm WHERE tenant_id = %s"
        cursor.execute(tenant_llm_query, (user_id,))
    
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except mysql.connector.Error as err:
        print(f"删除用户错误: {err}")
        return False

def create_user(user_data):
    """
    创建新用户（仅创建用户记录，不自动创建团队和配置）
    时间将以 UTC+8 (Asia/Shanghai) 存储。
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 开始插入
        user_id = generate_uuid()
        # 获取基本信息
        username = user_data.get("username")
        email = user_data.get("email")
        password = user_data.get("password")
        # 加密密码
        encrypted_password = encrypt_password(password)

        # 获取当前 UTC 时间并转换为 UTC+8
        utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
        target_tz = pytz.timezone('Asia/Shanghai')
        local_dt = utc_now.astimezone(target_tz)

        create_time = int(local_dt.timestamp() * 1000)
        current_date = local_dt.strftime("%Y-%m-%d %H:%M:%S")

        # 仅插入用户表
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
        user_data_tuple = (
            user_id, create_time, current_date, create_time, current_date, None,
            username, encrypted_password, email, None, "Chinese", "Bright", "UTC+8 Asia/Shanghai",
            current_date, 1, 1, 0, "password",
            1, 0
        )
        cursor.execute(user_insert_query, user_data_tuple)
        
        conn.commit()
        cursor.close()
        conn.close()

        return True
    except mysql.connector.Error as err:
        print(f"创建用户错误: {err}")
        return False

def update_user(user_id, user_data):
    """更新用户信息"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        query = """
        UPDATE user SET nickname = %s WHERE id = %s
        """
        cursor.execute(query, (
            user_data.get("username"),
            user_id
        ))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return True
    except mysql.connector.Error as err:
        print(f"更新用户错误: {err}")
        return False

def reset_user_password(user_id, new_password):
    """
    重置指定用户的密码。
    时间将以 UTC+8 (Asia/Shanghai) 存储。
    Args:
        user_id (str): 用户ID
        new_password (str): 新的明文密码
    Returns:
        bool: 操作是否成功
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 加密新密码
        encrypted_password = encrypt_password(new_password) # 使用与创建用户时相同的加密方法

        # --- 修改时间获取和格式化逻辑 ---
        # 获取当前 UTC 时间
        utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
        # 定义目标时区 (UTC+8)
        target_tz = pytz.timezone('Asia/Shanghai')
        # 将 UTC 时间转换为目标时区时间
        local_dt = utc_now.astimezone(target_tz)

        # 使用转换后的时间
        update_time = int(local_dt.timestamp() * 1000) # 使用本地化时间戳
        update_date = local_dt.strftime("%Y-%m-%d %H:%M:%S") # 使用本地化时间格式化
        # --- 时间逻辑修改结束 ---

        # 更新用户密码
        update_query = """
        UPDATE user
        SET password = %s, update_time = %s, update_date = %s
        WHERE id = %s
        """
        cursor.execute(update_query, (encrypted_password, update_time, update_date, user_id))

        # 检查是否有行被更新
        if cursor.rowcount == 0:
            conn.rollback() # 如果没有更新，回滚
            cursor.close()
            conn.close()
            print(f"用户 {user_id} 未找到，密码未更新。")
            return False # 用户不存在

        conn.commit() # 提交事务
        cursor.close()
        conn.close()
        print(f"用户 {user_id} 密码已成功重置。")
        return True

    except mysql.connector.Error as err:
        print(f"重置密码时数据库错误: {err}")
        # 可以在这里添加更详细的日志记录
        # 如果 conn 存在且打开，尝试回滚
        if 'conn' in locals() and conn.is_connected():
            conn.rollback()
            cursor.close()
            conn.close()
        return False
    except Exception as e:
        print(f"重置密码时发生未知错误: {e}")
        if 'conn' in locals() and conn.is_connected():
            conn.rollback()
            cursor.close()
            conn.close()
        return False