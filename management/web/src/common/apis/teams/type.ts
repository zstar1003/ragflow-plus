export interface CreateOrUpdateTableRequestData {
  id?: number
  username: string
  email?: string
  password?: string
}

export interface TableRequestData {
  /** 현재 페이지 번호 */
  currentPage: number
  /** 조회 개수 */
  size: number
  /** 조회 조건: 사용자명 */
  username?: string
  /** 조회 조건: 이메일 */
  email?: string
  /** 조회 조건: 팀명 */
  name?: string
  /** 정렬 필드 */
  sort_by: string
  /** 정렬 방식 */
  sort_order: string
}

export interface TableData {
  id: number
  username: string
  email: string
  createTime: string
  updateTime: string
}

export type TableResponseData = ApiResponseData<{
  list: TableData[]
  total: number
}>
