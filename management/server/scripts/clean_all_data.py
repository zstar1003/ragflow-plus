import os
from dotenv import load_dotenv
import mysql.connector
from minio import Minio

# 加载环境变量
load_dotenv("../../docker/.env")

# 数据库连接配置
DB_CONFIG = {"host": "localhost", "port": int(os.getenv("MYSQL_PORT", "5455")), "user": "root", "password": os.getenv("MYSQL_PASSWORD", "infini_rag_flow"), "database": "rag_flow"}

# MinIO连接配置
MINIO_CONFIG = {
    "endpoint": "localhost:" + os.getenv("MINIO_PORT", "9000"),
    "access_key": os.getenv("MINIO_USER", "rag_flow"),
    "secret_key": os.getenv("MINIO_PASSWORD", "infini_rag_flow"),
    "secure": False,
}


def get_minio_client():
    """创建MinIO客户端"""
    return Minio(endpoint=MINIO_CONFIG["endpoint"], access_key=MINIO_CONFIG["access_key"], secret_key=MINIO_CONFIG["secret_key"], secure=MINIO_CONFIG["secure"])


def clear_database_tables():
    """清空数据库表"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 禁用外键检查
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

        # 清空表数据
        tables = ["document", "file2document", "file"]
        for table in tables:
            cursor.execute(f"TRUNCATE TABLE {table}")
            print(f"已清空表: {table}")

        # 启用外键检查
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        conn.commit()
        cursor.close()
        conn.close()

        print("数据库表已全部清空")

    except Exception as e:
        print(f"清空数据库表失败: {str(e)}")
        raise


def clear_minio_buckets():
    """清空并删除MinIO所有存储桶"""
    try:
        minio_client = get_minio_client()
        buckets = minio_client.list_buckets()

        if not buckets:
            print("MinIO中没有存储桶需要清理")
            return

        print(f"开始清理 {len(buckets)} 个MinIO存储桶...")

        for bucket in buckets:
            bucket_name = bucket.name

            # 跳过系统保留的存储桶
            if bucket_name.startswith("."):
                print(f"跳过系统存储桶: {bucket_name}")
                continue

            try:
                # 递归删除存储桶中的所有对象(包括版本控制对象)
                objects = minio_client.list_objects(bucket_name, recursive=True)
                for obj in objects:
                    try:
                        # 强制删除对象(包括所有版本)
                        minio_client.remove_object(bucket_name, obj.object_name, version_id=obj.version_id)
                    except Exception as e:
                        print(f"删除对象 {obj.object_name} 失败: {str(e)}")
                        continue

                # 确保所有对象已删除
                while True:
                    remaining_objects = list(minio_client.list_objects(bucket_name))
                    if not remaining_objects:
                        break
                    for obj in remaining_objects:
                        minio_client.remove_object(bucket_name, obj.object_name)

                # 实际删除存储桶
                try:
                    minio_client.remove_bucket(bucket_name)
                    print(f"已删除存储桶: {bucket_name}")
                except Exception as e:
                    print(f"删除存储桶 {bucket_name} 失败: {str(e)}. 尝试强制删除...")
                    # 强制删除存储桶(即使非空)
                    try:
                        # 再次确保删除所有对象
                        objects = minio_client.list_objects(bucket_name, recursive=True)
                        for obj in objects:
                            minio_client.remove_object(bucket_name, obj.object_name)
                        minio_client.remove_bucket(bucket_name)
                        print(f"已强制删除存储桶: {bucket_name}")
                    except Exception as e:
                        print(f"强制删除存储桶 {bucket_name} 仍然失败: {str(e)}")

            except Exception as e:
                print(f"处理存储桶 {bucket_name} 时发生错误: {str(e)}")

        print("MinIO存储桶清理完成")

    except Exception as e:
        print(f"清理MinIO存储桶失败: {str(e)}")
        raise


def confirm_action():
    """确认操作"""
    print("警告: 此操作将永久删除所有数据!")
    confirmation = input("确认要清空所有数据吗? (输入'y'确认): ")
    return confirmation.lower() == "y"


if __name__ == "__main__":
    if confirm_action():
        print("开始清理数据...")
        clear_database_tables()
        clear_minio_buckets()
        print("数据清理完成")
    else:
        print("操作已取消")
