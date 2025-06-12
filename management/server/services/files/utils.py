import uuid
from enum import Enum

from strenum import StrEnum


class FileType(StrEnum):
    FOLDER = "folder"
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    PPT = "ppt"
    VISUAL = "visual"
    TEXT = "txt"
    HTML = "html"
    OTHER = "other"


class FileSource(StrEnum):
    LOCAL = ""
    KNOWLEDGEBASE = "knowledgebase"
    S3 = "s3"


class StatusEnum(Enum):
    VALID = "1"
    INVALID = "0"


# 参考：api.utils
def get_uuid():
    return uuid.uuid1().hex
