import mysql.connector
from datetime import datetime
from database import DB_CONFIG

def get_tenants_with_pagination(current_page, page_size, username=''):
    """查询租户信息，支持分页和条件筛选"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 构建WHERE子句和参数
        where_clauses = []
        params = []
        
        if username:
            where_clauses.append("""
            EXISTS (
                SELECT 1 FROM user_tenant ut 
                JOIN user u ON ut.user_id = u.id 
                WHERE ut.tenant_id = t.id AND u.nickname LIKE %s
            )
            """)
            params.append(f"%{username}%")
        
        # 组合WHERE子句
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # 查询总记录数
        count_sql = f"""
        SELECT COUNT(*) as total 
        FROM tenant t 
        WHERE {where_sql}
        """
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 计算分页偏移量
        offset = (current_page - 1) * page_size
        
        # 执行分页查询
        query = f"""
        SELECT 
            t.id, 
            (SELECT u.nickname FROM user_tenant ut JOIN user u ON ut.user_id = u.id 
             WHERE ut.tenant_id = t.id AND ut.role = 'owner' LIMIT 1) as username,
            t.llm_id as chat_model,
            t.embd_id as embedding_model,
            t.create_date, 
            t.update_date
        FROM 
            tenant t
        WHERE 
            {where_sql}
        ORDER BY 
            t.create_date DESC
        LIMIT %s OFFSET %s
        """
        cursor.execute(query, params + [page_size, offset])
        results = cursor.fetchall()
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        # 格式化结果
        formatted_tenants = []
        for tenant in results:
            formatted_tenants.append({
                "id": tenant["id"],
                "username": tenant["username"] if tenant["username"] else "未指定",
                "chatModel": tenant["chat_model"] if tenant["chat_model"] else "",
                "embeddingModel": tenant["embedding_model"] if tenant["embedding_model"] else "",
                "createTime": tenant["create_date"].strftime("%Y-%m-%d %H:%M:%S") if tenant["create_date"] else "",
                "updateTime": tenant["update_date"].strftime("%Y-%m-%d %H:%M:%S") if tenant["update_date"] else ""
            })
        
        return formatted_tenants, total
        
    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
        return [], 0

def update_tenant(tenant_id, tenant_data):
    """更新租户信息"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 更新租户表
        current_datetime = datetime.now()
        update_time = int(current_datetime.timestamp() * 1000)
        current_date = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
        
        query = """
        UPDATE tenant 
        SET update_time = %s, 
            update_date = %s, 
            llm_id = %s, 
            embd_id = %s
        WHERE id = %s
        """
        
        cursor.execute(query, (
            update_time,
            current_date,
            tenant_data.get("chatModel", ""),
            tenant_data.get("embeddingModel", ""),
            tenant_id
        ))
        
        affected_rows = cursor.rowcount
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return affected_rows > 0
        
    except mysql.connector.Error as err:
        print(f"更新租户错误: {err}")
        return False