import { request } from "@/http/axios"

// 获取知识库列表
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

// 获取知识库详情
export function getKnowledgeBaseDetailApi(id: string) {
  return request({
    url: `/api/v1/knowledgebases/${id}`,
    method: "get"
  })
}

// 创建知识库
export function createKnowledgeBaseApi(data: {
  name: string
  description?: string
  language?: string
  permission?: string
  creator_id: string
}) {
  return request({
    url: "/api/v1/knowledgebases",
    method: "post",
    data
  })
}

// 更新知识库
export function updateKnowledgeBaseApi(id: string, data: {
  name?: string
  description?: string
  language?: string
  permission?: string
}) {
  return request({
    url: `/api/v1/knowledgebases/${id}`,
    method: "put",
    data
  })
}

// 删除知识库
export function deleteKnowledgeBaseApi(id: string) {
  return request({
    url: `/api/v1/knowledgebases/${id}`,
    method: "delete"
  })
}

// 批量删除知识库
export function batchDeleteKnowledgeBaseApi(ids: string[]) {
  return request({
    url: "/api/v1/knowledgebases/batch",
    method: "delete",
    data: { ids }
  })
}

// 添加文档到知识库
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

// 获取系统 Embedding 配置
export function getSystemEmbeddingConfigApi() {
  return request({
    url: "/api/v1/knowledgebases/system_embedding_config", // 确认 API 路径前缀是否正确
    method: "get"
  })
}

// 设置系统 Embedding 配置
export function setSystemEmbeddingConfigApi(data: {
  llm_name: string
  api_base: string
  api_key?: string
}) {
  return request({
    url: "/api/v1/knowledgebases/system_embedding_config", // 确认 API 路径前缀是否正确
    method: "post",
    data
  })
}
