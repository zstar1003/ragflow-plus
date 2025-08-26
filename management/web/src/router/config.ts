import type { RouterHistory } from "vue-router"
import { createWebHashHistory, createWebHistory } from "vue-router"

/** 라우터 설정 */
interface RouterConfig {
  /**
   * @name 라우터 모드
   * @description hash 모드와 html5 모드
   */
  history: RouterHistory
  /**
   * @name 동적 라우터 기능 활성화 여부
   * @description 1. 활성화 시 백엔드 협업이 필요하며, 사용자 정보 조회 API에서 동적 라우터 로딩을 위한 판별 필드 반환 필요 (이 프로젝트는 roles 필드 사용)
   * @description 2. 프로젝트에서 사용자별로 다른 페이지를 보여줄 필요가 없다면 dynamic: false로 설정
   */
  dynamic: boolean
  /**
   * @name 기본 역할
   * @description 동적 라우터 기능이 비활성화된 경우:
   * @description 1. 모든 라우터를 상주 라우터에 작성해야 함 (모든 로그인 사용자가 접근할 수 있는 페이지가 동일함을 의미)
   * @description 2. 시스템이 현재 로그인 사용자에게 기능이 없는 기본 역할을 자동으로 할당
   */
  defaultRoles: Array<string>
  /**
   * @name 3단계 이상 라우터 캐시 기능 활성화 여부
   * @description 1. 활성화 시 라우터 다운그레이드 진행 (3단계 이상 라우터를 2단계 라우터로 변환)
   * @description 2. 모두 2단계 라우터로 변환되므로, 2단계 이상 라우터의 내장 자식 라우터는 비활성화됨
   */
  thirdLevelRouteCache: boolean
}

const VITE_ROUTER_HISTORY = import.meta.env.VITE_ROUTER_HISTORY

const VITE_PUBLIC_PATH = import.meta.env.VITE_PUBLIC_PATH

export const routerConfig: RouterConfig = {
  history: VITE_ROUTER_HISTORY === "hash" ? createWebHashHistory(VITE_PUBLIC_PATH) : createWebHistory(VITE_PUBLIC_PATH),
  dynamic: true,
  defaultRoles: ["DEFAULT_ROLE"],
  thirdLevelRouteCache: false
}
