from peewee import *  # noqa: F403

from .base_service import BaseService
from .models import File
from .utils import FileType, get_uuid


class FileService(BaseService):
    model = File

    @classmethod
    def create_file(cls, parent_id: str, name: str, location: str, size: int, file_type: str) -> File:
        return cls.insert({"parent_id": parent_id, "name": name, "location": location, "size": size, "type": file_type, "source_type": "knowledgebase"})

    @classmethod
    def get_parser(cls, file_type, filename, tenant_id):
        """파일 타입에 적합한 파서 ID 조회"""
        if file_type == FileType.PDF.value:
            return "pdf_parser"
        elif file_type == FileType.WORD.value:
            return "word_parser"
        elif file_type == FileType.EXCEL.value:
            return "excel_parser"
        elif file_type == FileType.PPT.value:
            return "ppt_parser"
        elif file_type == FileType.VISUAL.value:
            return "image_parser"
        elif file_type == FileType.TEXT.value:
            return "text_parser"
        else:
            return "default_parser"

    @classmethod
    def get_by_parent_id(cls, parent_id: str) -> list[File]:
        return cls.query(parent_id=parent_id)

    @classmethod
    def generate_bucket_name(cls):
        """랜덤 스토리지 버킷 이름 생성"""
        return f"kb-{get_uuid()}"
