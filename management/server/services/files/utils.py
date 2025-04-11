import uuid
from strenum import StrEnum
from enum import Enum


# 参考：api.db
class FileType(StrEnum):
    FOLDER = "folder"
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    PPT = "ppt"
    VISUAL = "visual"
    TEXT = "txt"
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