import mysql.connector
from datetime import datetime
from database import DB_CONFIG

def get_tenants_with_pagination(current_page, page_size, username=''):
    """테넌트 정보 조회, 페이징 및 조건 필터 지원"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # WHERE절 및 파라미터 구성
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
        
        # WHERE절 조합
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # 전체 레코드 수 쿼리
        count_sql = f"""
        SELECT COUNT(*) as total 
        FROM tenant t 
        WHERE {where_sql}
        """
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 페이징 오프셋 계산
        offset = (current_page - 1) * page_size
        
        # 페이징 쿼리 실행
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
        
        # 연결 종료
        cursor.close()
        conn.close()
        
        # 결과 포맷팅
        formatted_tenants = []
        for tenant in results:
            formatted_tenants.append({
                "id": tenant["id"],
                "username": tenant["username"] if tenant["username"] else "미지정",
                "chatModel": tenant["chat_model"] if tenant["chat_model"] else "",
                "embeddingModel": tenant["embedding_model"] if tenant["embedding_model"] else "",
                "createTime": tenant["create_date"].strftime("%Y-%m-%d %H:%M:%S") if tenant["create_date"] else "",
                "updateTime": tenant["update_date"].strftime("%Y-%m-%d %H:%M:%S") if tenant["update_date"] else ""
            })
        
        return formatted_tenants, total
        
    except mysql.connector.Error as err:
        print(f"데이터베이스 오류: {err}")
        return [], 0

def update_tenant(tenant_id, tenant_data):
    """테넌트 정보 업데이트"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 테넌트 테이블 업데이트
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
        print(f"테넌트 업데이트 오류: {err}")
        return False