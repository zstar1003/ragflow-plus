import numpy as np
from abc import ABC
from ollama import Client


class Base(ABC):
    def __init__(self, key, model_name):
        pass

    def encode(self, texts: list):
        raise NotImplementedError("Please implement encode method!")

    def encode_queries(self, text: str):
        raise NotImplementedError("Please implement encode method!")

    def total_token_count(self, resp):
        try:
            return resp.usage.total_tokens
        except Exception:
            pass
        try:
            return resp["usage"]["total_tokens"]
        except Exception:
            pass
        return 0


class OllamaEmbed(Base):
    def __init__(self, model_name, **kwargs):
        self.client = Client(host="http://localhost:11434", **kwargs)
        self.model_name = model_name

    def encode(self, texts: list):
        arr = []
        tks_num = 0
        for txt in texts:
            res = self.client.embeddings(prompt=txt, model=self.model_name)
            arr.append(res["embedding"])
            tks_num += 128
        return np.array(arr), tks_num


if __name__ == "__main__":
    # 初始化嵌入模型
    embedder = OllamaEmbed(model_name="bge-m3")

    # 测试文本
    test_texts = ["测试文本"]

    # 获取嵌入向量和token计数
    embeddings, total_tokens = embedder.encode(test_texts)

    # 打印结果
    print(f"Total tokens used: {total_tokens}")
    print("\nEmbedding vectors:")
    for i, (text, embedding) in enumerate(zip(test_texts, embeddings)):
        print(f"\nText {i + 1}: '{text}'")
        print(f"Embedding shape: {embedding.shape}")
        print(f"First 5 values: {embedding[:5]}")
        print(f"Embedding dtype: {embedding.dtype}")

    # 打印完整的第一个embedding向量
    print("\nComplete first embedding vector:")
    print(embeddings[0])
