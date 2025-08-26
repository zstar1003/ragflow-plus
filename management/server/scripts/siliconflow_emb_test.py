# siliconflow의 embedding model 연결성 테스트용

import requests

url = "https://api.siliconflow.cn/v1/embeddings"
api_key = "귀하의 API 키"  # 귀하의 API 키로 교체

payload = {"model": "BAAI/bge-m3", "input": "테스트 텍스트"}
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

response = requests.request("POST", url, json=payload, headers=headers)

print(response.text)

# print(response.text.data)

# embedding_resp = response
# embedding_data = embedding_resp.json()
# q_1024_vec = embedding_data["data"][0]["embedding"]

# print("q_1024_vec", q_1024_vec)
