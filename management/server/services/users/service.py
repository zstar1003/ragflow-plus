import mysql.connector
import pytz
from datetime import datetime
from utils import generate_uuid, encrypt_password
from database import DB_CONFIG

def get_users_with_pagination(current_page, page_size, username='', email='', sort_by="create_time",sort_order="desc"):
    """사용자 정보 조회, 페이징 및 조건 필터 지원"""
    try:
        # 데이터베이스 연결 생성
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # WHERE절 및 파라미터 구성
        where_clauses = []
        params = []
        
        if username:
            where_clauses.append("nickname LIKE %s")
            params.append(f"%{username}%")
        
        if email:
            where_clauses.append("email LIKE %s")
            params.append(f"%{email}%")
        
        # WHERE절 조합
        where_sql = "WHERE " + (" AND ".join(where_clauses) if where_clauses else "1=1")

        # 정렬 필드 검증
        valid_sort_fields = ["name", "email", "create_time", "create_date"]
        if sort_by not in valid_sort_fields:
            sort_by = "create_time"

        # 정렬 쿼리 생성
        sort_clause = f"ORDER BY {sort_by} {sort_order.upper()}"
        
        # 전체 레코드 수 쿼리
        count_sql = f"SELECT COUNT(*) as total FROM user {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 페이징 오프셋 계산
        offset = (current_page - 1) * page_size
        
        # 페이징 쿼리 실행
        query = f"""
        SELECT id, nickname, email, create_date, update_date, status, is_superuser, create_date
        FROM user
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
        print(f"데이터베이스 오류: {err}")
        return [], 0

def delete_user(user_id):
    """지정한 ID의 사용자 삭제"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # user 테이블에서 사용자 레코드 삭제
        query = "DELETE FROM user WHERE id = %s"
        cursor.execute(query, (user_id,))
        
        # user_tenant 테이블에서 연관 레코드 삭제
        user_tenant_query = "DELETE FROM user_tenant WHERE user_id = %s"
        cursor.execute(user_tenant_query, (user_id,))

        # tenant 테이블에서 연관 레코드 삭제
        tenant_query = "DELETE FROM tenant WHERE id = %s"
        cursor.execute(tenant_query, (user_id,))
    
        # tenant_llm 테이블에서 연관 레코드 삭제
        tenant_llm_query = "DELETE FROM tenant_llm WHERE tenant_id = %s"
        cursor.execute(tenant_llm_query, (user_id,))
    
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except mysql.connector.Error as err:
        print(f"사용자 삭제 오류: {err}")
        return False

def create_user(user_data):
    """
    새 사용자 생성, 가장 빠른 사용자의 팀에 가입 및 동일한 모델 설정 사용.
    시간은 UTC+8 (Asia/Shanghai)로 저장됨.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 사용자 테이블이 비어있는지 확인
        check_users_query = "SELECT COUNT(*) as user_count FROM user"
        cursor.execute(check_users_query)
        user_count = cursor.fetchone()['user_count']
        
        # 사용자가 있으면 가장 빠른 tenant 및 사용자 설정 조회
        if user_count > 0:
            # 가장 먼저 생성된 tenant 설정 조회
            query_earliest_tenant = """
            SELECT id, llm_id, embd_id, asr_id, img2txt_id, rerank_id, tts_id, parser_ids, credit
            FROM tenant 
            WHERE create_time = (SELECT MIN(create_time) FROM tenant)
            LIMIT 1
            """
            cursor.execute(query_earliest_tenant)
            earliest_tenant = cursor.fetchone()
            
            # 가장 먼저 생성된 사용자 ID 조회
            query_earliest_user = """
            SELECT id FROM user 
            WHERE create_time = (SELECT MIN(create_time) FROM user)
            LIMIT 1
            """
            cursor.execute(query_earliest_user)
            earliest_user = cursor.fetchone()
            
            # 가장 빠른 사용자의 모든 tenant_llm 설정 조회
            query_earliest_user_tenant_llms = """
            SELECT llm_factory, model_type, llm_name, api_key, api_base, max_tokens, used_tokens
            FROM tenant_llm 
            WHERE tenant_id = %s
            """
            cursor.execute(query_earliest_user_tenant_llms, (earliest_user['id'],))
            earliest_user_tenant_llms = cursor.fetchall()
        
        # 삽입 시작
        user_id = generate_uuid()
        # 기본 정보 가져오기
        username = user_data.get("username")
        email = user_data.get("email")
        password = user_data.get("password")
        # 비밀번호 암호화
        encrypted_password = encrypt_password(password)

        # --- 시간 획득 및 포맷 로직 수정 ---
        # 현재 UTC 시간 가져오기
        utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
        # 목표 타임존 정의 (UTC+8)
        target_tz = pytz.timezone('Asia/Shanghai')
        # UTC 시간을 목표 타임존 시간으로 변환
        local_dt = utc_now.astimezone(target_tz)

        # 변환된 시간 사용
        create_time = int(local_dt.timestamp() * 1000) # 현지화된 타임스탬프 사용
        current_date = local_dt.strftime("%Y-%m-%d %H:%M:%S") # 현지화된 시간 포맷 사용
        # --- 시간 로직 수정 끝 ---

        # 사용자 테이블에 삽입
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
            user_id, create_time, current_date, create_time, current_date, None, # 수정된 시간 사용
            username, encrypted_password, email, None, "Chinese", "Bright", "UTC+8 Asia/Shanghai",
            current_date, 1, 1, 0, "password", # last_login_time도 UTC+8 시간 사용
            1, 0
        )
        cursor.execute(user_insert_query, user_data_tuple)

        # 테넌트 테이블에 삽입
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
            # 기존 사용자가 있으면 모델 설정 복사
            tenant_data = (
                user_id, create_time, current_date, create_time, current_date, username + "의 Kingdom", # 수정된 시간 사용
                None, str(earliest_tenant['llm_id']), str(earliest_tenant['embd_id']),
                str(earliest_tenant['asr_id']), str(earliest_tenant['img2txt_id']),
                str(earliest_tenant['rerank_id']), str(earliest_tenant['tts_id']),
                str(earliest_tenant['parser_ids']), str(earliest_tenant['credit']), 1
            )
        else:
            # 첫 번째 사용자라면 모델 ID는 빈 문자열
            tenant_data = (
                user_id, create_time, current_date, create_time, current_date, username + "의 Kingdom", # 수정된 시간 사용
                None, '', '', '', '', '', '',
                '', "1000", 1
            )
        cursor.execute(tenant_insert_query, tenant_data)

        # 사용자-테넌트 관계 테이블에 삽입(owner 역할)
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
            generate_uuid(), create_time, current_date, create_time, current_date, user_id, # 수정된 시간 사용
            user_id, "owner", user_id, 1
        )
        cursor.execute(user_tenant_insert_owner_query, user_tenant_data_owner)

        # 다른 사용자가 있을 때만 가장 빠른 사용자의 팀에 가입
        if user_count > 0:
            # 사용자-테넌트 관계 테이블에 삽입(normal 역할)
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
                generate_uuid(), create_time, current_date, create_time, current_date, user_id, # 수정된 시간 사용
                earliest_tenant['id'], "normal", earliest_tenant['id'], 1
            )
            cursor.execute(user_tenant_insert_normal_query, user_tenant_data_normal)

            # 새 사용자에게 가장 빠른 사용자의 모든 tenant_llm 설정 복사
            tenant_llm_insert_query = """
            INSERT INTO tenant_llm (
                create_time, create_date, update_time, update_date, tenant_id,
                llm_factory, model_type, llm_name, api_key, api_base, max_tokens, used_tokens
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
            """

            # 가장 오래된 사용자의 모든 tenant_llm 설정을 순회하며 새 사용자에게 복사
            for tenant_llm in earliest_user_tenant_llms:
                tenant_llm_data = (
                    create_time, current_date, create_time, current_date, user_id, # 수정된 시간 사용
                    str(tenant_llm['llm_factory']), str(tenant_llm['model_type']), str(tenant_llm['llm_name']),
                    str(tenant_llm['api_key']), str(tenant_llm['api_base']), str(tenant_llm['max_tokens']), 0
                )
                cursor.execute(tenant_llm_insert_query, tenant_llm_data)
        
        conn.commit()
        cursor.close()
        conn.close()

        return True
    except mysql.connector.Error as err:
        print(f"사용자 생성 오류: {err}")
        return False

def update_user(user_id, user_data):
    """사용자 정보 업데이트"""
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
        print(f"사용자 정보 업데이트 오류: {err}")
        return False

def reset_user_password(user_id, new_password):
    """
    지정된 사용자의 비밀번호를 재설정합니다.
    시간은 UTC+8 (Asia/Shanghai)로 저장됩니다.
    Args:
        user_id (str): 사용자 ID
        new_password (str): 새로운 평문 비밀번호
    Returns:
        bool: 작업 성공 여부
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 새 비밀번호 암호화
        encrypted_password = encrypt_password(new_password) # 사용자 생성 시와 동일한 암호화 방법 사용

        # --- 시간 획득 및 포맷팅 로직 수정 ---
        # 현재 UTC 시간 획득
        utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
        # 대상 시간대 정의 (UTC+8)
        target_tz = pytz.timezone('Asia/Shanghai')
        # UTC 시간을 대상 시간대 시간으로 변환
        local_dt = utc_now.astimezone(target_tz)

        # 변환된 시간 사용
        update_time = int(local_dt.timestamp() * 1000) # 현지화된 타임스탬프 사용
        update_date = local_dt.strftime("%Y-%m-%d %H:%M:%S") # 현지화된 시간 포맷 사용
        # --- 시간 로직 수정 끝 ---

        # 사용자 비밀번호 업데이트
        update_query = """
        UPDATE user
        SET password = %s, update_time = %s, update_date = %s
        WHERE id = %s
        """
        cursor.execute(update_query, (encrypted_password, update_time, update_date, user_id))

        # 업데이트된 행이 있는지 확인
        if cursor.rowcount == 0:
            conn.rollback() # 업데이트가 없으면 롤백
            cursor.close()
            conn.close()
            print(f"사용자 {user_id}를 찾을 수 없어 비밀번호가 변경되지 않았습니다.")
            return False # 사용자가 존재하지 않음

        conn.commit() # 트랜잭션 커밋
        cursor.close()
        conn.close()
        print(f"사용자 {user_id}의 비밀번호가 성공적으로 재설정되었습니다.")
        return True

    except mysql.connector.Error as err:
        print(f"비밀번호 재설정 중 데이터베이스 오류: {err}")
        # 여기서 더 자세한 로그 기록 추가 가능
        # conn이 존재하고 열려있으면 롤백 시도
        if 'conn' in locals() and conn.is_connected():
            conn.rollback()
            cursor.close()
            conn.close()
        return False
    except Exception as e:
        print(f"비밀번호 재설정 중 알 수 없는 오류 발생: {e}")
        if 'conn' in locals() and conn.is_connected():
            conn.rollback()
            cursor.close()
            conn.close()
        return False