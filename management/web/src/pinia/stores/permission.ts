import type { RouteRecordRaw } from "vue-router"
import { pinia } from "@/pinia"
import { constantRoutes, dynamicRoutes } from "@/router"
import { routerConfig } from "@/router/config"
import { flatMultiLevelRoutes } from "@/router/helper"

function hasPermission(roles: string[], route: RouteRecordRaw) {
  const routeRoles = route.meta?.roles
  return routeRoles ? roles.some(role => routeRoles.includes(role)) : true
}

function filterDynamicRoutes(routes: RouteRecordRaw[], roles: string[]) {
  const res: RouteRecordRaw[] = []
  routes.forEach((route) => {
    const tempRoute = { ...route }
    if (hasPermission(roles, tempRoute)) {
      if (tempRoute.children) {
        tempRoute.children = filterDynamicRoutes(tempRoute.children, roles)
      }
      res.push(tempRoute)
    }
  })
  return res
}

export const usePermissionStore = defineStore("permission", () => {
  // 접근 가능한 라우트
  const routes = ref<RouteRecordRaw[]>([])

  // 접근 권한이 있는 동적 라우트
  const addRoutes = ref<RouteRecordRaw[]>([])

  // 역할에 따라 접근 가능한 Routes 생성 (접근 가능한 라우트 = 상주 라우트 + 접근 권한이 있는 동적 라우트)
  const setRoutes = (roles: string[]) => {
    const accessedRoutes = filterDynamicRoutes(dynamicRoutes, roles)
    set(accessedRoutes)
  }

  // 모든 라우트 = 모든 상주 라우트 + 모든 동적 라우트
  const setAllRoutes = () => {
    set(dynamicRoutes)
  }

  // 통합 설정
  const set = (accessedRoutes: RouteRecordRaw[]) => {
    routes.value = constantRoutes.concat(accessedRoutes)
    addRoutes.value = routerConfig.thirdLevelRouteCache ? flatMultiLevelRoutes(accessedRoutes) : accessedRoutes
  }

  return { routes, addRoutes, setRoutes, setAllRoutes }
})

/**
 * @description SPA 애플리케이션에서 pinia 인스턴스가 활성화되기 전에 store를 사용할 수 있습니다
 * @description SSR 애플리케이션에서 setup 외부에서 store를 사용할 수 있습니다
 */
export function usePermissionStoreOutside() {
  return usePermissionStore(pinia)
}
