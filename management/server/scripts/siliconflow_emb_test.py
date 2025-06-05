# 用于测试siliconflow的embedding model连通性

import requests

url = "https://api.siliconflow.cn/v1/embeddings"
api_key = "你的API密钥"  # 替换为你的API密钥

payload = {"model": "BAAI/bge-m3", "input": "测试文本"}
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

response = requests.request("POST", url, json=payload, headers=headers)

print(response.text)

# print(response.text.data)

# embedding_resp = response
# embedding_data = embedding_resp.json()
# q_1024_vec = embedding_data["data"][0]["embedding"]

# print("q_1024_vec", q_1024_vec)
