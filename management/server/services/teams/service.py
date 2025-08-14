import mysql.connector
from datetime import datetime
from utils import generate_uuid
from database import DB_CONFIG

def get_teams_with_pagination(current_page, page_size, name='', sort_by="create_time",sort_order="desc"):
    """팀 정보 조회, 페이징 및 조건 필터 지원"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # WHERE절 및 파라미터 구성
        where_clauses = []
        params = []
        
        if name:
            where_clauses.append("t.name LIKE %s")
            params.append(f"%{name}%")
        
        # WHERE절 조합
        where_sql = "WHERE " + (" AND ".join(where_clauses) if where_clauses else "1=1")

        # 정렬 필드 검증
        valid_sort_fields = ["name", "create_time", "create_date"]
        if sort_by not in valid_sort_fields:
            sort_by = "create_time"

        # 정렬 쿼리 생성
        sort_clause = f"ORDER BY {sort_by} {sort_order.upper()}"

        # 전체 레코드 수 쿼리
        count_sql = f"SELECT COUNT(*) as total FROM tenant t {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 페이징 오프셋 계산
        offset = (current_page - 1) * page_size
        
        # 페이징 쿼리 실행, 책임자 정보 및 멤버 수 포함
        query = f"""
        SELECT 
            t.id, 
            t.name, 
            t.create_date, 
            t.update_date, 
            t.status,
            (SELECT u.nickname FROM user_tenant ut JOIN user u ON ut.user_id = u.id 
            WHERE ut.tenant_id = t.id AND ut.role = 'owner' LIMIT 1) as owner_name,
            (SELECT COUNT(*) FROM user_tenant ut WHERE ut.tenant_id = t.id AND ut.status = 1) as member_count
        FROM 
            tenant t
        {where_sql}
        {sort_clause}
        LIMIT %s OFFSET %s
        """
        cursor.execute(query, params + [page_size, offset])
        results = cursor.fetchall()
        
        # 연결 종료
        cursor.close()
        conn.close()
        
        # 결과 포맷팅
        formatted_teams = []
        for team in results:
            owner_name = team["owner_name"] if team["owner_name"] else "미지정"
            formatted_teams.append({
                "id": team["id"],
                "name": f"{owner_name}의 팀",
                "ownerName": owner_name,
                "memberCount": team["member_count"],
                "createTime": team["create_date"].strftime("%Y-%m-%d %H:%M:%S") if team["create_date"] else "",
                "updateTime": team["update_date"].strftime("%Y-%m-%d %H:%M:%S") if team["update_date"] else "",
                "status": team["status"]
            })
        
        return formatted_teams, total
        
    except mysql.connector.Error as err:
        print(f"데이터베이스 오류: {err}")
        return [], 0


def get_team_by_id(team_id):
    """ID로 팀 상세 정보 조회"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT id, name, create_date, update_date, status, credit
        FROM tenant
        WHERE id = %s
        """
        cursor.execute(query, (team_id,))
        team = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if team:
            return {
                "id": team["id"],
                "name": team["name"],
                "createTime": team["create_date"].strftime("%Y-%m-%d %H:%M:%S") if team["create_date"] else "",
                "updateTime": team["update_date"].strftime("%Y-%m-%d %H:%M:%S") if team["update_date"] else "",
                "status": team["status"],
                "credit": team["credit"]
            }
        return None
        
    except mysql.connector.Error as err:
        print(f"데이터베이스 오류: {err}")
        return None

def delete_team(team_id):
    """지정한 ID의 팀 삭제"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 팀 멤버 연관 삭제
        member_query = "DELETE FROM user_tenant WHERE tenant_id = %s"
        cursor.execute(member_query, (team_id,))
        
        # 팀 삭제
        team_query = "DELETE FROM tenant WHERE id = %s"
        cursor.execute(team_query, (team_id,))
        
        affected_rows = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return affected_rows > 0
        
    except mysql.connector.Error as err:
        print(f"팀 삭제 오류: {err}")
        return False

def get_team_members(team_id):
    """팀 멤버 목록 조회"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT ut.user_id, u.nickname, u.email, ut.role, ut.create_date
        FROM user_tenant ut
        JOIN user u ON ut.user_id = u.id
        WHERE ut.tenant_id = %s AND ut.status = 1
        ORDER BY ut.create_date DESC
        """
        cursor.execute(query, (team_id,))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # 결과 포맷팅
        formatted_members = []
        for member in results:
            formatted_members.append({
                "userId": member["user_id"],
                "username": member["nickname"],
                "role": member["role"],  # 원래 역할 값 유지("owner" 또는 "normal")
                "joinTime": member["create_date"].strftime("%Y-%m-%d %H:%M:%S") if member["create_date"] else ""
            })
        
        return formatted_members
        
    except mysql.connector.Error as err:
        print(f"팀 멤버 조회 오류: {err}")
        return []

def add_team_member(team_id, user_id, role="member"):
    """팀 멤버 추가"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 사용자가 이미 팀 멤버인지 확인
        check_query = """
        SELECT id FROM user_tenant 
        WHERE tenant_id = %s AND user_id = %s
        """
        cursor.execute(check_query, (team_id, user_id))
        existing = cursor.fetchone()
        
        if existing:
            # 이미 멤버라면 역할 업데이트
            update_query = """
            UPDATE user_tenant SET role = %s, status = 1
            WHERE tenant_id = %s AND user_id = %s
            """
            cursor.execute(update_query, (role, team_id, user_id))
        else:
            # 멤버가 아니라면 새 레코드 추가
            current_datetime = datetime.now()
            create_time = int(current_datetime.timestamp() * 1000)
            current_date = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
            
            insert_query = """
            INSERT INTO user_tenant (
                id, create_time, create_date, update_time, update_date, user_id,
                tenant_id, role, invited_by, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """
            # 초대자는 시스템 관리자라고 가정
            invited_by = "system"
            
            user_tenant_data = (
                generate_uuid(), create_time, current_date, create_time, current_date, user_id,
                team_id, role, invited_by, 1
            )
            cursor.execute(insert_query, user_tenant_data)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except mysql.connector.Error as err:
        print(f"팀 멤버 추가 오류: {err}")
        return False

def remove_team_member(team_id, user_id):
    """팀 멤버 제거"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 팀의 유일한 소유자인지 확인
        check_owner_query = """
        SELECT COUNT(*) as owner_count FROM user_tenant 
        WHERE tenant_id = %s AND role = 'owner'
        """
        cursor.execute(check_owner_query, (team_id,))
        owner_count = cursor.fetchone()[0]
        
        # 현재 사용자가 소유자인지 확인
        check_user_role_query = """
        SELECT role FROM user_tenant 
        WHERE tenant_id = %s AND user_id = %s
        """
        cursor.execute(check_user_role_query, (team_id, user_id))
        user_role = cursor.fetchone()
        
        # 유일한 소유자라면 제거 불가
        if owner_count == 1 and user_role and user_role[0] == 'owner':
            return False
        
        # 멤버 제거
        delete_query = """
        DELETE FROM user_tenant 
        WHERE tenant_id = %s AND user_id = %s
        """
        cursor.execute(delete_query, (team_id, user_id))
        affected_rows = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return affected_rows > 0
        
    except mysql.connector.Error as err:
        print(f"팀 멤버 제거 오류: {err}")
        return False