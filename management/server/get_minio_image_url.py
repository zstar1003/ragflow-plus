import os
import sys
import argparse
from minio import Minio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("../../docker/.env")

def is_running_in_docker():
    # 检查是否存在/.dockerenv文件
    docker_env = os.path.exists('/.dockerenv')
    # 或者检查cgroup中是否包含docker字符串
    try:
        with open('/proc/self/cgroup', 'r') as f:
            return docker_env or 'docker' in f.read()
    except:
        return docker_env

MINIO_HOST = 'host.docker.internal' if is_running_in_docker() else 'localhost'

# MinIO连接配置
MINIO_CONFIG = {
    "endpoint": f"{MINIO_HOST}:{os.getenv('MINIO_PORT', '9000')}",
    "access_key": os.getenv("MINIO_USER", "rag_flow"),
    "secret_key": os.getenv("MINIO_PASSWORD", "infini_rag_flow"),
    "secure": False
}

def get_minio_client():
    """创建MinIO客户端"""
    return Minio(
        endpoint=MINIO_CONFIG["endpoint"],
        access_key=MINIO_CONFIG["access_key"],
        secret_key=MINIO_CONFIG["secret_key"],
        secure=MINIO_CONFIG["secure"]
    )

def get_image_url(kb_id, image_key):
    """获取图片的公共访问URL
    
    Args:
        kb_id: 知识库ID
        image_key: 图片在MinIO中的键
            
    Returns:
        图片的公共访问URL
    """
    try:
        minio_client = get_minio_client()
        
        # 检查桶和对象是否存在
        if not minio_client.bucket_exists(kb_id):
            print(f"[ERROR] 存储桶不存在: {kb_id}")
            return None
                
        try:
            minio_client.stat_object(kb_id, image_key)
        except Exception as e:
            print(f"[ERROR] 对象不存在: {kb_id}/{image_key}, 错误: {str(e)}")
            return None
                
        # 获取MinIO服务器配置
        minio_endpoint = MINIO_CONFIG["endpoint"]
        use_ssl = MINIO_CONFIG["secure"]
        
        # 构建URL
        protocol = "https" if use_ssl else "http"
        url = f"{protocol}://{minio_endpoint}/{kb_id}/{image_key}"
        
        return url
    except Exception as e:
        print(f"[ERROR] 获取图片URL失败: {str(e)}")
        return None

def list_bucket_images(kb_id, prefix="images/"):
    """列出知识库中的所有图片
    
    Args:
        kb_id: 知识库ID
        prefix: 图片前缀，默认为"images/"
            
    Returns:
        图片列表
    """
    try:
        minio_client = get_minio_client()
        
        # 检查桶是否存在
        if not minio_client.bucket_exists(kb_id):
            print(f"[ERROR] 存储桶不存在: {kb_id}")
            return []
        
        # 列出桶中的所有对象
        objects = minio_client.list_objects(kb_id, prefix=prefix, recursive=True)
        image_list = []
        
        for obj in objects:
            image_list.append(obj.object_name)
        
        return image_list
    except Exception as e:
        print(f"[ERROR] 列出图片失败: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(description="查询MinIO中图片的外链")
    parser.add_argument("--kb_id", help="知识库ID", required=False)
    parser.add_argument("--image_key", help="图片在MinIO中的键", required=False)
    parser.add_argument("--list", action="store_true", help="列出知识库中的所有图片")
    parser.add_argument("--list_buckets", action="store_true", help="列出所有存储桶")
    
    args = parser.parse_args()
    
    # 列出所有存储桶
    if args.list_buckets:
        try:
            minio_client = get_minio_client()
            buckets = minio_client.list_buckets()
            print("可用的存储桶列表:")
            for bucket in buckets:
                print(f"  - {bucket.name}")
            return
        except Exception as e:
            print(f"[ERROR] 列出存储桶失败: {str(e)}")
            return
    
    # 检查必要参数
    if not args.kb_id:
        print("[ERROR] 请提供知识库ID (--kb_id)")
        parser.print_help()
        return
    
    # 列出知识库中的所有图片
    if args.list:
        images = list_bucket_images(args.kb_id)
        if images:
            print(f"知识库 {args.kb_id} 中的图片列表:")
            for i, image in enumerate(images, 1):
                url = get_image_url(args.kb_id, image)
                print(f"  {i}. {image}")
                print(f"     URL: {url}")
        else:
            print(f"知识库 {args.kb_id} 中没有图片")
        return
    
    # 获取单个图片的URL
    if not args.image_key:
        print("[ERROR] 请提供图片键 (--image_key) 或使用 --list 列出所有图片")
        parser.print_help()
        return
    
    url = get_image_url(args.kb_id, args.image_key)
    if url:
        print(f"图片 {args.kb_id}/{args.image_key} 的URL:")
        print(url)
    else:
        print(f"无法获取图片 {args.kb_id}/{args.image_key} 的URL")

if __name__ == "__main__":
    main()