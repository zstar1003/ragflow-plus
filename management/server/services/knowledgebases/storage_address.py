"""Resolve recorded storage metadata, never infer a bucket from folder names."""


def document_storage_address(document, file):
    source = file.get("source_type")
    if source in (None, "", "local"):
        # File-manager uploads use a physical bucket and the file's own key.
        bucket, location = file.get("parent_id"), file.get("location")
    elif source == "knowledgebase":
        # SDK uploads store in the KB bucket; parent_id is only a UI folder.
        bucket, location = document.get("kb_id"), document.get("location")
    else:
        raise ValueError("管理端解析不支持此文件存储来源")
    if not isinstance(bucket, str) or not bucket.strip() or not isinstance(location, str) or not location:
        raise ValueError("文件缺少有效的存储桶或对象路径")
    return bucket, location
