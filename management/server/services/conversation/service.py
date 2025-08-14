import mysql.connector
from database import DB_CONFIG


def get_conversations_by_user_id(user_id, page=1, size=20, sort_by="update_time", sort_order="desc"):
    """
    사용자 ID로 대화 목록 조회

    매개변수:
        user_id (str): 사용자 ID
        page (int): 현재 페이지 번호
        size (int): 페이지당 크기
        sort_by (str): 정렬 필드
        sort_order (str): 정렬 방식 (asc/desc)

    반환:
        tuple: (대화 목록, 전체 개수)
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # user_id를 tenant_id로 바로 사용
        tenant_id = user_id

        # 전체 레코드 수 조회
        count_sql = """
        SELECT COUNT(*) as total 
        FROM dialog d
        WHERE d.tenant_id = %s
        """
        cursor.execute(count_sql, (tenant_id,))
        total = cursor.fetchone()["total"]

        # print(f"전체 레코드 수: {total}")

        # 페이지 오프셋 계산
        offset = (page - 1) * size

        # 정렬 방향 결정
        sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"

        # 페이지 쿼리 실행
        query = f"""
        SELECT 
            d.id, 
            d.name,
            d.create_date,
            d.update_date,
            d.tenant_id
        FROM 
            dialog d
        WHERE 
            d.tenant_id = %s
        ORDER BY 
            d.{sort_by} {sort_direction}
        LIMIT %s OFFSET %s
        """

        # print(f"쿼리 실행: {query}")
        # print(f"파라미터: tenant_id={tenant_id}, size={size}, offset={offset}")

        cursor.execute(query, (tenant_id, size, offset))
        results = cursor.fetchall()

        print(f"조회 결과 개수: {len(results)}")

        # 각 대화의 최신 메시지 가져오기
        conversations = []
        for dialog in results:
            # 대화의 모든 메시지 조회
            conv_query = """
            SELECT id, message, name 
            FROM conversation 
            WHERE dialog_id = %s
            ORDER BY create_date DESC
            """
            cursor.execute(conv_query, (dialog["id"],))
            conv_results = cursor.fetchall()

            latest_message = ""
            conversation_name = dialog["name"]  # 기본적으로 dialog의 name 사용
            if conv_results and len(conv_results) > 0:
                # 최신 대화 레코드 가져오기
                latest_conv = conv_results[0]
                # conversation에 name이 있으면 우선 사용
                if latest_conv and latest_conv.get("name"):
                    conversation_name = latest_conv["name"]

                if latest_conv and latest_conv["message"]:
                    # 마지막 메시지 내용 가져오기
                    messages = latest_conv["message"]
                    if messages and len(messages) > 0:
                        # 메시지 타입 확인(문자열/딕트)
                        if isinstance(messages[-1], dict):
                            latest_message = messages[-1].get("content", "")
                        elif isinstance(messages[-1], str):
                            latest_message = messages[-1]
                        else:
                            latest_message = str(messages[-1])

            conversations.append(
                {
                    "id": dialog["id"],
                    "name": conversation_name,
                    "latestMessage": latest_message[:100] + "..." if len(latest_message) > 100 else latest_message,
                    "createTime": dialog["create_date"].strftime("%Y-%m-%d %H:%M:%S") if dialog["create_date"] else "",
                    "updateTime": dialog["update_date"].strftime("%Y-%m-%d %H:%M:%S") if dialog["update_date"] else "",
                }
            )

        # 연결 종료
        cursor.close()
        conn.close()

        return conversations, total

    except mysql.connector.Error as err:
        print(f"DB 오류: {err}")
        # 상세 오류 로그
        import traceback

        traceback.print_exc()
        return [], 0
    except Exception as e:
        print(f"알 수 없는 오류: {e}")
        import traceback

        traceback.print_exc()
        return [], 0


def get_messages_by_conversation_id(conversation_id, page=1, size=30):
    """
    특정 대화의 상세 정보 조회

    매개변수:
        conversation_id (str): 대화 ID
        page (int): 현재 페이지 번호
        size (int): 페이지당 크기

    반환:
        tuple: (대화 상세, 전체 메시지 수)
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # 대화 정보 조회
        query = """
        SELECT *
        FROM conversation 
        WHERE dialog_id = %s
        ORDER BY create_date DESC
        """
        cursor.execute(query, (conversation_id,))
        result = cursor.fetchall()  # 모든 결과 읽기

        if not result:
            print(f"대화 ID를 찾을 수 없음: {conversation_id}")
            cursor.close()
            conn.close()
            return None, 0

        # 첫 번째 레코드를 대화 상세로 사용
        conversation = None
        if len(result) > 0:
            conversation = {
                "id": result[0]["id"],
                "dialogId": result[0].get("dialog_id", ""),
                "createTime": result[0]["create_date"].strftime("%Y-%m-%d %H:%M:%S") if result[0].get("create_date") else "",
                "updateTime": result[0]["update_date"].strftime("%Y-%m-%d %H:%M:%S") if result[0].get("update_date") else "",
                "messages": result[0].get("message", []),
            }

        # 디버그 정보 출력
        print(f"대화 상세 조회: ID={conversation_id}")
        print(f"메시지 길이: {len(conversation['messages']) if conversation and conversation.get('messages') else 0}")

        # 연결 종료
        cursor.close()
        conn.close()

        # 대화 상세와 메시지 총 개수 반환
        total = len(conversation["messages"]) if conversation and conversation.get("messages") else 0
        return conversation, total

    except mysql.connector.Error as err:
        print(f"DB 오류: {err}")
        # 상세 오류 로그
        import traceback

        traceback.print_exc()
        return None, 0
    except Exception as e:
        print(f"알 수 없는 오류: {e}")
        import traceback

        traceback.print_exc()
        return None, 0
