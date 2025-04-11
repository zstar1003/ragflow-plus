from peewee import *
from .base_service import BaseService
from .models import Document
from .utils import get_uuid, StatusEnum

class DocumentService(BaseService):
    model = Document
    
    @classmethod
    def create_document(cls, kb_id: str, name: str, location: str, size: int, file_type: str, created_by: str = None, parser_id: str = None, parser_config: dict = None) -> Document:
        """
        创建文档记录
        
        Args:
            kb_id: 知识库ID
            name: 文件名
            location: 存储位置
            size: 文件大小
            file_type: 文件类型
            created_by: 创建者ID
            parser_id: 解析器ID
            parser_config: 解析器配置
            
        Returns:
            Document: 创建的文档对象
        """
        doc_id = get_uuid()
        
        # 构建基本文档数据
        doc_data = {
            'id': doc_id,
            'kb_id': kb_id,
            'name': name,
            'location': location,
            'size': size,
            'type': file_type,
            'created_by': created_by or 'system',
            'parser_id': parser_id or '',
            'parser_config': parser_config or {"pages": [[1, 1000000]]},
            'source_type': 'local',
            'token_num': 0,
            'chunk_num': 0,
            'progress': 0,
            'progress_msg': '',
            'run': '0',  # 未开始解析
            'status': StatusEnum.VALID.value
        }
        
        return cls.insert(doc_data)
    
    @classmethod
    def get_by_kb_id(cls, kb_id: str) -> list[Document]:
        return cls.query(kb_id=kb_id)