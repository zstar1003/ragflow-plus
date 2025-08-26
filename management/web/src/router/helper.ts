import type { Router, RouteRecordNormalized, RouteRecordRaw } from "vue-router"
import { cloneDeep, omit } from "lodash-es"
import { createRouter } from "vue-router"
import { routerConfig } from "./config"

/** 라우트 다운그레이드 (3단계 이상의 라우트를 2단계 라우트로 변환) */
export function flatMultiLevelRoutes(routes: RouteRecordRaw[]) {
  const routesMirror = cloneDeep(routes)
  routesMirror.forEach((route) => {
    // 라우트가 3단계 이상이면 다운그레이드 처리
    isMultipleRoute(route) && promoteRouteLevel(route)
  })
  return routesMirror
}

/** 라우트 레벨이 2보다 큰지 판단 */
function isMultipleRoute(route: RouteRecordRaw) {
  const children = route.children
  // 자식 라우트 중 하나라도 children 길이가 0보다 크면 3단계 이상 라우트임
  if (children?.length) return children.some(child => child.children?.length)
  return false
}

/** 라우트 레벨 승격 (다차원 라우트를 2차원으로 변환) */
function promoteRouteLevel(route: RouteRecordRaw) {
  // 현재 전달된 route의 모든 라우트 정보를 가져오기 위해 router 인스턴스 생성
  let router: Router | null = createRouter({
    history: routerConfig.history,
    routes: [route]
  })
  const routes = router.getRoutes()
  // addToChildren 함수에서 위에서 가져온 라우트 정보를 사용하여 route의 children 업데이트
  addToChildren(routes, route.children || [], route)
  router = null
  // 2단계 라우트로 변환 후, 모든 자식 라우트의 children 제거
  route.children = route.children?.map(item => omit(item, "children") as RouteRecordRaw)
}

/** 주어진 자식 라우트를 지정된 라우트 모듈에 추가 */
function addToChildren(routes: RouteRecordNormalized[], children: RouteRecordRaw[], routeModule: RouteRecordRaw) {
  children.forEach((child) => {
    const route = routes.find(item => item.name === child.name)
    if (route) {
      // routeModule의 children 초기화
      routeModule.children = routeModule.children || []
      // routeModule의 children 속성에 해당 라우트가 포함되어 있지 않으면 추가
      if (!routeModule.children.includes(route)) {
        routeModule.children.push(route)
      }
      // 해당 자식 라우트에 자체 자식 라우트가 있으면, 재귀적으로 이 함수를 호출하여 추가
      if (child.children?.length) {
        addToChildren(routes, child.children, routeModule)
      }
    }
  })
}
