import { request } from "@/http/axios"

interface UploadResponse {
  code: number
  message?: string
  data: any
}

// 문서 목록 가져오기
export function getDocumentListApi(params: {
  kb_id: string
  currentPage: number
  size: number
  name?: string
  sort_by: string
  sort_order: string
}) {
  return request({
    url: `/api/v1/knowledgebases/${params.kb_id}/documents`,
    method: "get",
    params: {
      currentPage: params.currentPage,
      size: params.size,
      name: params.name,
      sort_by: params.sort_by,
      sort_order: params.sort_order
    }
  })
}

// 문서 상세정보 가져오기
export function getDocumentDetailApi(id: string) {
  return request({
    url: `/api/v1/documents/${id}`,
    method: "get"
  })
}

// 문서 파싱 진행률 가져오기
export function getDocumentParseProgress(docId: any) {
  return request({
    url: `/api/v1/knowledgebases/documents/${docId}/parse/progress`,
    method: "get"
  })
}

// 문서 파싱 시작
export function startDocumentParse(docId: any) {
  return request({
    url: `/api/v1/knowledgebases/documents/${docId}/parse`,
    method: "post"
  })
}

// 문서 업로드
export function uploadDocumentApi(formData: FormData): Promise<any> {
  return request<UploadResponse>({
    url: "/api/v1/knowledgebases/documents/upload",
    method: "post",
    data: formData,
    headers: {
      "Content-Type": "multipart/form-data"
    }
  }).then((response) => {
    if (response.code !== 0) {
      throw new Error(response.message || "업로드 실패")
    }
    return response.data
  })
}

// 문서 삭제
export function deleteDocumentApi(docId: string) {
  return request({
    url: `/api/v1/knowledgebases/documents/${docId}`,
    method: "delete"
  })
}

// 문서 일괄 삭제
export function batchDeleteDocumentsApi(ids: string[]) {
  return request({
    url: "/api/v1/knowledgebases/documents/batch",
    method: "delete",
    data: { ids }
  })
}

// 문서 상태 변경 (활성화/비활성화)
export function changeDocumentStatusApi(id: string, status: string) {
  return request({
    url: `/api/v1/knowledgebases/documents/${id}/status`,
    method: "put",
    data: { status }
  })
}

// 문서 파싱 실행
export function runDocumentParseApi(id: string) {
  return request({
    url: `/api/v1/knowledgebases/documents/${id}/parse`,
    method: "post",
    timeout: 60000000 // 문서 파싱 타임아웃 시간
  })
}

// 문서 청크 목록 가져오기
export function getDocumentChunksApi(params: {
  doc_id: string
  currentPage: number
  size: number
  content?: string
}) {
  return request({
    url: "/api/v1/chunks",
    method: "get",
    params
  })
}

// 파일 목록 가져오기
/**
 * 파일 목록을 가져오는 API 요청 함수
 * @param params 요청 매개변수 객체
 * @param params.currentPage 현재 페이지 번호
 * @param params.size 페이지당 항목 수
 * @param params.name 선택적 파일명 필터
 * @param params.sort_by 정렬 필드
 * @param params.sort_order 정렬 방식 (오름차순/내림차순)
 * @returns Promise 파일 목록 요청의 응답을 반환
 */
export function getFileListApi(params: {
  currentPage: number
  size: number
  name?: string
  sort_by: string
  sort_order: string
}) {
  return request({
    url: "/api/v1/files",
    method: "get",
    params
  })
}

// 지식베이스에 문서 추가
export function addDocumentToKnowledgeBaseApi(data: {
  kb_id: string
  file_ids: string[]
}) {
  return request<{ code: number, message?: string, data?: any }>({
    url: `/api/v1/knowledgebases/${data.kb_id}/documents`,
    method: "post",
    data: { file_ids: data.file_ids }
  }).then((response) => {
    if (response.code === 0 || response.code === 201) {
      return response.data || { added_count: data.file_ids.length }
    }
    throw new Error(response.message || "문서 추가 실패")
  })
}

// --- 새로 추가: 순차 배치 파싱 API ---

/** 지식베이스 순차 배치 문서 파싱 시작 */
export function startSequentialBatchParseAsyncApi(kbId: string) {
  // 예상되는 성공 응답 구조 타입 정의
  interface StartBatchResponse {
    code: number
    message?: string
    data?: {
      message: string
    }
  }
  return request<StartBatchResponse>({
    url: `/api/v1/knowledgebases/${kbId}/batch_parse_sequential/start`, // 새로운 시작 라우트를 가리킴
    method: "post"
  })
}

/** 지식베이스 순차 배치 파싱 진행률 가져오기 */
export interface SequentialBatchTaskProgress {
  status: "starting" | "running" | "completed" | "failed" | "not_found" | "cancelling" | "cancelled" // 가능한 상태
  total: number
  current: number
  message: string
  start_time?: number
}

export interface BatchProgressResponse {
  code: number
  message?: string
  data?: SequentialBatchTaskProgress
}

export function getSequentialBatchParseProgressApi(kbId: string) {
  return request<BatchProgressResponse>({
    url: `/api/v1/knowledgebases/${kbId}/batch_parse_sequential/progress`, // 새로운 진행률 라우트를 가리킴
    method: "get"
  })
}
