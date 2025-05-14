import { request } from "@/http/axios"

interface UploadResponse {
  code: number
  message?: string
  data: any
}

// 获取文档列表
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

// 获取文档详情
export function getDocumentDetailApi(id: string) {
  return request({
    url: `/api/v1/documents/${id}`,
    method: "get"
  })
}

// 获取文档解析进度
export function getDocumentParseProgress(docId: any) {
  return request({
    url: `/api/v1/knowledgebases/documents/${docId}/parse/progress`,
    method: "get"
  })
}

// 开始解析文档
export function startDocumentParse(docId: any) {
  return request({
    url: `/api/v1/knowledgebases/documents/${docId}/parse`,
    method: "post"
  })
}

// 上传文档
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
      throw new Error(response.message || "上传失败")
    }
    return response.data
  })
}

// 删除文档
export function deleteDocumentApi(docId: string) {
  return request({
    url: `/api/v1/knowledgebases/documents/${docId}`,
    method: "delete"
  })
}

// 批量删除文档
export function batchDeleteDocumentsApi(ids: string[]) {
  return request({
    url: "/api/v1/knowledgebases/documents/batch",
    method: "delete",
    data: { ids }
  })
}

// 更改文档状态（启用/禁用）
export function changeDocumentStatusApi(id: string, status: string) {
  return request({
    url: `/api/v1/knowledgebases/documents/${id}/status`,
    method: "put",
    data: { status }
  })
}

// 运行文档解析
export function runDocumentParseApi(id: string) {
  return request({
    url: `/api/v1/knowledgebases/documents/${id}/parse`,
    method: "post"
  })
}

// 获取文档分块列表
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

// 获取文件列表
/**
 * 获取文件列表的 API 请求函数
 * @param params 请求参数对象
 * @param params.currentPage 当前页码
 * @param params.size 每页数量
 * @param params.name 可选的文件名称过滤
 * @param params.sort_by 排序字段
 * @param params.sort_order 排序方式（升序/降序）
 * @returns Promise 返回文件列表请求的响应
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

// 添加文档到知识库
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
    throw new Error(response.message || "添加文档失败")
  })
}

// --- 新增：顺序批量解析 API ---

/** 启动知识库顺序批量文档解析 */
export function startSequentialBatchParseAsyncApi(kbId: string) {
  // 定义预期的成功响应结构类型
  interface StartBatchResponse {
    code: number
    message?: string
    data?: {
      message: string
    }
  }
  return request<StartBatchResponse>({
    url: `/api/v1/knowledgebases/${kbId}/batch_parse_sequential/start`, // 指向新的启动路由
    method: "post"
  })
}

/** 获取知识库顺序批量解析进度 */
export interface SequentialBatchTaskProgress {
  status: "starting" | "running" | "completed" | "failed" | "not_found" | "cancelling" | "cancelled" // 可能的状态
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
    url: `/api/v1/knowledgebases/${kbId}/batch_parse_sequential/progress`, // 指向新的进度路由
    method: "get"
  })
}
