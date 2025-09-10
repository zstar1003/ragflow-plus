# RagFlow-Plus에 사용되는 언어 모델(chat,emb,rerank,vlm,img2txt) docker compose deployment 소개 및 유의사항

**vllm 기반 Reranker 우선 작성**

## 개요

RagFlow-Plus에서 사용되는 언어 모델들(chat, embedding, rerank, vlm, img2txt)의 Docker Compose 기반 배포 방법을 소개합니다.
**vLLM 기반 Reranker** 우선으로 작성되었습니다(추후 추가 예정)

## 하드웨어 환경

- **GPU**: Nvidia L40S × 1개
- **CUDA**: 12.4 버전
- **배포 방식**: Docker Compose (Docker Swarm 미사용)

## 1. vLLM 기반 Reranker 배포

### 1.1 지원 모델 확인

vLLM에서 지원하는 Rerank 모델 목록을 확인합니다:
- 공식 문서: https://docs.vllm.ai/en/latest/models/supported_models.html#classification

### 1.2 Docker Compose 설정

`ragflow-plus/docker/llm_deployment/vllm/docker-compose.yml` 파일에서 모델 경로를 설정하고 컨테이너 기반 모델 서빙을 구성합니다.

### 1.3 웹 환경에서 모델 설정

RagFlow-Plus 웹 인터페이스에서 다음과 같이 설정합니다:

1. **모델 추가 경로**: `http://${RAGFLOW_PATH}/user-setting/model` > `Models_to_be_added`
2. **설정 값**:
   - **Model Type**: `rerank`
   - **Model Name**: Docker Compose에 설정된 모델 경로 또는 HuggingFace 모델명
   - **Base URL**: `http://${RAGFLOW_PATH}/v1` 
3. **사용 방법**: Chat > Create Assistant > Prompt Setting > Rerank Model 선택

## 2. 오류 해결 가이드

### 2.1 "Model ${모델이름}___VLLM@VLLM is not authorized" 오류

이 오류는 모델명 불일치로 인해 발생합니다. 다음 단계로 해결할 수 있습니다:

#### Step 1: Tenant ID 확인

모델 관련 정보는 `ragflowplus-mysql` 컨테이너의 `tenant_llm` 테이블에 저장됩니다.

```bash
docker exec -it ragflow-mysql mysql -u root -pinfini_rag_flow rag_flow -e \
"SELECT * FROM tenant_llm WHERE model_type LIKE '%rerank%' AND status='1';"
```

#### Step 2: 실제 서빙 모델명 확인

vLLM에서 실제로 서빙되고 있는 모델명을 확인합니다:

```bash
curl -X GET "http://localhost:8001/v1/models" | jq -r '.data[0].id'
```

#### Step 3: 모델명 업데이트

데이터베이스의 모델명을 실제 서빙 모델명과 일치시킵니다:

```bash
docker exec -it ragflow-mysql mysql -u root -pinfini_rag_flow rag_flow -e \
"UPDATE tenant_llm SET llm_name='${MODEL_NAME}' WHERE tenant_id='${TENANT_ID}' AND model_type='rerank' AND llm_factory='VLLM';"
```

#### Step 4: 서비스 재시작

변경사항 적용을 위해 관련 서비스를 재시작합니다:

