import type { Router } from "vue-router"
import { usePermissionStore } from "@/pinia/stores/permission"
import { useUserStore } from "@/pinia/stores/user"
import { routerConfig } from "@/router/config"
import { isWhiteList } from "@/router/whitelist"
import { setRouteChange } from "@@/composables/useRouteListener"
import { useTitle } from "@@/composables/useTitle"
import { getToken } from "@@/utils/cache/cookies"
import NProgress from "nprogress"

NProgress.configure({ showSpinner: false })

const { setTitle } = useTitle()

const LOGIN_PATH = "/login"

export function registerNavigationGuard(router: Router) {
  // 전역 전처리 가드
  router.beforeEach(async (to, _from) => {
    NProgress.start()
    const userStore = useUserStore()
    const permissionStore = usePermissionStore()
    // 로그인하지 않은 경우
    if (!getToken()) {
      // 로그인 면제 화이트리스트에 있으면 직접 진입
      if (isWhiteList(to)) return true
      // 다른 접근 권한이 없는 페이지는 로그인 페이지로 리다이렉트
      return LOGIN_PATH
    }
    // 이미 로그인했고 Login 페이지에 진입하려는 경우, 홈페이지로 리다이렉트
    if (to.path === LOGIN_PATH) return "/"
    // 사용자가 이미 권한 역할을 가지고 있는 경우
    if (userStore.roles.length !== 0) return true
    // 그렇지 않으면 권한 역할을 다시 가져옴
    try {
      await userStore.getInfo()
      // 주의: 역할은 배열이어야 함! 예: ["admin"] 또는 ["developer", "editor"]
      const roles = userStore.roles
      // 접근 가능한 Routes 생성
      routerConfig.dynamic ? permissionStore.setRoutes(roles) : permissionStore.setAllRoutes()
      // "접근 권한이 있는 동적 라우트"를 Router에 추가
      permissionStore.addRoutes.forEach(route => router.addRoute(route))
      // replace: true로 설정하여 네비게이션이 히스토리 기록을 남기지 않음
      return { ...to, replace: true }
    } catch (error) {
      // 과정 중 오류가 발생하면 Token을 직접 초기화하고 로그인 페이지로 리다이렉트
      userStore.resetToken()
      ElMessage.error((error as Error).message || "라우트 가드에서 오류 발생")
      return LOGIN_PATH
    }
  })

  // 전역 후처리 훅
  router.afterEach((to) => {
    setRouteChange(to)
    setTitle(to.meta.title)
    NProgress.done()
  })
}
