import type { RouteRecordRaw } from "vue-router"
import { routerConfig } from "@/router/config"
import { registerNavigationGuard } from "@/router/guard"
import { createRouter } from "vue-router"
import { flatMultiLevelRoutes } from "./helper"

const Layouts = () => import("@/layouts/index.vue")

/**
 * @name 상주 라우트
 * @description redirect/403/404/login 등 숨겨진 페이지를 제외하고, 다른 페이지는 고유한 Name 속성을 설정하는 것을 권장
 */
export const constantRoutes: RouteRecordRaw[] = [
  {
    path: "/redirect",
    component: Layouts,
    meta: {
      hidden: true
    },
    children: [
      {
        path: ":path(.*)",
        component: () => import("@/pages/redirect/index.vue")
      }
    ]
  },
  {
    path: "/403",
    component: () => import("@/pages/error/403.vue"),
    meta: {
      hidden: true
    }
  },
  {
    path: "/404",
    component: () => import("@/pages/error/404.vue"),
    meta: {
      hidden: true
    },
    alias: "/:pathMatch(.*)*"
  },
  {
    path: "/login",
    component: () => import("@/pages/login/index.vue"),
    meta: {
      hidden: true
    }
  },
  {
    path: "/",
    component: Layouts,
    redirect: "/dashboard",
    children: [
      {
        path: "dashboard",
        component: () => import("@/pages/user-management/index.vue"),
        name: "UserManagement",
        meta: {
          title: "사용자 관리",
          svgIcon: "user-management",
          affix: true
        }
      }
    ]
  },
  {
    path: "/team",
    component: Layouts,
    redirect: "/team/index",
    children: [
      {
        path: "index",
        component: () => import("@/pages/team-management/index.vue"),
        name: "Team",
        meta: {
          title: "팀 관리",
          svgIcon: "team-management",
          affix: false,
          keepAlive: true
        }
      }
    ]
  },
  {
    path: "/config",
    component: Layouts,
    redirect: "/config/index",
    children: [
      {
        path: "index",
        component: () => import("@/pages/user-config/index.vue"),
        name: "UserConfig",
        meta: {
          title: "사용자 설정",
          svgIcon: "user-config",
          affix: false,
          keepAlive: true
        }
      }
    ]
  },
  {
    path: "/file",
    component: Layouts,
    redirect: "/file/index",
    children: [
      {
        path: "index",
        component: () => import("@/pages/file/index.vue"),
        name: "File",
        meta: {
          title: "파일 관리",
          svgIcon: "file",
          affix: false,
          keepAlive: true
        }
      }
    ]
  },
  {
    path: "/knowledgebase",
    component: Layouts,
    redirect: "/knowledgebase/index",
    children: [
      {
        path: "index",
        component: () => import("@/pages/knowledgebase/index.vue"),
        name: "KnowledgeBase",
        meta: {
          title: "지식베이스 관리",
          svgIcon: "kb",
          affix: false,
          keepAlive: true
        }
      }
    ]
  },
  {
    path: "/conversation",
    component: Layouts,
    redirect: "/conversation/index",
    children: [
      {
        path: "index",
        component: () => import("@/pages/conversation/index.vue"),
        name: "conversation",
        meta: {
          title: "사용자 대화 관리",
          svgIcon: "conversation",
          affix: false,
          keepAlive: true
        }
      }
    ]
  }
]

/**
 * @name 동적 라우트
 * @description 권한 (Roles 속성)이 있는 라우트를 배치하는 곳
 * @description 고유한 Name 속성을 가져야 함
 */
export const dynamicRoutes: RouteRecordRaw[] = [
  // {
  //   path: "/permission",
  //   component: Layouts,
  //   redirect: "/permission/page-level",
  //   name: "Permission",
  //   meta: {
  //     title: "권한 데모",
  //     elIcon: "Lock",
  //     // 루트 라우트에서 역할 설정 가능
  //     roles: ["admin", "editor"],
  //     alwaysShow: true
  //   },
  //   children: [
  //     {
  //       path: "page-level",
  //       component: () => import("@/pages/demo/permission/page-level.vue"),
  //       name: "PermissionPageLevel",
  //       meta: {
  //         title: "페이지 레벨",
  //         // 또는 자식 라우트에서 역할 설정
  //         roles: ["admin"]
  //       }
  //     },
  //     {
  //       path: "button-level",
  //       component: () => import("@/pages/demo/permission/button-level.vue"),
  //       name: "PermissionButtonLevel",
  //       meta: {
  //         title: "버튼 레벨",
  //         // 역할이 설정되지 않으면: 해당 페이지는 권한이 필요하지 않지만 루트 라우트의 역할을 상속받음
  //         roles: undefined
  //       }
  //     }
  //   ]
  // }
]

/** 라우터 인스턴스 */
export const router = createRouter({
  history: routerConfig.history,
  routes: routerConfig.thirdLevelRouteCache ? flatMultiLevelRoutes(constantRoutes) : constantRoutes
})

/** 라우터 재설정 */
export function resetRouter() {
  try {
    // 주의: 모든 동적 라우트는 Name 속성을 가져야 하며, 그렇지 않으면 완전히 재설정되지 않을 수 있음
    router.getRoutes().forEach((route) => {
      const { name, meta } = route
      if (name && meta.roles?.length) {
        router.hasRoute(name) && router.removeRoute(name)
      }
    })
  } catch {
    // 브라우저를 강제로 새로고침해도 되지만, 사용자 경험이 좋지 않음
    location.reload()
  }
}

// 라우터 내비게이션 가드 등록
registerNavigationGuard(router)
