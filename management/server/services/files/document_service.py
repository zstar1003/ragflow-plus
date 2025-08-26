from peewee import *  # noqa: F403

from .base_service import BaseService
from .models import Document
from .utils import StatusEnum, get_uuid


class DocumentService(BaseService):
    model = Document

    @classmethod
    def create_document(cls, kb_id: str, name: str, location: str, size: int, file_type: str, created_by: str = None, parser_id: str = None, parser_config: dict = None) -> Document:
        """
        문서 기록 생성

        Args:
            kb_id: 지식베이스 ID
            name: 파일명
            location: 저장 위치
            size: 파일 크기
            file_type: 파일 타입
            created_by: 생성자 ID
            parser_id: 파서 ID
            parser_config: 파서 설정

        Returns:
            Document: 생성된 문서 객체
        """
        doc_id = get_uuid()

        # 기본 문서 데이터 구성
        doc_data = {
            "id": doc_id,
            "kb_id": kb_id,
            "name": name,
            "location": location,
            "size": size,
            "type": file_type,
            "created_by": created_by or "system",
            "parser_id": parser_id or "",
            "parser_config": parser_config or {"pages": [[1, 1000000]]},
            "source_type": "local",
            "token_num": 0,
            "chunk_num": 0,
            "progress": 0,
            "progress_msg": "",
            "run": "0",  # 파싱 시작 전
            "status": StatusEnum.VALID.value,
        }

        return cls.insert(doc_data)

    @classmethod
    def get_by_kb_id(cls, kb_id: str) -> list[Document]:
        return cls.query(kb_id=kb_id)
