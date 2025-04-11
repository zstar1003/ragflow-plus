from peewee import *
from .base_service import BaseService
from .models import File2Document

class File2DocumentService(BaseService):
    model = File2Document
    
    @classmethod
    def create_mapping(cls, file_id: str, document_id: str) -> File2Document:
        return cls.insert({
            'file_id': file_id,
            'document_id': document_id
        })
    
    @classmethod
    def get_by_document_id(cls, document_id: str) -> list[File2Document]:
        return cls.query(document_id=document_id)
    
    @classmethod
    def get_by_file_id(cls, file_id: str) -> list[File2Document]:
        return cls.query(file_id=file_id)