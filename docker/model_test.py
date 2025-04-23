import requests
from openai import OpenAI

# 测试 embedding 模型 (vllm-bge)
def test_embedding(model, text):
    """测试嵌入模型"""
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="1")
    
    response = client.embeddings.create(
        model=model,  # 使用支持嵌入的模型
        input=text  # 需要嵌入的文本
    )
    
    # 打印嵌入响应内容
    # print(f"Embedding response: {response}")
    
    result = response.data[0].embedding

    if response and response.data:
        print(len(result))
    else:
        print("Failed to get embedding.")

# 测试文本生成模型 (vllm-deepseek)
def test_chat(model, prompt):
    """测试文本生成模型"""
    client = OpenAI(base_url="http://localhost:8001/v1", api_key="1")
    
    response = client.completions.create(
        model=model,
        prompt=prompt
    )
    
    # 打印生成的文本
    print(f"Chat response: {response.choices[0].text}")

def main():
    # 测试文本生成模型 deepseek-r1
    prompt = "你好，今天的天气怎么样？"
    print("Testing vllm-deepseek model for chat...")
    test_chat("deepseek-r1", prompt)
    
    # 测试嵌入模型 bge-m3
    embedding_text = "我喜欢编程，尤其是做AI模型。"
    print("\nTesting vllm-bge model for embedding...")
    test_embedding("bge-m3", embedding_text)

if __name__ == "__main__":
    main()
