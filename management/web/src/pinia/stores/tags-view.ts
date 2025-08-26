import type { RouteLocationNormalizedGeneric } from "vue-router"
import { pinia } from "@/pinia"
import { getCachedViews, getVisitedViews, setCachedViews, setVisitedViews } from "@@/utils/cache/local-storage"
import { useSettingsStore } from "./settings"

export type TagView = Partial<RouteLocationNormalizedGeneric>

export const useTagsViewStore = defineStore("tags-view", () => {
  const { cacheTagsView } = useSettingsStore()
  const visitedViews = ref<TagView[]>(cacheTagsView ? getVisitedViews() : [])
  const cachedViews = ref<string[]>(cacheTagsView ? getCachedViews() : [])

  // 태그바 데이터 캐시
  watchEffect(() => {
    setVisitedViews(visitedViews.value)
    setCachedViews(cachedViews.value)
  })

  // #region add
  const addVisitedView = (view: TagView) => {
    // 동일한 visitedView가 이미 존재하는지 확인
    const index = visitedViews.value.findIndex(v => v.path === view.path)
    if (index !== -1) {
      // query 파라미터 손실 방지
      visitedViews.value[index].fullPath !== view.fullPath && (visitedViews.value[index] = { ...view })
    } else {
      // 새로운 visitedView 추가
      visitedViews.value.push({ ...view })
    }
  }

  const addCachedView = (view: TagView) => {
    if (typeof view.name !== "string") return
    if (cachedViews.value.includes(view.name)) return
    if (view.meta?.keepAlive) {
      cachedViews.value.push(view.name)
    }
  }
  // #endregion

  // #region del
  const delVisitedView = (view: TagView) => {
    const index = visitedViews.value.findIndex(v => v.path === view.path)
    if (index !== -1) {
      visitedViews.value.splice(index, 1)
    }
  }

  const delCachedView = (view: TagView) => {
    if (typeof view.name !== "string") return
    const index = cachedViews.value.indexOf(view.name)
    if (index !== -1) {
      cachedViews.value.splice(index, 1)
    }
  }
  // #endregion

  // #region delOthers
  const delOthersVisitedViews = (view: TagView) => {
    visitedViews.value = visitedViews.value.filter((v) => {
      return v.meta?.affix || v.path === view.path
    })
  }

  const delOthersCachedViews = (view: TagView) => {
    if (typeof view.name !== "string") return
    const index = cachedViews.value.indexOf(view.name)
    if (index !== -1) {
      cachedViews.value = cachedViews.value.slice(index, index + 1)
    } else {
      // index = -1인 경우, 캐시된 tags가 없음
      cachedViews.value = []
    }
  }
  // #endregion

  // #region delAll
  const delAllVisitedViews = () => {
    // 고정된 tags 유지
    visitedViews.value = visitedViews.value.filter(tag => tag.meta?.affix)
  }

  const delAllCachedViews = () => {
    cachedViews.value = []
  }
  // #endregion

  return {
    visitedViews,
    cachedViews,
    addVisitedView,
    addCachedView,
    delVisitedView,
    delCachedView,
    delOthersVisitedViews,
    delOthersCachedViews,
    delAllVisitedViews,
    delAllCachedViews
  }
})

/**
 * @description SPA 애플리케이션에서 pinia 인스턴스가 활성화되기 전에 store를 사용할 수 있습니다
 * @description SSR 애플리케이션에서 setup 외부에서 store를 사용할 수 있습니다
 */
export function useTagsViewStoreOutside() {
  return useTagsViewStore(pinia)
}
