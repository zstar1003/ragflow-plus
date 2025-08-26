import requests
import time

# Ollama 설정
OLLAMA_HOST = "http://localhost:11434"  # 기본 Ollama 주소
MODEL_NAME = "bge-m3"  # 사용할 임베딩 모델
TEXT_TO_EMBED = "테스트 텍스트"

# 인터페이스 URL 및 해당 요청 본문 구조 정의
ENDPOINTS = {
    "api/embeddings": {
        "url": f"{OLLAMA_HOST}/api/embeddings",  # 네이티브 API 경로
        "payload": {"model": MODEL_NAME, "prompt": TEXT_TO_EMBED},  # 네이티브 API는 prompt 필드 사용
    },
    "v1/embeddings": {
        "url": f"{OLLAMA_HOST}/v1/embeddings",  # OpenAI 호환 API 경로
        "payload": {"model": MODEL_NAME, "input": TEXT_TO_EMBED},  # OpenAI 호환 API는 input 필드 사용
    },
}

headers = {"Content-Type": "application/json"}


def test_endpoint(endpoint_name, endpoint_info):
    """단일 엔드포인트를 테스트하고 결과 반환"""
    print(f"\n인터페이스 테스트: {endpoint_name}")
    url = endpoint_info["url"]
    payload = endpoint_info["payload"]

    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload)
        response_time = time.time() - start_time

        print(f"상태 코드: {response.status_code}")
        print(f"응답 시간: {response_time:.3f}초")

        try:
            data = response.json()

            # 서로 다른 인터페이스의 응답 구조 차이 처리
            embedding = None
            if endpoint_name == "api/embeddings":
                embedding = data.get("embedding")  # 네이티브 API는 embedding 필드 반환
            elif endpoint_name == "v1/embeddings":
                embedding = data.get("data", [{}])[0].get("embedding")  # OpenAI 호환 API는 data 배열 내 embedding 반환

            if embedding:
                print(f"임베딩 벡터 길이: {len(embedding)}")
                return {
                    "endpoint": endpoint_name,
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "embedding_length": len(embedding),
                    "embedding": embedding[:5],
                }
            else:
                print("응답에서 'embedding' 필드를 찾을 수 없습니다")
                return {"endpoint": endpoint_name, "status_code": response.status_code, "error": "No embedding field in response"}

        except ValueError:
            print("응답이 유효한 JSON 형식이 아닙니다")
            return {"endpoint": endpoint_name, "status_code": response.status_code, "error": "Invalid JSON response"}

    except Exception as e:
        print(f"요청 실패: {str(e)}")
        return {"endpoint": endpoint_name, "error": str(e)}


def compare_endpoints():
    """두 엔드포인트의 성능 비교"""
    results = []

    print("=" * 50)
    print(f"Ollama의 embeddings 인터페이스 비교 시작, 사용 모델: {MODEL_NAME}")
    print("=" * 50)

    for endpoint_name, endpoint_info in ENDPOINTS.items():
        results.append(test_endpoint(endpoint_name, endpoint_info))

    print("\n" + "=" * 50)
    print("비교 결과 요약:")
    print("=" * 50)

    successful_results = [res for res in results if "embedding_length" in res]

    if len(successful_results) == 2:
        if successful_results[0]["embedding_length"] == successful_results[1]["embedding_length"]:
            print(f"두 인터페이스가 반환한 embedding 차원이 동일합니다: {successful_results[0]['embedding_length']}")
        else:
            print("두 인터페이스가 반환한 embedding 차원이 다릅니다:")
            for result in successful_results:
                print(f"- {result['endpoint']}: {result['embedding_length']}")

        print("\nEmbedding 처음 5개 요소 예시:")
        for result in successful_results:
            print(f"- {result['endpoint']}: {result['embedding']}")

        faster = min(successful_results, key=lambda x: x["response_time"])
        slower = max(successful_results, key=lambda x: x["response_time"])
        print(f"\n더 빠른 인터페이스: {faster['endpoint']} ({faster['response_time']:.3f}초 vs {slower['response_time']:.3f}초)")
    else:
        print("최소 하나의 인터페이스가 유효한 embedding 데이터를 반환하지 않았습니다")
        for result in results:
            if "error" in result:
                print(f"- {result['endpoint']} 오류: {result['error']}")


if __name__ == "__main__":
    compare_endpoints()
