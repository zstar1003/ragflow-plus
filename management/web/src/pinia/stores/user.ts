import { pinia } from "@/pinia"
import { resetRouter } from "@/router"
import { routerConfig } from "@/router/config"
import { getCurrentUserApi } from "@@/apis/users"
import { setToken as _setToken, getToken, removeToken } from "@@/utils/cache/cookies"
import { useSettingsStore } from "./settings"
import { useTagsViewStore } from "./tags-view"

export const useUserStore = defineStore("user", () => {
  const token = ref<string>(getToken() || "")
  const roles = ref<string[]>([])
  const username = ref<string>("")
  const avatar = ref<string>("https://pic1.zhimg.com/v2-aaf12b68b54b8812e6b449e7368d30cf_l.jpg?source=32738c0c&needBackground=1")
  const tagsViewStore = useTagsViewStore()
  const settingsStore = useSettingsStore()

  // Token 설정
  const setToken = (value: string) => {
    _setToken(value)
    token.value = value
  }

  // 사용자 정보 가져오기
  const getInfo = async () => {
    const { data } = await getCurrentUserApi()
    username.value = data.username
    // 반환된 roles가 비어있지 않은 배열인지 검증, 그렇지 않으면 기본 역할을 넣어 라우터 가드 로직이 무한 루프에 빠지는 것을 방지
    roles.value = data.roles?.length > 0 ? data.roles : routerConfig.defaultRoles
  }

  // 역할 변경 시뮬레이션
  const changeRoles = (role: string) => {
    const newToken = `token-${role}`
    token.value = newToken
    _setToken(newToken)
    // 다시 로그인하는 대신 페이지 새로고침 사용
    location.reload()
  }

  // 로그아웃
  const logout = () => {
    removeToken()
    token.value = ""
    roles.value = []
    resetRouter()
    resetTagsView()
  }

  // Token 초기화
  const resetToken = () => {
    removeToken()
    token.value = ""
    roles.value = []
  }

  // Visited Views와 Cached Views 초기화
  const resetTagsView = () => {
    if (!settingsStore.cacheTagsView) {
      tagsViewStore.delAllVisitedViews()
      tagsViewStore.delAllCachedViews()
    }
  }

  return { token, roles, username, avatar, setToken, getInfo, changeRoles, logout, resetToken }
})

/**
 * @description SPA 애플리케이션에서 pinia 인스턴스가 활성화되기 전에 store를 사용할 수 있습니다
 * @description SSR 애플리케이션에서 setup 외부에서 store를 사용할 수 있습니다
 */
export function useUserStoreOutside() {
  return useUserStore(pinia)
}
