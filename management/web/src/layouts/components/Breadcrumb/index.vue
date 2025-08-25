<script lang="ts" setup>
import type { RouteLocationMatched } from "vue-router"
import { useRouteListener } from "@@/composables/useRouteListener"
import { compile } from "path-to-regexp"

const route = useRoute()

const router = useRouter()

const { listenerRouteChange } = useRouteListener()

/** 반응형 데이터 breadcrumbs 정의, 브레드크럼 네비게이션 정보 저장용 */
const breadcrumbs = ref<RouteLocationMatched[]>([])

/** 브레드크럼 네비게이션 정보 가져오기 */
function getBreadcrumb() {
  breadcrumbs.value = route.matched.filter(item => item.meta?.title && item.meta?.breadcrumb !== false)
}

/** 라우트 경로 컴파일 */
function pathCompile(path: string) {
  const toPath = compile(path)
  return toPath(route.params)
}

/** 브레드크럼 네비게이션 클릭 이벤트 처리 */
function handleLink(item: RouteLocationMatched) {
  const { redirect, path } = item
  if (redirect) return router.push(redirect as string)
  router.push(pathCompile(path))
}

// 라우트 변경 감지, 브레드크럼 네비게이션 정보 업데이트
listenerRouteChange((route) => {
  if (route.path.startsWith("/redirect/")) return
  getBreadcrumb()
}, true)
</script>

<template>
  <el-breadcrumb>
    <el-breadcrumb-item v-for="(item, index) in breadcrumbs" :key="item.path">
      <span v-if="item.redirect === 'noRedirect' || index === breadcrumbs.length - 1" class="no-redirect">
        {{ item.meta.title }}
      </span>
      <a v-else @click.prevent="handleLink(item)">
        {{ item.meta.title }}
      </a>
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>

<style lang="scss" scoped>
.el-breadcrumb {
  line-height: var(--v3-navigationbar-height);
  .no-redirect {
    color: var(--el-text-color-placeholder);
  }
  a {
    font-weight: normal;
  }
}
</style>
