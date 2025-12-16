import type { RouteRecordRaw } from "vue-router"
import { routerConfig } from "@/router/config"
import { registerNavigationGuard } from "@/router/guard"
import { createRouter } from "vue-router"
import { flatMultiLevelRoutes } from "./helper"

const Layouts = () => import("@/layouts/index.vue")

/**
 * @name 常驻路由
 * @description 除了 redirect/403/404/login 等隐藏页面，其他页面建议设置唯一的 Name 属性
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
  }
]

/**
 * @name 动态路由
 * @description 用来放置有权限 (Roles 属性) 的路由
 * @description 必须带有唯一的 Name 属性
 */
export const dynamicRoutes: RouteRecordRaw[] = [
  {
    path: "/",
    component: Layouts,
    redirect: "/file",
    name: "Root",
    meta: {
      roles: ["admin", "team_owner"]
    },
    children: []
  },
  {
    path: "/dashboard",
    component: Layouts,
    redirect: "/dashboard/index",
    name: "Dashboard",
    meta: {
      roles: ["admin"]
    },
    children: [
      {
        path: "index",
        component: () => import("@/pages/user-management/index.vue"),
        name: "UserManagement",
        meta: {
          title: "用户管理",
          svgIcon: "user-management",
          affix: true,
          roles: ["admin"]
        }
      }
    ]
  },
  {
    path: "/team",
    component: Layouts,
    redirect: "/team/index",
    name: "TeamManagement",
    meta: {
      roles: ["admin", "team_owner"]
    },
    children: [
      {
        path: "index",
        component: () => import("@/pages/team-management/index.vue"),
        name: "Team",
        meta: {
          title: "团队管理",
          svgIcon: "team-management",
          affix: false,
          keepAlive: true,
          roles: ["admin", "team_owner"]
        }
      }
    ]
  },
  {
    path: "/config",
    component: Layouts,
    redirect: "/config/index",
    name: "ConfigManagement",
    meta: {
      roles: ["admin"]
    },
    children: [
      {
        path: "index",
        component: () => import("@/pages/user-config/index.vue"),
        name: "UserConfig",
        meta: {
          title: "用户配置",
          svgIcon: "user-config",
          affix: false,
          keepAlive: true,
          roles: ["admin"]
        }
      }
    ]
  },
  {
    path: "/file",
    component: Layouts,
    redirect: "/file/index",
    name: "FileManagement",
    meta: {
      roles: ["admin", "team_owner"]
    },
    children: [
      {
        path: "index",
        component: () => import("@/pages/file/index.vue"),
        name: "File",
        meta: {
          title: "文件管理",
          svgIcon: "file",
          affix: false,
          keepAlive: true,
          roles: ["admin", "team_owner"]
        }
      }
    ]
  },
  {
    path: "/knowledgebase",
    component: Layouts,
    redirect: "/knowledgebase/index",
    name: "KnowledgeBaseManagement",
    meta: {
      roles: ["admin", "team_owner"]
    },
    children: [
      {
        path: "index",
        component: () => import("@/pages/knowledgebase/index.vue"),
        name: "KnowledgeBase",
        meta: {
          title: "知识库管理",
          svgIcon: "kb",
          affix: false,
          keepAlive: true,
          roles: ["admin", "team_owner"]
        }
      }
    ]
  },
  {
    path: "/conversation",
    component: Layouts,
    redirect: "/conversation/index",
    name: "ConversationManagement",
    meta: {
      roles: ["admin"]
    },
    children: [
      {
        path: "index",
        component: () => import("@/pages/conversation/index.vue"),
        name: "Conversation",
        meta: {
          title: "用户会话管理",
          svgIcon: "conversation",
          affix: false,
          keepAlive: true,
          roles: ["admin"]
        }
      }
    ]
  }
]

/** 路由实例 */
export const router = createRouter({
  history: routerConfig.history,
  routes: routerConfig.thirdLevelRouteCache ? flatMultiLevelRoutes(constantRoutes) : constantRoutes
})

/** 重置路由 */
export function resetRouter() {
  try {
    // 注意：所有动态路由路由必须带有 Name 属性，否则可能会不能完全重置干净
    router.getRoutes().forEach((route) => {
      const { name, meta } = route
      if (name && meta.roles?.length) {
        router.hasRoute(name) && router.removeRoute(name)
      }
    })
  } catch {
    // 强制刷新浏览器也行，只是交互体验不是很好
    location.reload()
  }
}

// 注册路由导航守卫
registerNavigationGuard(router)
