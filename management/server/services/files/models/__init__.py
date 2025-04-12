from peewee import *
import os
from datetime import datetime
from database import DB_CONFIG

# 使用MySQL数据库
db = MySQLDatabase(
    DB_CONFIG["database"],
    host=DB_CONFIG["host"],
    port=DB_CONFIG["port"],
    user=DB_CONFIG["user"],
    password=DB_CONFIG["password"]
)

class BaseModel(Model):
    # 添加共同的时间戳字段
    create_time = BigIntegerField(null=True)
    create_date = CharField(null=True)
    update_time = BigIntegerField(null=True)
    update_date = CharField(null=True)
    
    class Meta:
        database = db

class Document(BaseModel):
    id = CharField(primary_key=True)
    thumbnail = TextField(null=True)
    kb_id = CharField(index=True)
    parser_id = CharField(null=True, index=True)
    parser_config = TextField(null=True)  # JSONField在SQLite中用TextField替代
    source_type = CharField(default="local", index=True)
    type = CharField(index=True)
    created_by = CharField(null=True, index=True)
    name = CharField(null=True, index=True)
    location = CharField(null=True)
    size = IntegerField(default=0)
    token_num = IntegerField(default=0)
    chunk_num = IntegerField(default=0)
    progress = FloatField(default=0)
    progress_msg = TextField(null=True, default="")
    process_begin_at = DateTimeField(null=True)
    process_duation = FloatField(default=0)
    meta_fields = TextField(null=True)  # JSONField
    run = CharField(default="0")
    status = CharField(default="1")
    
    class Meta:
        db_table = "document"

class File(BaseModel):
    id = CharField(primary_key=True)
    parent_id = CharField(index=True)
    tenant_id = CharField(null=True, index=True)
    created_by = CharField(null=True, index=True)
    name = CharField(index=True)
    location = CharField(null=True)
    size = IntegerField(default=0)
    type = CharField(index=True)
    source_type = CharField(default="", index=True)
    
    class Meta:
        db_table = "file"

class File2Document(BaseModel):
    id = CharField(primary_key=True)
    file_id = CharField(index=True)
    document_id = CharField(index=True)
    
    class Meta:
        db_table = "file2document"