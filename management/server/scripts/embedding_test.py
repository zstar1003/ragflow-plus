import requests
import time

# Ollama配置
OLLAMA_HOST = "http://localhost:11434"  # 默认Ollama地址
MODEL_NAME = "bge-m3"  # 使用的embedding模型
TEXT_TO_EMBED = "测试文本"

# 定义接口URL和对应的请求体结构
ENDPOINTS = {
    "api/embeddings": {
        "url": f"{OLLAMA_HOST}/api/embeddings",  # 原生API路径
        "payload": {"model": MODEL_NAME, "prompt": TEXT_TO_EMBED},  # 原生API用prompt字段
    },
    "v1/embeddings": {
        "url": f"{OLLAMA_HOST}/v1/embeddings",  # OpenAI兼容API路径
        "payload": {"model": MODEL_NAME, "input": TEXT_TO_EMBED},  # OpenAI兼容API用input字段
    },
}

headers = {"Content-Type": "application/json"}


def test_endpoint(endpoint_name, endpoint_info):
    """测试单个端点并返回结果"""
    print(f"\n测试接口: {endpoint_name}")
    url = endpoint_info["url"]
    payload = endpoint_info["payload"]

    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload)
        response_time = time.time() - start_time

        print(f"状态码: {response.status_code}")
        print(f"响应时间: {response_time:.3f}秒")

        try:
            data = response.json()

            # 处理不同接口的响应结构差异
            embedding = None
            if endpoint_name == "api/embeddings":
                embedding = data.get("embedding")  # 原生API返回embedding字段
            elif endpoint_name == "v1/embeddings":
                embedding = data.get("data", [{}])[0].get("embedding")  # OpenAI兼容API返回data数组中的embedding

            if embedding:
                print(f"Embedding向量长度: {len(embedding)}")
                return {
                    "endpoint": endpoint_name,
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "embedding_length": len(embedding),
                    "embedding": embedding[:5],
                }
            else:
                print("响应中未找到'embedding'字段")
                return {"endpoint": endpoint_name, "status_code": response.status_code, "error": "No embedding field in response"}

        except ValueError:
            print("响应不是有效的JSON格式")
            return {"endpoint": endpoint_name, "status_code": response.status_code, "error": "Invalid JSON response"}

    except Exception as e:
        print(f"请求失败: {str(e)}")
        return {"endpoint": endpoint_name, "error": str(e)}


def compare_endpoints():
    """比较两个端点的性能"""
    results = []

    print("=" * 50)
    print(f"开始比较Ollama的embeddings接口，使用模型: {MODEL_NAME}")
    print("=" * 50)

    for endpoint_name, endpoint_info in ENDPOINTS.items():
        results.append(test_endpoint(endpoint_name, endpoint_info))

    print("\n" + "=" * 50)
    print("比较结果摘要:")
    print("=" * 50)

    successful_results = [res for res in results if "embedding_length" in res]

    if len(successful_results) == 2:
        if successful_results[0]["embedding_length"] == successful_results[1]["embedding_length"]:
            print(f"两个接口返回的embedding维度相同: {successful_results[0]['embedding_length']}")
        else:
            print("两个接口返回的embedding维度不同:")
            for result in successful_results:
                print(f"- {result['endpoint']}: {result['embedding_length']}")

        print("\nEmbedding前5个元素示例:")
        for result in successful_results:
            print(f"- {result['endpoint']}: {result['embedding']}")

        faster = min(successful_results, key=lambda x: x["response_time"])
        slower = max(successful_results, key=lambda x: x["response_time"])
        print(f"\n更快的接口: {faster['endpoint']} ({faster['response_time']:.3f}秒 vs {slower['response_time']:.3f}秒)")
    else:
        print("至少有一个接口未返回有效的embedding数据")
        for result in results:
            if "error" in result:
                print(f"- {result['endpoint']} 错误: {result['error']}")


if __name__ == "__main__":
    compare_endpoints()
