import json
import threading
import time
import traceback
from datetime import datetime

import mysql.connector
import requests
from database import DB_CONFIG, get_es_client
from utils import generate_uuid

# 파싱 관련 모듈
from .document_parser import _update_document_progress, perform_parse

# 순차적 배치 작업 상태 저장용
# 구조: { kb_id: {"status": "running/completed/failed", "total": N, "current": M, "message": "...", "start_time": timestamp} }
SEQUENTIAL_BATCH_TASKS = {}


class KnowledgebaseService:
    @classmethod
    def _get_db_connection(cls):
        """데이터베이스 연결 생성"""
        return mysql.connector.connect(**DB_CONFIG)

    @classmethod
    def get_knowledgebase_list(cls, page=1, size=10, name="", sort_by="create_time", sort_order="desc"):
        """지식베이스 목록 가져오기"""
        conn = cls._get_db_connection()
        cursor = conn.cursor(dictionary=True)


        # 정렬 필드 검증
        valid_sort_fields = ["name", "create_time", "create_date"]
        if sort_by not in valid_sort_fields:
            sort_by = "create_time"

        # 정렬 구문 생성
        sort_clause = f"ORDER BY k.{sort_by} {sort_order.upper()}"

        query = """
            SELECT 
                k.id, 
                k.name, 
                k.embd_id,
                k.description, 
                k.create_date,
                k.update_date,
                k.doc_num,
                k.language,
                k.permission,
                k.created_by,
                u.nickname
            FROM knowledgebase k
            LEFT JOIN user u ON k.created_by = u.id  -- 생성자 닉네임 가져오기
        """
        params = []

        if name:
            query += " WHERE k.name LIKE %s"
            params.append(f"%{name}%")

        # 정렬 조건 추가
        query += f" {sort_clause}"

        query += " LIMIT %s OFFSET %s"
        params.extend([size, (page - 1) * size])
        cursor.execute(query, params)
        results = cursor.fetchall()

        # 결과 처리
        for result in results:
            # 빈 설명 처리
            if not result.get("description"):
                result["description"] = "설명 없음"
            # 날짜 형식 처리
            if result.get("create_date"):
                if isinstance(result["create_date"], datetime):
                    result["create_date"] = result["create_date"].strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(result["create_date"], str):
                    try:
                        # 기존 문자열 포맷 파싱 시도
                        datetime.strptime(result["create_date"], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        result["create_date"] = ""
            if not result.get("nickname"):
                # 생성자 이름 가져오기
                result['nickname'] = "알 수 없는 사용자"

        # 총 개수 가져오기
        count_query = "SELECT COUNT(*) as total FROM knowledgebase"
        if name:
            count_query += " WHERE name LIKE %s"
        cursor.execute(count_query, params[:1] if name else [])
        total = cursor.fetchone()["total"]

        cursor.close()
        conn.close()

        return {"list": results, "total": total}

    @classmethod
    def get_knowledgebase_detail(cls, kb_id):
        """获取知识库详情"""
        conn = cls._get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                k.id, 
                k.name, 
                k.description, 
                k.create_date,
                k.update_date,
                k.doc_num,
                k.avatar
            FROM knowledgebase k
            WHERE k.id = %s
        """
        cursor.execute(query, (kb_id,))
        result = cursor.fetchone()

        if result:
            # 빈 설명 처리
            if not result.get("description"):
                result["description"] = "설명 없음"
            # 날짜 형식 처리
            if result.get("create_date"):
                if isinstance(result["create_date"], datetime):
                    result["create_date"] = result["create_date"].strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(result["create_date"], str):
                    try:
                        datetime.strptime(result["create_date"], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        result["create_date"] = ""

        cursor.close()
        conn.close()

        return result

    @classmethod
    def _check_name_exists(cls, name):
        """지식베이스 상세 정보 가져오기"""
        conn = cls._get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT COUNT(*) as count 
            FROM knowledgebase 
            WHERE name = %s
        """
        cursor.execute(query, (name,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return result[0] > 0

    @classmethod
    def create_knowledgebase(cls, **data):
        """지식베이스 생성"""

        try:
            # 지식베이스 이름 중복 확인
            exists = cls._check_name_exists(data["name"])
            if exists:
                raise Exception("지식베이스 이름이 이미 존재합니다")

            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # 입력된 creator_id를 tenant_id와 created_by로 사용
            tenant_id = data.get("creator_id")
            created_by = data.get("creator_id")

            if not tenant_id:
                # creator_id가 없으면 기본값 사용
                print("creator_id가 제공되지 않아, 가장 오래된 사용자 ID를 가져옵니다")
                try:
                    query_earliest_user = """
                    SELECT id FROM user 
                    WHERE create_time = (SELECT MIN(create_time) FROM user)
                    LIMIT 1
                    """
                    cursor.execute(query_earliest_user)
                    earliest_user = cursor.fetchone()

                    if earliest_user:
                        tenant_id = earliest_user["id"]
                        created_by = earliest_user["id"]
                        print(f"가장 오래된 사용자 ID를 tenant_id와 created_by로 사용: {tenant_id}")
                    else:
                        # 사용자를 찾지 못하면 기본값 사용
                        tenant_id = "system"
                        created_by = "system"
                        print(f"사용자를 찾지 못해 기본값을 tenant_id와 created_by로 사용: {tenant_id}")
                except Exception as e:
                    print(f"사용자 ID를 가져오지 못해 기본값 사용: {str(e)}")
                    tenant_id = "system"
                    created_by = "system"
            else:
                print(f"입력된 creator_id를 tenant_id와 created_by로 사용: {tenant_id}")

            # 프론트에서 전달된 Embedding ID 우선 사용
            embd_id = data.get("embd_id")
            
            if embd_id:
                # 프론트에서 embd_id가 오면 우선 사용
                if "___" in embd_id:
                    embd_id = embd_id.split("___")[0]
                print(f"프론트에서 전달된 embedding 모델 ID 사용: {embd_id}")
            else:
                # 프론트에서 전달 안되면 동적으로 가져옴
                dynamic_embd_id = None
                default_embd_id = "bge-m3"  # 기본값
                try:
                    query_embedding_model = """
                        SELECT llm_name
                        FROM tenant_llm
                        WHERE model_type = 'embedding'
                        ORDER BY create_time DESC
                        LIMIT 1
                    """
                    cursor.execute(query_embedding_model)
                    embedding_model = cursor.fetchone()

                    if embedding_model and embedding_model.get("llm_name"):
                        dynamic_embd_id = embedding_model["llm_name"]
                        print(f"동적으로 가져온 embedding 모델 ID: {dynamic_embd_id}")
                    else:
                        dynamic_embd_id = default_embd_id
                        print(f"tenant_llm 테이블에서 embedding 모델을 찾지 못해 기본값 사용: {dynamic_embd_id}")
                except Exception as e:
                    dynamic_embd_id = default_embd_id
                    print(f"embedding 모델 쿼리 실패: {str(e)}. 기본값 사용: {dynamic_embd_id}")
                    traceback.print_exc()  # 디버깅용 전체 트레이스백
                
                embd_id = dynamic_embd_id

            current_time = datetime.now()
            create_date = current_time.strftime("%Y-%m-%d %H:%M:%S")
            create_time = int(current_time.timestamp() * 1000)  # 밀리초 단위 타임스탬프
            update_date = create_date
            update_time = create_time

            # 전체 필드 목록
            query = """
                INSERT INTO knowledgebase (
                    id, create_time, create_date, update_time, update_date,
                    avatar, tenant_id, name, language, description,
                    embd_id, permission, created_by, doc_num, token_num,
                    chunk_num, similarity_threshold, vector_similarity_weight, parser_id, parser_config,
                    pagerank, status
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s
                )
            """

            # 기본값 설정
            default_parser_config = json.dumps(
                {
                    "layout_recognize": "MinerU",
                    "chunk_token_num": 512,
                    "delimiter": "\n!?;。；！？",
                    "auto_keywords": 0,
                    "auto_questions": 0,
                    "html4excel": False,
                    "raptor": {"use_raptor": False},
                    "graphrag": {"use_graphrag": False},
                }
            )

            kb_id = generate_uuid()
            cursor.execute(
                query,
                (
                    kb_id,  # id
                    create_time,  # create_time
                    create_date,  # create_date
                    update_time,  # update_time
                    update_date,  # update_date
                    None,  # avatar
                    tenant_id,  # tenant_id
                    data["name"],  # name
                    data.get("language", "Chinese"),  # language
                    data.get("description", ""),  # description
                    embd_id,  # embd_id
                    data.get("permission", "me"),  # permission
                    created_by,  # created_by - 내부에서 가져온 값 사용
                    0,  # doc_num
                    0,  # token_num
                    0,  # chunk_num
                    0.7,  # similarity_threshold
                    0.3,  # vector_similarity_weight
                    "naive",  # parser_id
                    default_parser_config,  # parser_config
                    0,  # pagerank
                    "1",  # status
                ),
            )
            conn.commit()

            cursor.close()
            conn.close()

            # 생성된 지식베이스 상세 정보 반환
            return cls.get_knowledgebase_detail(kb_id)

        except Exception as e:
            print(f"지식베이스 생성 실패: {str(e)}")
            raise Exception(f"지식베이스 생성 실패: {str(e)}")

    @classmethod
    def update_knowledgebase(cls, kb_id, **data):
        """更新知识库"""
        try:
            # 直接通过ID检查知识库是否存在
            kb = cls.get_knowledgebase_detail(kb_id)
            if not kb:
                return None

            conn = cls._get_db_connection()
            cursor = conn.cursor()

            # 如果要更新名称，先检查名称是否已存在
            if data.get("name") and data["name"] != kb["name"]:
                exists = cls._check_name_exists(data["name"])
                if exists:
                    raise Exception("지식베이스 이름이 이미 존재합니다")

            # 构建更新语句
            update_fields = []
            params = []

            if data.get("name"):
                update_fields.append("name = %s")
                params.append(data["name"])

            if "description" in data:
                update_fields.append("description = %s")
                params.append(data["description"])

            if "permission" in data:
                update_fields.append("permission = %s")
                params.append(data["permission"])

            if "avatar" in data and data["avatar"]:
                avatar_base64 = data["avatar"]
                # 拼接上前缀
                full_avatar_url = f"data:image/png;base64,{avatar_base64}"
                update_fields.append("avatar = %s")
                params.append(full_avatar_url)
            if "embd_id" in data and data["embd_id"]:
                update_fields.append("embd_id = %s")
                params.append(data["embd_id"])

            # 更新时间
            current_time = datetime.now()
            update_date = current_time.strftime("%Y-%m-%d %H:%M:%S")
            update_fields.append("update_date = %s")
            params.append(update_date)

            # 如果没有要更新的字段，直接返回
            if not update_fields:
                return kb_id

            # 构建并执行更新语句
            query = f"""
                UPDATE knowledgebase 
                SET {", ".join(update_fields)}
                WHERE id = %s
            """
            params.append(kb_id)

            cursor.execute(query, params)
            conn.commit()

            cursor.close()
            conn.close()

            # 返回更新后的知识库详情
            return cls.get_knowledgebase_detail(kb_id)

        except Exception as e:
            print(f"지식베이스 업데이트 실패: {str(e)}")
            raise Exception(f"지식베이스 업데이트 실패: {str(e)}")

    @classmethod
    def delete_knowledgebase(cls, kb_id):
        """删除知识库"""
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor()

            # 먼저 지식베이스 존재 여부 확인
            check_query = "SELECT id FROM knowledgebase WHERE id = %s"
            cursor.execute(check_query, (kb_id,))
            if not cursor.fetchone():
                raise Exception("지식베이스가 존재하지 않습니다")

            # 执行删除
            delete_query = "DELETE FROM knowledgebase WHERE id = %s"
            cursor.execute(delete_query, (kb_id,))
            conn.commit()

            cursor.close()
            conn.close()

            return True
        except Exception as e:
            print(f"지식베이스 삭제 실패: {str(e)}")
            raise Exception(f"지식베이스 삭제 실패: {str(e)}")

    @classmethod
    def batch_delete_knowledgebase(cls, kb_ids):
        """批量删除知识库"""
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor()

            # 检查所有ID是否存在
            check_query = "SELECT id FROM knowledgebase WHERE id IN (%s)" % ",".join(["%s"] * len(kb_ids))
            cursor.execute(check_query, kb_ids)
            existing_ids = [row[0] for row in cursor.fetchall()]

            if len(existing_ids) != len(kb_ids):
                missing_ids = set(kb_ids) - set(existing_ids)
                raise Exception(f"다음 지식베이스가 존재하지 않습니다: {', '.join(missing_ids)}")

            # 执行批量删除
            delete_query = "DELETE FROM knowledgebase WHERE id IN (%s)" % ",".join(["%s"] * len(kb_ids))
            cursor.execute(delete_query, kb_ids)
            conn.commit()

            cursor.close()
            conn.close()

            return len(kb_ids)
        except Exception as e:
            print(f"지식베이스 일괄 삭제 실패: {str(e)}")
            raise Exception(f"지식베이스 일괄 삭제 실패: {str(e)}")

    @classmethod
    def get_knowledgebase_documents(cls, kb_id, page=1, size=10, name="", sort_by="create_time", sort_order="desc"):
        """获取知识库下的文档列表"""
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # 먼저 지식베이스 존재 여부 확인
            check_query = "SELECT id FROM knowledgebase WHERE id = %s"
            cursor.execute(check_query, (kb_id,))
            if not cursor.fetchone():
                raise Exception("지식베이스가 존재하지 않습니다")

            # 验证排序字段
            valid_sort_fields = ["name", "size", "create_time", "create_date"]
            if sort_by not in valid_sort_fields:
                sort_by = "create_time"

            # 构建排序子句
            sort_clause = f"ORDER BY d.{sort_by} {sort_order.upper()}"

            # 查询文档列表
            query = """
                SELECT 
                    d.id, 
                    d.name, 
                    d.chunk_num,
                    d.create_date,
                    d.status,
                    d.run,
                    d.progress,
                    d.parser_id,
                    d.parser_config,
                    d.meta_fields
                FROM document d
                WHERE d.kb_id = %s
            """
            params = [kb_id]

            if name:
                query += " AND d.name LIKE %s"
                params.append(f"%{name}%")

            # 添加查询排序条件
            query += f" {sort_clause}"

            query += " LIMIT %s OFFSET %s"
            params.extend([size, (page - 1) * size])

            cursor.execute(query, params)
            results = cursor.fetchall()

            # 处理日期时间格式
            for result in results:
                if result.get("create_date"):
                    result["create_date"] = result["create_date"].strftime("%Y-%m-%d %H:%M:%S")

            # 获取总数
            count_query = "SELECT COUNT(*) as total FROM document WHERE kb_id = %s"
            count_params = [kb_id]
            if name:
                count_query += " AND name LIKE %s"
                count_params.append(f"%{name}%")

            cursor.execute(count_query, count_params)
            total = cursor.fetchone()["total"]

            cursor.close()
            conn.close()

            return {"list": results, "total": total}

        except Exception as e:
            print(f"지식베이스 문서 목록 가져오기 실패: {str(e)}")
            raise Exception(f"지식베이스 문서 목록 가져오기 실패: {str(e)}")

    @classmethod
    def add_documents_to_knowledgebase(cls, kb_id, file_ids, created_by=None):
        """添加文档到知识库"""
        try:
            print(f"[DEBUG] 문서 추가 시작, 파라미터: kb_id={kb_id}, file_ids={file_ids}")

            # created_by가 없으면 가장 오래된 사용자 ID를 가져옴
            if created_by is None:
                conn = cls._get_db_connection()
                cursor = conn.cursor(dictionary=True)

                # 생성일이 가장 오래된 사용자 ID 쿼리
                query_earliest_user = """
                SELECT id FROM user 
                WHERE create_time = (SELECT MIN(create_time) FROM user)
                LIMIT 1
                """
                cursor.execute(query_earliest_user)
                earliest_user = cursor.fetchone()

                if earliest_user:
                    created_by = earliest_user["id"]
                    print(f"가장 오래된 사용자 ID 사용: {created_by}")
                else:
                    created_by = "system"
                    print("사용자를 찾지 못해 기본 사용자ID: system 사용")

                cursor.close()
                conn.close()

            # 检查知识库是否存在
            kb = cls.get_knowledgebase_detail(kb_id)
            print(f"[DEBUG] 지식베이스 확인 결과: {kb}")
            if not kb:
                print(f"[ERROR] 지식베이스가 존재하지 않음: {kb_id}")
                raise Exception("지식베이스가 존재하지 않습니다")

            conn = cls._get_db_connection()
            cursor = conn.cursor()

            # 获取文件信息
            file_query = """
                SELECT id, name, location, size, type 
                FROM file 
                WHERE id IN (%s)
            """ % ",".join(["%s"] * len(file_ids))

            print(f"[DEBUG] 파일 쿼리 SQL 실행: {file_query}")
            print(f"[DEBUG] 쿼리 파라미터: {file_ids}")

            try:
                cursor.execute(file_query, file_ids)
                files = cursor.fetchall()
                print(f"[DEBUG] 查询到的文件数据: {files}")
            except Exception as e:
                print(f"[ERROR] 파일 쿼리 실패: {str(e)}")
                raise

            if len(files) != len(file_ids):
                print(f"일부 파일이 존재하지 않음: 기대={len(file_ids)}, 실제={len(files)}")
                raise Exception("일부 파일이 존재하지 않습니다")

            # 添加文档记录
            added_count = 0
            for file in files:
                file_id = file[0]
                file_name = file[1]
                print(f"파일 처리: id={file_id}, name={file_name}")

                file_location = file[2]
                file_size = file[3]
                file_type = file[4]

                # 检查文档是否已存在于知识库
                check_query = """
                    SELECT COUNT(*) 
                    FROM document d
                    JOIN file2document f2d ON d.id = f2d.document_id
                    WHERE d.kb_id = %s AND f2d.file_id = %s
                """
                cursor.execute(check_query, (kb_id, file_id))
                exists = cursor.fetchone()[0] > 0

                if exists:
                    continue  # 跳过已存在的文档

                # 创建文档记录
                doc_id = generate_uuid()
                current_datetime = datetime.now()
                create_time = int(current_datetime.timestamp() * 1000)  # 毫秒级时间戳
                current_date = current_datetime.strftime("%Y-%m-%d %H:%M:%S")  # 格式化日期字符串

                # 设置默认值
                default_parser_id = "naive"
                default_parser_config = json.dumps(
                    {
                        "layout_recognize": "MinerU",
                        "chunk_token_num": 512,
                        "delimiter": "\n!?;。；！？",
                        "auto_keywords": 0,
                        "auto_questions": 0,
                        "html4excel": False,
                        "raptor": {"use_raptor": False},
                        "graphrag": {"use_graphrag": False},
                    }
                )
                default_source_type = "local"

                # 插入document表
                doc_query = """
                    INSERT INTO document (
                        id, create_time, create_date, update_time, update_date,
                        thumbnail, kb_id, parser_id, parser_config, source_type,
                        type, created_by, name, location, size,
                        token_num, chunk_num, progress, progress_msg, process_begin_at,
                        process_duation, meta_fields, run, status
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                """

                doc_params = [
                    doc_id,
                    create_time,
                    current_date,
                    create_time,
                    current_date,  # ID和时间
                    None,
                    kb_id,
                    default_parser_id,
                    default_parser_config,
                    default_source_type,  # thumbnail到source_type
                    file_type,
                    created_by,
                    file_name,
                    file_location,
                    file_size,  # type到size
                    0,
                    0,
                    0.0,
                    None,
                    None,  # token_num到process_begin_at
                    0.0,
                    None,
                    "0",
                    "1",  # process_duation到status
                ]

                cursor.execute(doc_query, doc_params)

                # 创建文件到文档的映射
                f2d_id = generate_uuid()
                f2d_query = """
                    INSERT INTO file2document (
                        id, create_time, create_date, update_time, update_date,
                        file_id, document_id
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s
                    )
                """

                f2d_params = [f2d_id, create_time, current_date, create_time, current_date, file_id, doc_id]

                cursor.execute(f2d_query, f2d_params)

                added_count += 1

            # 지식베이스 문서 수 업데이트
            if added_count > 0:
                try:
                    update_query = """
                        UPDATE knowledgebase 
                        SET doc_num = doc_num + %s,
                            update_date = %s
                        WHERE id = %s
                    """
                    cursor.execute(update_query, (added_count, current_date, kb_id))
                    conn.commit()  # 먼저 업데이트 커밋
                except Exception as e:
                    print(f"[WARNING] 지식베이스 문서 수 업데이트 실패, 문서는 추가됨: {str(e)}")

            cursor.close()
            conn.close()

            return {"added_count": added_count}

        except Exception as e:
            print(f"[ERROR] 문서 추가 실패: {str(e)}")
            print(f"[ERROR] 에러 타입: {type(e)}")
            import traceback

            print(f"[ERROR] 스택 정보: {traceback.format_exc()}")
            raise Exception(f"지식베이스에 문서 추가 실패: {str(e)}")

    @classmethod
    def delete_document(cls, doc_id):
        """删除文档"""
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # 先检查文档是否存在
            # check_query = """
            #     SELECT 
            #         d.kb_id, 
            #         kb.created_by AS tenant_id  -- 获取 tenant_id (knowledgebase的创建者)
            #     FROM document d
            #     JOIN knowledgebase kb ON d.kb_id = kb.id -- JOIN knowledgebase 表
            #     WHERE d.id = %s
            # """
            check_query = """
                SELECT 
                    d.kb_id, 
                    d.created_by AS tenant_id
                FROM document d
                WHERE d.id = %s
            """
            cursor.execute(check_query, (doc_id,))
            doc_data = cursor.fetchone()

            if not doc_data:
                print(f"[INFO] 문서 {doc_id}가 DB에서 발견되지 않음.")
                return False

            kb_id = doc_data["kb_id"]

            # 파일-문서 매핑 삭제
            f2d_query = "DELETE FROM file2document WHERE document_id = %s"
            cursor.execute(f2d_query, (doc_id,))

            # 문서 삭제
            doc_query = "DELETE FROM document WHERE id = %s"
            cursor.execute(doc_query, (doc_id,))

            # 지식베이스 문서 수 업데이트
            update_query = """
                UPDATE knowledgebase 
                SET doc_num = doc_num - 1,
                    update_date = %s
                WHERE id = %s
            """
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(update_query, (current_date, kb_id))

            conn.commit()
            cursor.close()
            conn.close()

            es_client = get_es_client()
            tenant_id_for_cleanup = doc_data["tenant_id"]

            # Elasticsearch에서 관련 문서 블록 삭제
            if es_client and tenant_id_for_cleanup:
                es_index_name = f"ragflow_{tenant_id_for_cleanup}"
                try:
                    if es_client.indices.exists(index=es_index_name):
                        query_body = {"query": {"term": {"doc_id": doc_id}}}
                        resp = es_client.delete_by_query(
                            index=es_index_name,
                            body=query_body,
                            refresh=True,  # 즉시 반영
                            ignore_unavailable=True,  # 인덱스가 삭제된 경우 무시
                        )
                        deleted_count = resp.get("deleted", 0)
                        print(f"[ES-SUCCESS] 인덱스 {es_index_name}에서 doc_id {doc_id} 관련 블록 {deleted_count}개 삭제.")
                    else:
                        print(f"[ES-INFO] 인덱스 {es_index_name}가 존재하지 않아 ES 정리 생략 for doc_id {doc_id}.")
                except Exception as es_err:
                    print(f"[ES-ERROR] doc_id {doc_id} (index {es_index_name})의 ES 블록 정리 실패: {str(es_err)}")

            return True

        except Exception as e:
            print(f"[ERROR] 문서 삭제 실패: {str(e)}")
            raise Exception(f"문서 삭제 실패: {str(e)}")

    @classmethod
    def parse_document(cls, doc_id):
        """解析文档"""
        conn = None
        cursor = None
        try:
            # 获取文档和文件信息
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # 查询文档信息
            doc_query = """
                SELECT d.id, d.name, d.location, d.type, d.kb_id, d.parser_id, d.parser_config, d.created_by
                FROM document d
                WHERE d.id = %s
            """
            cursor.execute(doc_query, (doc_id,))
            doc_info = cursor.fetchone()

            if not doc_info:
                raise Exception("文档不存在")

            # 获取关联的文件信息 (主要是 parent_id 作为 bucket_name)
            f2d_query = "SELECT file_id FROM file2document WHERE document_id = %s"
            cursor.execute(f2d_query, (doc_id,))
            f2d_result = cursor.fetchone()

            if not f2d_result:
                raise Exception("无法找到文件到文档的映射关系")

            file_id = f2d_result["file_id"]
            file_query = "SELECT parent_id FROM file WHERE id = %s"
            cursor.execute(file_query, (file_id,))
            file_info = cursor.fetchone()

            if not file_info:
                raise Exception("无法找到文件记录")

            # 获取知识库创建人信息
            # 根据doc_id查询document这张表，得到kb_id
            kb_id_query = "SELECT kb_id FROM document WHERE id = %s"
            cursor.execute(kb_id_query, (doc_id,))
            kb_id = cursor.fetchone()
            # 根据kb_id查询knowledgebase这张表，得到created_by
            kb_query = "SELECT created_by FROM knowledgebase WHERE id = %s"
            cursor.execute(kb_query, (kb_id["kb_id"],))
            kb_info = cursor.fetchone()

            cursor.close()
            conn.close()
            conn = None  # 确保连接已关闭

            # 更新文档状态为处理中 (使用 parser 模块的函数)
            _update_document_progress(doc_id, status="2", run="1", progress=0.0, message="开始解析")

            # 调用后台解析函数
            embedding_config = cls.get_kb_embedding_config(kb_id["kb_id"])
            parse_result = perform_parse(doc_id, doc_info, file_info, embedding_config, kb_info)

            # 返回解析结果
            return parse_result

        except Exception as e:
            print(f"문서 파싱 시작 또는 실행 중 오류 발생 (Doc ID: {doc_id}): {str(e)}")
            # 예외 발생 시 상태를 실패로 업데이트
            try:
                _update_document_progress(doc_id, status="1", run="0", message=f"파싱 실패: {str(e)}")
            except Exception as update_err:
                print(f"문서 실패 상태 업데이트 중 오류 (Doc ID: {doc_id}): {str(update_err)}")
            # raise Exception(f"문서 파싱 실패: {str(e)}")
            return {"success": False, "error": f"문서 파싱 실패: {str(e)}"}

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @classmethod
    def async_parse_document(cls, doc_id):
        """异步解析文档"""
        try:
            # 백그라운드 스레드로 동기 parse_document 실행
            thread = threading.Thread(target=cls.parse_document, args=(doc_id,))
            thread.daemon = True  # 데몬 스레드로 설정, 메인 종료 시 같이 종료
            thread.start()

            # 즉시 반환, 작업이 제출됨을 알림
            return {
                "task_id": doc_id,  # doc_id를 태스크 식별자로 사용
                "status": "processing",
                "message": "문서 파싱 작업이 백그라운드로 제출되었습니다",
            }
        except Exception as e:
            print(f"비동기 파싱 태스크 시작 실패 (Doc ID: {doc_id}): {str(e)}")
            try:
                _update_document_progress(doc_id, status="1", run="0", message=f"파싱 시작 실패: {str(e)}")
            except Exception as update_err:
                print(f"문서 파싱 시작 실패 상태 업데이트 중 오류 (Doc ID: {doc_id}): {str(update_err)}")
            raise Exception(f"비동기 파싱 태스크 시작 실패: {str(e)}")

    @classmethod
    def get_document_parse_progress(cls, doc_id):
        """获取文档解析进度"""
        conn = None
        cursor = None
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query = """
                SELECT progress, progress_msg, status, run
                FROM document
                WHERE id = %s
            """
            cursor.execute(query, (doc_id,))
            result = cursor.fetchone()

            if not result:
                return {"error": "문서가 존재하지 않습니다"}

            # 确保 progress 是浮点数
            progress_value = 0.0
            if result.get("progress") is not None:
                try:
                    progress_value = float(result["progress"])
                except (ValueError, TypeError):
                    progress_value = 0.0  # 或记录错误

            return {
                "progress": progress_value,
                "message": result.get("progress_msg", ""),
                "status": result.get("status", "0"),
                "running": result.get("run", "0"),
            }

        except Exception as e:
            print(f"문서 진행률 가져오기 실패 (Doc ID: {doc_id}): {str(e)}")
            return {"error": f"진행률 가져오기 실패: {str(e)}"}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # --- 가장 오래된 사용자 ID 가져오기 ---
    @classmethod
    def _get_earliest_user_tenant_id(cls):
        """생성일이 가장 오래된 사용자의 ID (tenant_id로 사용)"""
        conn = None
        cursor = None
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor()
            query = "SELECT id FROM user ORDER BY create_time ASC LIMIT 1"
            cursor.execute(query)
            result = cursor.fetchone()
            if result:
                return result[0]  # 返回用户 ID
            else:
                print("경고: DB에 사용자가 없습니다!")
                return None
        except Exception as e:
            print(f"가장 오래된 사용자 쿼리 중 오류: {e}")
            traceback.print_exc()
            return None
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    # --- 임베딩 연결 테스트 ---
    @classmethod
    def _test_embedding_connection(cls, base_url, model_name, api_key):
        """
        커스텀 임베딩 모델 연결 테스트 (requests 사용)
        """
        print(f"연결 테스트 시작: base_url={base_url}, model_name={model_name}")
        try:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = {"input": ["Test connection"], "model": model_name}

            if not base_url.startswith(("http://", "https://")):
                base_url = "http://" + base_url
            if not base_url.endswith("/"):
                base_url += "/"

            # --- URL 조합 최적화 ---
            endpoint_segment = "embeddings"
            full_endpoint_path = "v1/embeddings"
            # 移除末尾斜杠以方便判断
            normalized_base_url = base_url.rstrip("/")

            if normalized_base_url.endswith("/v1"):
                # 如果 base_url 已经是 http://host/v1 形式
                current_test_url = normalized_base_url + "/" + endpoint_segment
            elif normalized_base_url.endswith("/embeddings"):
                # 如果 base_url 已经是 http://host/embeddings 形式(比如硅基流动API，无需再进行处理)
                current_test_url = normalized_base_url
            else:
                # 如果 base_url 是 http://host 或 http://host/api 形式
                current_test_url = normalized_base_url + "/" + full_endpoint_path

            # --- URL 조합 최적화 끝 ---
            print(f"요청 시도 URL: {current_test_url}")
            try:
                response = requests.post(current_test_url, headers=headers, json=payload, timeout=15)
                print(f"요청 {current_test_url} 응답 코드: {response.status_code}")

                if response.status_code == 200:
                    res_json = response.json()
                    if (
                        "data" in res_json and isinstance(res_json["data"], list) and len(res_json["data"]) > 0 and "embedding" in res_json["data"][0] and len(res_json["data"][0]["embedding"]) > 0
                    ) or (isinstance(res_json, list) and len(res_json) > 0 and isinstance(res_json[0], list) and len(res_json[0]) > 0):
                        print(f"연결 테스트 성공: {current_test_url}")
                        return True, "连接成功"
                    else:
                        print(f"연결 성공했으나 응답 포맷이 올바르지 않음: {current_test_url}")

            except Exception as json_e:
                print(f"JSON 응답 파싱 실패: {current_test_url}: {json_e}")

            return False, "연결 실패: 응답 오류"

        except Exception as e:
            print(f"연결 테스트 중 알 수 없는 오류: {str(e)}")
            traceback.print_exc()
            return False, f"테스트 중 알 수 없는 오류: {str(e)}"
    
    # --- 지식베이스 임베딩 설정 가져오기 ---
    @classmethod
    def get_kb_embedding_config(cls,kb_id):
        """
        시스템 임베딩 설정에서 지식베이스에 해당하는 임베딩 설정 가져오기
        args:
            kb_id: 지식베이스 ID
        returns:
            dict: llm_name, api_key, api_base 포함 설정 딕셔너리
        """
        if not kb_id:
            return {"llm_name": "", "api_key": "", "api_base": ""}

        conn = None
        cursor = None
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)  # 使用字典游标方便访问列名
            # 1. 가장 오래된 사용자 ID 찾기
            query_earliest_user = """
            SELECT id FROM user
            ORDER BY create_time ASC
            LIMIT 1
            """
            cursor.execute(query_earliest_user)
            earliest_user = cursor.fetchone()
            earliest_user_id = earliest_user["id"]

            # 2. 가장 오래된 사용자 ID로 tenant_llm 테이블에서 embedding 설정 조회
            query_embedding_config = """
                SELECT llm_name, api_key, api_base
                FROM tenant_llm
                WHERE tenant_id = %s AND model_type = 'embedding'
                ORDER BY create_time DESC
            """
            cursor.execute(query_embedding_config, (earliest_user_id,))
            config = cursor.fetchall()

            # 3. kb_id로 knowledgebase 테이블에서 embd_id 조회
            kb_query = "SELECT embd_id FROM knowledgebase WHERE id = %s"
            cursor.execute(kb_query, (kb_id,))
            kb_embd_info= cursor.fetchone()

            # 4. 시스템 설정에서 지식베이스의 임베딩 설정 찾기
            if config:
                for row in config:
                    if row["llm_name"] and "___" in row["llm_name"]:
                        row["llm_name"] = row["llm_name"].split("___")[0]
                    if row["llm_name"]==kb_embd_info['embd_id']:
                        llm_name = row.get("llm_name", "")
                        api_key = row.get("api_key", "")
                        api_base = row.get("api_base", "")

                        # # 실리콘플로우 플랫폼 특이 처리
                        # if llm_name == "netease-youdao/bce-embedding-base_v1":
                        #     llm_name = "BAAI/bge-m3"

                        # API base가 빈 문자열이면 실리콘플로우 기본값 사용
                        if api_base == "":
                            api_base = "https://api.siliconflow.cn/v1/embeddings"

                        return {"llm_name": llm_name, "api_key": api_key, "api_base": api_base}

        except Exception as e:
            print(f"지식베이스 임베딩 설정 가져오기 오류: {e}")
            traceback.print_exc()
            # 기존 예외 처리 유지, 호출자에게 위임
            raise Exception(f"설정 가져오기 DB 오류: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    # --- 시스템 임베딩 설정 가져오기 ---
    @classmethod
    def get_system_embedding_config(cls):
        """시스템(가장 오래된 사용자)의 임베딩 설정 가져오기"""
        conn = None
        cursor = None
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)  # 使用字典游标方便访问列名

            # 1. 가장 오래된 사용자 ID 찾기
            query_earliest_user = """
                SELECT id FROM user
                ORDER BY create_time ASC
                LIMIT 1
            """
            cursor.execute(query_earliest_user)
            earliest_user = cursor.fetchone()

            if not earliest_user:
                # 사용자가 없으면 빈 설정 반환
                return {"llm_name": "", "api_key": "", "api_base": ""}

            earliest_user_id = earliest_user["id"]

            # 2. 가장 오래된 사용자 ID로 tenant_llm 테이블에서 embedding 설정 조회
            query_embedding_config = """
                SELECT llm_name, api_key, api_base
                FROM tenant_llm
                WHERE tenant_id = %s AND model_type = 'embedding'
                ORDER BY update_time DESC, create_time DESC
                LIMIT 1
            """
            cursor.execute(query_embedding_config, (earliest_user_id,))
            config = cursor.fetchone()

            if config:
                llm_name = config.get("llm_name", "")
                api_key = config.get("api_key", "")
                api_base = config.get("api_base", "")
                # 모델명 처리 (필요시)
                if llm_name and "___" in llm_name:
                    llm_name = llm_name.split("___")[0]

                # 실리콘플로우 특수 처리 제거, 원본 모델명 유지
                # 아래 코드 주석 처리로 읽기/저장 일관성 유지
                # if llm_name == "netease-youdao/bce-embedding-base_v1":
                #     llm_name = "BAAI/bge-m3"

                # API base가 빈 문자열이면 실리콘플로우 기본값 사용
                if api_base == "":
                    api_base = "https://api.siliconflow.cn/v1/embeddings"

                # 설정 있으면 반환
                return {"llm_name": llm_name, "api_key": api_key, "api_base": api_base}
            else:
                # 가장 오래된 사용자가 embedding 설정 없으면 빈 값 반환
                return {"llm_name": "", "api_key": "", "api_base": ""}
        except Exception as e:
            print(f"시스템 임베딩 설정 가져오기 오류: {e}")
            traceback.print_exc()
            # 기존 예외 처리 유지, 호출자에게 위임
            raise Exception(f"설정 가져오기 DB 오류: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    # --- 시스템 임베딩 설정 저장 ---
    @classmethod
    def set_system_embedding_config(cls, llm_name, api_base, api_key):
        """设置系统级（最早用户）的 Embedding 配置"""
        tenant_id = cls._get_earliest_user_tenant_id()
        if not tenant_id:
            raise Exception("시스템 기본 사용자를 찾을 수 없습니다")

        print(f"시스템 임베딩 설정 저장 시작: {llm_name}, {api_base}, {api_key}")
        # 연결 테스트 실행
        is_connected, message = cls._test_embedding_connection(base_url=api_base, model_name=llm_name, api_key=api_key)

        if not is_connected:
            # 구체적인 테스트 실패 사유를 호출자(라우터)에 반환
            return False, f"연결 테스트 실패: {message}"

        # 연결 테스트 성공, DB에 설정 저장
        conn = None
        cursor = None
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # 检查是否已存在该租户的 embedding 配置
            check_query = """
                SELECT tenant_id, llm_name FROM tenant_llm 
                WHERE tenant_id = %s AND model_type = 'embedding' AND llm_name = %s
            """
            cursor.execute(check_query, (tenant_id, llm_name))
            existing_config = cursor.fetchone()

            current_time = datetime.now()
            create_date = current_time.strftime("%Y-%m-%d %H:%M:%S")
            create_time = int(current_time.timestamp() * 1000)

            if existing_config:
                # 更新现有配置
                update_query = """
                    UPDATE tenant_llm 
                    SET api_base = %s, api_key = %s, update_date = %s, update_time = %s
                    WHERE tenant_id = %s AND model_type = 'embedding' AND llm_name = %s
                """
                cursor.execute(update_query, (api_base, api_key, create_date, create_time, tenant_id, llm_name))
                print(f"기존 임베딩 설정 업데이트: {llm_name}")
            else:
                # 插入新配置
                insert_query = """
                    INSERT INTO tenant_llm (
                        create_time, create_date, update_time, update_date,
                        tenant_id, llm_name, model_type, llm_factory, api_base, api_key, max_tokens, used_tokens
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                cursor.execute(insert_query, (
                    create_time, create_date, create_time, create_date,
                    tenant_id, llm_name, 'embedding', 'Custom', api_base, api_key, '0', 0
                ))
                print(f"새 임베딩 설정 삽입: {llm_name}")

            conn.commit()
            return True, "설정 저장 성공, 연결 테스트 통과"

        except Exception as e:
            print(f"임베딩 설정 저장 실패: {str(e)}")
            traceback.print_exc()
            return False, f"설정 저장 실패: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    # 순차적 배치 파싱 (핵심 로직, 백그라운드 스레드에서 실행)
    @classmethod
    def _run_sequential_batch_parse(cls, kb_id):
        """순차적으로 배치 파싱을 실행하고 SEQUENTIAL_BATCH_TASKS에 상태를 업데이트"""
        global SEQUENTIAL_BATCH_TASKS
        task_info = SEQUENTIAL_BATCH_TASKS.get(kb_id)
        if not task_info:
            print(f"[Seq Batch ERROR] Task info for KB {kb_id} not found at start.")
            return  # 理论上不应发生

        conn = None
        cursor = None
        parsed_count = 0
        failed_count = 0
        total_count = 0

        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # 파싱이 필요한 문서 쿼리
            query = """
                SELECT id, name FROM document
                WHERE kb_id = %s AND run != '3'
            """
            cursor.execute(query, (kb_id,))
            documents_to_parse = cursor.fetchall()
            total_count = len(documents_to_parse)

            # 작업 총 개수 업데이트
            task_info["total"] = total_count
            task_info["status"] = "running"
            task_info["message"] = f"총 {total_count}개 문서 파싱 대기 중."
            task_info["start_time"] = time.time()
            start_time = time.time()
            SEQUENTIAL_BATCH_TASKS[kb_id] = task_info  # 딕셔너리 업데이트

            if not documents_to_parse:
                task_info["status"] = "completed"
                task_info["message"] = "파싱할 문서가 없습니다."
                SEQUENTIAL_BATCH_TASKS[kb_id] = task_info
                print(f"[Seq Batch] KB {kb_id}: 파싱할 문서가 없습니다.")
                return

            print(f"[Seq Batch] KB {kb_id}: 순차적으로 {total_count}개 문서 파싱 시작...")

            # 각 문서 순차 파싱
            for i, doc in enumerate(documents_to_parse):
                doc_id = doc["id"]
                doc_name = doc["name"]

                # 현재 진행도 업데이트
                task_info["current"] = i + 1
                task_info["message"] = f"파싱 중: {doc_name} ({i + 1}/{total_count})"
                SEQUENTIAL_BATCH_TASKS[kb_id] = task_info
                print(f"[Seq Batch] KB {kb_id}: ({i + 1}/{total_count}) {doc_name} (ID: {doc_id}) 파싱 중...")

                try:
                    # 동기 parse_document 호출
                    # 내부적으로 단일 문서 상태(run, status) 업데이트
                    result = cls.parse_document(doc_id)
                    if result and result.get("success"):
                        parsed_count += 1
                        print(f"[Seq Batch] KB {kb_id}: 문서 {doc_id} 파싱 성공.")
                    else:
                        failed_count += 1
                        error_msg = result.get("message", "알 수 없는 오류") if result else "알 수 없는 오류"
                        print(f"[Seq Batch] KB {kb_id}: 문서 {doc_id} 파싱 실패: {error_msg}")
                except Exception as e:
                    failed_count += 1
                    print(f"[Seq Batch ERROR] KB {kb_id}: parse_document 호출 오류 {doc_id}: {str(e)}")
                    traceback.print_exc()
                    # 문서 상태를 실패로 업데이트
                    try:
                        _update_document_progress(doc_id, status="1", run="0", progress=0.0, message=f"배치 작업 중 파싱 실패: {str(e)[:255]}")
                    except Exception as update_err:
                        print(f"[Service-ERROR] 문서 {doc_id} 실패 상태 업데이트 오류: {str(update_err)}")

            # 작업 완료
            end_time = time.time()
            duration = round(end_time - task_info.get("start_time", start_time), 2)
            final_message = f"배치 순차 파싱 완료. 총 {total_count}개, 성공 {parsed_count}개, 실패 {failed_count}개. 소요 {duration}초."
            task_info["status"] = "completed"
            task_info["message"] = final_message
            task_info["current"] = total_count
            SEQUENTIAL_BATCH_TASKS[kb_id] = task_info
            print(f"[Seq Batch] KB {kb_id}: {final_message}")

        except Exception as e:
            # 작업 중 심각한 오류 발생
            error_message = f"배치 순차 파싱 중 심각한 오류 발생: {str(e)}"
            print(f"[Seq Batch ERROR] KB {kb_id}: {error_message}")
            traceback.print_exc()
            task_info["status"] = "failed"
            task_info["message"] = error_message
            SEQUENTIAL_BATCH_TASKS[kb_id] = task_info
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    # 순차적 배치 파싱 시작 (비동기 요청)
    @classmethod
    def start_sequential_batch_parse_async(cls, kb_id):
        """异步启动知识库的顺序批量解析任务"""
        global SEQUENTIAL_BATCH_TASKS
        if kb_id in SEQUENTIAL_BATCH_TASKS and SEQUENTIAL_BATCH_TASKS[kb_id].get("status") == "running":
            return {"success": False, "message": "해당 지식베이스의 배치 파싱 작업이 이미 실행 중입니다."}

        # 작업 상태 초기화
        start_time = time.time()
        SEQUENTIAL_BATCH_TASKS[kb_id] = {"status": "starting", "total": 0, "current": 0, "message": "작업 준비 중...", "start_time": start_time}

        try:
            # 백그라운드 스레드로 순차 파싱 로직 실행
            thread = threading.Thread(target=cls._run_sequential_batch_parse, args=(kb_id,))
            thread.daemon = True
            thread.start()
            print(f"[Seq Batch] KB {kb_id}: 백그라운드 순차 파싱 스레드 시작.")

            return {"success": True, "message": "순차 배치 파싱 작업이 시작되었습니다."}

        except Exception as e:
            error_message = f"순차 배치 파싱 작업 시작 실패: {str(e)}"
            print(f"[Seq Batch ERROR] KB {kb_id}: {error_message}")
            traceback.print_exc()
            # 작업 상태를 실패로 업데이트
            SEQUENTIAL_BATCH_TASKS[kb_id] = {"status": "failed", "total": 0, "current": 0, "message": error_message, "start_time": start_time}
            return {"success": False, "message": error_message}

    # 순차 배치 파싱 진행률 가져오기
    @classmethod
    def get_sequential_batch_parse_progress(cls, kb_id):
        """获取指定知识库的顺序批量解析任务进度"""
        global SEQUENTIAL_BATCH_TASKS
        task_info = SEQUENTIAL_BATCH_TASKS.get(kb_id)

        if not task_info:
            return {"status": "not_found", "message": "해당 지식베이스의 배치 파싱 작업 기록을 찾을 수 없습니다."}

        # 返回当前任务状态
        return task_info

    # 지식베이스 모든 문서 상태 가져오기 (리스트 새로고침용)
    @classmethod
    def get_knowledgebase_parse_progress(cls, kb_id):
        """지정한 지식베이스의 모든 문서 파싱 진행률 및 상태 가져오기 (변경 없음)"""
        conn = None
        cursor = None
        try:
            conn = cls._get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query = """
                SELECT id, name, progress, progress_msg, status, run
                FROM document
                WHERE kb_id = %s
                ORDER BY create_date DESC -- 或者其他排序方式
            """
            cursor.execute(query, (kb_id,))
            documents_status = cursor.fetchall()

            # progress를 float으로 변환
            for doc in documents_status:
                progress_value = 0.0
                if doc.get("progress") is not None:
                    try:
                        progress_value = float(doc["progress"])
                    except (ValueError, TypeError):
                        progress_value = 0.0
                doc["progress"] = progress_value
                # 다른 필드도 기본값 보장
                doc["progress_msg"] = doc.get("progress_msg", "")
                doc["status"] = doc.get("status", "0")
                doc["run"] = doc.get("run", "0")

            return {"documents": documents_status}

        except Exception as e:
            print(f"지식베이스 {kb_id} 문서 진행률 가져오기 실패: {str(e)}")
            traceback.print_exc()
            return {"error": f"지식베이스 문서 진행률 가져오기 실패: {str(e)}"}
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    @classmethod
    def get_tenant_embedding(cls,kb_id):
        """테넌트의 임베딩 모델 설정 가져오기

        Returns:
            dict: {llm_name,llm_factory} 테넌트 임베딩 모델 설정
        """
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)

            # 테넌트 임베딩 모델 설정 찾기
            query = """  
            SELECT tl.llm_name, tl.llm_factory, tl.tenant_id
            FROM tenant_llm tl  
            JOIN knowledgebase kb ON tl.tenant_id = kb.tenant_id  
            WHERE kb.id = %s AND tl.model_type = 'embedding'  
            ORDER BY tl.llm_factory DESC  
            """
            cursor.execute(query,(kb_id,))
            results = cursor.fetchall()
            
            if results:
                for result in results:
                    if result["llm_name"] and "__" in result["llm_name"]:
                        result["llm_name"] = result["llm_name"].split("__")[0]
            else:
                return {"error": "테넌트 임베딩 모델 설정 오류: 관련 설정을 찾을 수 없음"}
            return results
            
        except Exception as e:
            print(f"테넌트 임베딩 모델 설정 오류: {e}")
            return {"error": f"테넌트 임베딩 모델 설정 오류: {str(e)}"}
        finally:
            if cursor:
                    cursor.close()
            if conn and conn.is_connected():
                conn.close()
