/**
 * 파일 데이터 타입
 */
export interface FileData {
  /** 파일 ID */
  id: string
  /** 파일명 */
  name: string
  /** 파일 크기(바이트) */
  size: number
  /** 파일 타입 */
  type: string
  /** 지식베이스 ID */
  kb_id: string
  /** 저장 위치 */
  location: string
  /** 생성 시간 */
  create_time?: number
  /** 업데이트 시간 */
  update_time?: number
  /** 생성 날짜 */
  create_date?: string
}

/**
 * 파일 목록 결과
 */
export interface FileListResult {
  /** 파일 목록 */
  list: FileData[]
  /** 총 개수 */
  total: number
}

/**
 * 페이지 조회 매개변수
 */
export interface PageQuery {
  /** 현재 페이지 번호 */
  currentPage: number
  /** 페이지당 항목 수 */
  size: number
  /** 정렬 필드 */
  sort_by: string
  /** 정렬 방식 */
  sort_order: string
}

/**
 * 페이지 결과
 */
export interface PageResult<T> {
  /** 데이터 목록 */
  list: T[]
  /** 총 개수 */
  total: number
}

/**
 * 공통 응답 구조
 */
export interface ApiResponse<T> {
  /** 상태 코드 */
  code: number
  /** 응답 데이터 */
  data: T
  /** 응답 메시지 */
  message: string
}
