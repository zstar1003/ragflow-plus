export interface CreateOrUpdateTableRequestData {
  id?: number
  username: string
  chatModel?: string
  embeddingModel?: string
}

export interface TableRequestData {
  /** 当前页码 */
  currentPage: number
  /** 查询条数 */
  size: number
  /** 查询参数：用户名 */
  username?: string
}

export interface TableData {
  id: number
  username: string
  chatModel: string
  embeddingModel: string
  createTime: string
  updateTime: string
}

export type TableResponseData = ApiResponseData<{
  list: TableData[]
  total: number
}>
