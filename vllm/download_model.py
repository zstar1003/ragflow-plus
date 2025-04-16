import os
from huggingface_hub import snapshot_download

# 1. 设置镜像源（国内加速）
# os.environ["HF_ENDPOINT"] = "https://mirrors.tuna.tsinghua.edu.cn/hugging-face/"

# 2. 定义模型列表（名称 + 下载路径）
models_to_download = [
    {
        "repo_id": "BAAI/bge-m3",  # Embedding 模型
        "local_dir": os.path.expanduser("./models/bge-m3"),
    },
    {
        "repo_id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",  # LLM 模型
        "local_dir": os.path.expanduser("./models/DeepSeek-R1-1.5B"),
    }
]

# 3. 遍历下载所有模型
for model in models_to_download:
    while True:  # 断点续传重试机制
        try:
            print(f"开始下载模型: {model['repo_id']} 到目录: {model['local_dir']}")
            snapshot_download(
                repo_id=model["repo_id"],
                local_dir=model["local_dir"],
                resume_download=True,  # 启用断点续传
                force_download=False,  # 避免重复下载已有文件
                token=None,            # 如需访问私有模型，替换为你的 token
            )
            print(f"模型 {model['repo_id']} 下载完成！")
            break
        except Exception as e:
            print(f"下载失败: {e}, 重试中...")