import mysql.connector
import pytz
from datetime import datetime
from utils import generate_uuid, encrypt_password
from database import DB_CONFIG

def get_users_with_pagination(current_page, page_size, username='', email=''):
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
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # 查询总记录数
        count_sql = f"SELECT COUNT(*) as total FROM user WHERE {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 计算分页偏移量
        offset = (current_page - 1) * page_size
        
        # 执行分页查询
        query = f"""
        SELECT id, nickname, email, create_date, update_date, status, is_superuser
        FROM user
        WHERE {where_sql}
        ORDER BY id DESC
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
    创建新用户，并加入最早用户的团队，并使用相同的模型配置。
    时间将以 UTC+8 (Asia/Shanghai) 存储。
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 检查用户表是否为空
        check_users_query = "SELECT COUNT(*) as user_count FROM user"
        cursor.execute(check_users_query)
        user_count = cursor.fetchone()['user_count']
        
        # 如果有用户，则查询最早的tenant和用户配置
        if user_count > 0:
            # 查询最早创建的tenant配置
            query_earliest_tenant = """
            SELECT id, llm_id, embd_id, asr_id, img2txt_id, rerank_id, tts_id, parser_ids, credit
            FROM tenant 
            WHERE create_time = (SELECT MIN(create_time) FROM tenant)
            LIMIT 1
            """
            cursor.execute(query_earliest_tenant)
            earliest_tenant = cursor.fetchone()
            
            # 查询最早创建的用户ID
            query_earliest_user = """
            SELECT id FROM user 
            WHERE create_time = (SELECT MIN(create_time) FROM user)
            LIMIT 1
            """
            cursor.execute(query_earliest_user)
            earliest_user = cursor.fetchone()
            
            # 查询最早用户的所有tenant_llm配置
            query_earliest_user_tenant_llms = """
            SELECT llm_factory, model_type, llm_name, api_key, api_base, max_tokens, used_tokens
            FROM tenant_llm 
            WHERE tenant_id = %s
            """
            cursor.execute(query_earliest_user_tenant_llms, (earliest_user['id'],))
            earliest_user_tenant_llms = cursor.fetchall()
        
        # 开始插入
        user_id = generate_uuid()
        # 获取基本信息
        username = user_data.get("username")
        email = user_data.get("email")
        password = user_data.get("password")
        # 加密密码
        encrypted_password = encrypt_password(password)

        # --- 修改时间获取和格式化逻辑 ---
        # 获取当前 UTC 时间
        utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
        # 定义目标时区 (UTC+8)
        target_tz = pytz.timezone('Asia/Shanghai')
        # 将 UTC 时间转换为目标时区时间
        local_dt = utc_now.astimezone(target_tz)

        # 使用转换后的时间
        create_time = int(local_dt.timestamp() * 1000) # 使用本地化时间戳
        current_date = local_dt.strftime("%Y-%m-%d %H:%M:%S") # 使用本地化时间格式化
        # --- 时间逻辑修改结束 ---

        # 插入用户表
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
            user_id, create_time, current_date, create_time, current_date, None, # 使用修改后的时间
            username, encrypted_password, email, None, "Chinese", "Bright", "UTC+8 Asia/Shanghai",
            current_date, 1, 1, 0, "password", # last_login_time 也使用 UTC+8 时间
            1, 0
        )
        cursor.execute(user_insert_query, user_data_tuple)

        # 插入租户表
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

        if user_count > 0:
            # 如果有现有用户，复制其模型配置
            tenant_data = (
                user_id, create_time, current_date, create_time, current_date, username + "'s Kingdom", # 使用修改后的时间
                None, str(earliest_tenant['llm_id']), str(earliest_tenant['embd_id']),
                str(earliest_tenant['asr_id']), str(earliest_tenant['img2txt_id']),
                str(earliest_tenant['rerank_id']), str(earliest_tenant['tts_id']),
                str(earliest_tenant['parser_ids']), str(earliest_tenant['credit']), 1
            )
        else:
            # 如果是第一个用户，模型ID使用空字符串
            tenant_data = (
                user_id, create_time, current_date, create_time, current_date, username + "'s Kingdom", # 使用修改后的时间
                None, '', '', '', '', '', '',
                '', "1000", 1
            )
        cursor.execute(tenant_insert_query, tenant_data)

        # 插入用户租户关系表（owner角色）
        user_tenant_insert_owner_query = """
        INSERT INTO user_tenant (
            id, create_time, create_date, update_time, update_date, user_id,
            tenant_id, role, invited_by, status
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        """
        user_tenant_data_owner = (
            generate_uuid(), create_time, current_date, create_time, current_date, user_id, # 使用修改后的时间
            user_id, "owner", user_id, 1
        )
        cursor.execute(user_tenant_insert_owner_query, user_tenant_data_owner)

        # 只有在存在其他用户时，才加入最早用户的团队
        if user_count > 0:
            # 插入用户租户关系表（normal角色）
            user_tenant_insert_normal_query = """
            INSERT INTO user_tenant (
                id, create_time, create_date, update_time, update_date, user_id,
                tenant_id, role, invited_by, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """
            user_tenant_data_normal = (
                generate_uuid(), create_time, current_date, create_time, current_date, user_id, # 使用修改后的时间
                earliest_tenant['id'], "normal", earliest_tenant['id'], 1
            )
            cursor.execute(user_tenant_insert_normal_query, user_tenant_data_normal)

            # 为新用户复制最早用户的所有tenant_llm配置
            tenant_llm_insert_query = """
            INSERT INTO tenant_llm (
                create_time, create_date, update_time, update_date, tenant_id,
                llm_factory, model_type, llm_name, api_key, api_base, max_tokens, used_tokens
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
            """

            # 遍历最早用户的所有tenant_llm配置并复制给新用户
            for tenant_llm in earliest_user_tenant_llms:
                tenant_llm_data = (
                    create_time, current_date, create_time, current_date, user_id, # 使用修改后的时间
                    str(tenant_llm['llm_factory']), str(tenant_llm['model_type']), str(tenant_llm['llm_name']),
                    str(tenant_llm['api_key']), str(tenant_llm['api_base']), str(tenant_llm['max_tokens']), 0
                )
                cursor.execute(tenant_llm_insert_query, tenant_llm_data)
        
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