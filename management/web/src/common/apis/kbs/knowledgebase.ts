import { request } from "@/http/axios"

// 定义修改数据库界面中显示的信息
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
export function getKbDetailApi(id: string): Promise<ApiDetailResponse> {
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
  embd_id?: string
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
  avatar?: string
  embd_id?: string
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

 // 获取知识库 Embedding 配置
export function getKnowledgeBaseEmbeddingConfigApi(params:{kb_id: string}) {
  return request({
    url: "/api/v1/knowledgebases/embedding_config", // 确认 API 路径前缀是否正确
    method: "get",
    params
  })
}

// 获取系统 Embedding 配置
export function getSystemEmbeddingConfigApi(params?: { t?: number }) {
  return request({
    url: "/api/v1/knowledgebases/system_embedding_config",
    method: "get",
    params
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

// 根据知识库id获取租户的 Embedding 模型列表
export function loadingEmbeddingModelsApi(params:{kb_id: string}) {
  return request({
    url: `/api/v1/knowledgebases/embedding_models/${params.kb_id}`,
    method: "get",
  })
}