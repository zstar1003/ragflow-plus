import { request } from "@/http/axios"

// 데이터베이스 인터페이스에 표시되는 정보 수정 정의
interface KbDetailData {
  id: string
  name: string
  permission: string
  avatar?: string
}

interface ApiDetailResponse {
  data: KbDetailData
  code: number
  message: string
}

// 지식베이스 목록 가져오기
export function getKnowledgeBaseListApi(params: {
  currentPage: number
  size: number
  name?: string
  sort_by: string
  sort_order: string
}) {
  return request({
    url: "/api/v1/knowledgebases",
    method: "get",
    params
  })
}

// 지식베이스 상세정보 가져오기
export function getKbDetailApi(id: string): Promise<ApiDetailResponse> {
  return request({
    url: `/api/v1/knowledgebases/${id}`,
    method: "get"
  })
}

// 지식베이스 생성
export function createKnowledgeBaseApi(data: {
  name: string
  description?: string
  language?: string
  permission?: string
  creator_id: string
  embd_id?: string
}) {
  return request({
    url: "/api/v1/knowledgebases",
    method: "post",
    data
  })
}

// 지식베이스 업데이트
export function updateKnowledgeBaseApi(id: string, data: {
  name?: string
  description?: string
  language?: string
  permission?: string
  avatar?: string
  embd_id?: string
}) {
  return request({
    url: `/api/v1/knowledgebases/${id}`,
    method: "put",
    data
  })
}

// 지식베이스 삭제
export function deleteKnowledgeBaseApi(id: string) {
  return request({
    url: `/api/v1/knowledgebases/${id}`,
    method: "delete"
  })
}

// 지식베이스 일괄 삭제
export function batchDeleteKnowledgeBaseApi(ids: string[]) {
  return request({
    url: "/api/v1/knowledgebases/batch",
    method: "delete",
    data: { ids }
  })
}

// 지식베이스에 문서 추가
export function addDocumentToKnowledgeBaseApi(data: {
  kb_id: string
  file_ids: string[]
}) {
  return request({
    url: `/api/v1/knowledgebases/${data.kb_id}/documents`,
    method: "post",
    data: { file_ids: data.file_ids }
  })
}

 // 지식베이스 Embedding 설정 가져오기
export function getKnowledgeBaseEmbeddingConfigApi(params:{kb_id: string}) {
  return request({
    url: "/api/v1/knowledgebases/embedding_config", // API 경로 접두사가 올바른지 확인
    method: "get",
    params
  })
}

// 시스템 Embedding 설정 가져오기
export function getSystemEmbeddingConfigApi(params?: { t?: number }) {
  return request({
    url: "/api/v1/knowledgebases/system_embedding_config",
    method: "get",
    params
  })
}

// 시스템 Embedding 설정 지정
export function setSystemEmbeddingConfigApi(data: {
  llm_name: string
  api_base: string
  api_key?: string
}) {
  return request({
    url: "/api/v1/knowledgebases/system_embedding_config", // API 경로 접두사가 올바른지 확인
    method: "post",
    data
  })
}

// 지식베이스 ID로 테넌트의 Embedding 모델 목록 가져오기
export function loadingEmbeddingModelsApi(params:{kb_id: string}) {
  return request({
    url: `/api/v1/knowledgebases/embedding_models/${params.kb_id}`,
    method: "get",
  })
}