import os
from dotenv import load_dotenv
import mysql.connector
from minio import Minio

# 加载环境变量
load_dotenv("../../docker/.env")

# 数据库连接配置
DB_CONFIG = {
    "host": "localhost",
    "port": int(os.getenv("MYSQL_PORT", "5455")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD", "infini_rag_flow"),
    "database": "rag_flow"
}

# MinIO连接配置
MINIO_CONFIG = {
    "endpoint": "localhost:" + os.getenv("MINIO_PORT", "9000"),
    "access_key": os.getenv("MINIO_USER", "rag_flow"),
    "secret_key": os.getenv("MINIO_PASSWORD", "infini_rag_flow"),
    "secure": False
}

def get_used_buckets_from_db():
    """从数据库获取正在使用的存储桶(kb_id)列表"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 查询所有不重复的kb_id
        cursor.execute("SELECT DISTINCT kb_id FROM document")
        kb_ids = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return kb_ids
        
    except Exception as e:
        print(f"数据库查询失败: {str(e)}")
        return []

def cleanup_unused_buckets():
    """清理未使用的MinIO存储桶"""
    try:
        # 获取MinIO客户端
        minio_client = Minio(
            endpoint=MINIO_CONFIG["endpoint"],
            access_key=MINIO_CONFIG["access_key"],
            secret_key=MINIO_CONFIG["secret_key"],
            secure=MINIO_CONFIG["secure"]
        )
        
        # 获取数据库中的有效kb_id列表
        used_buckets = set(get_used_buckets_from_db())
        
        # 获取MinIO中的所有存储桶
        all_buckets = minio_client.list_buckets()
        minio_bucket_names = {bucket.name for bucket in all_buckets}
        
        # 计算需要删除的存储桶
        buckets_to_delete = minio_bucket_names - used_buckets
        
        if not buckets_to_delete:
            print("没有需要删除的多余存储桶")
            return
        
        print(f"发现 {len(buckets_to_delete)} 个多余存储桶需要清理:")
        
        # 删除多余的存储桶
        for bucket_name in buckets_to_delete:
            try:
                # 先确保存储桶为空
                objects = minio_client.list_objects(bucket_name)
                for obj in objects:
                    minio_client.remove_object(bucket_name, obj.object_name)
                
                # 删除存储桶
                minio_client.remove_bucket(bucket_name)
                print(f"已删除存储桶: {bucket_name}")
                
            except Exception as e:
                print(f"删除存储桶 {bucket_name} 失败: {str(e)}")
                
    except Exception as e:
        print(f"清理存储桶过程中发生错误: {str(e)}")

if __name__ == "__main__":
    cleanup_unused_buckets()