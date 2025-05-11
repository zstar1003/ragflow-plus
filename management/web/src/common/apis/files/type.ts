/**
 * 文件数据类型
 */
export interface FileData {
  /** 文件ID */
  id: string
  /** 文件名称 */
  name: string
  /** 文件大小(字节) */
  size: number
  /** 文件类型 */
  type: string
  /** 知识库ID */
  kb_id: string
  /** 存储位置 */
  location: string
  /** 创建时间 */
  create_time?: number
  /** 更新时间 */
  update_time?: number
  /** 创建日期 */
  create_date?: string
}

/**
 * 文件列表结果
 */
export interface FileListResult {
  /** 文件列表 */
  list: FileData[]
  /** 总条数 */
  total: number
}

/**
 * 分页查询参数
 */
export interface PageQuery {
  /** 当前页码 */
  currentPage: number
  /** 每页条数 */
  size: number
  /** 排序字段 */
  sort_by: string
  /** 排序方式 */
  sort_order: string
}

/**
 * 分页结果
 */
export interface PageResult<T> {
  /** 数据列表 */
  list: T[]
  /** 总条数 */
  total: number
}

/**
 * 通用响应结构
 */
export interface ApiResponse<T> {
  /** 状态码 */
  code: number
  /** 响应数据 */
  data: T
  /** 响应消息 */
  message: string
}
