import { pinia } from "@/pinia"
import { DeviceEnum, SIDEBAR_CLOSED, SIDEBAR_OPENED } from "@@/constants/app-key"
import { getSidebarStatus, setSidebarStatus } from "@@/utils/cache/local-storage"

interface Sidebar {
  opened: boolean
  withoutAnimation: boolean
}

/** 사이드바 상태 로컬 캐시 설정 */
function handleSidebarStatus(opened: boolean) {
  opened ? setSidebarStatus(SIDEBAR_OPENED) : setSidebarStatus(SIDEBAR_CLOSED)
}

export const useAppStore = defineStore("app", () => {
  // 사이드바 상태
  const sidebar: Sidebar = reactive({
    opened: getSidebarStatus() !== SIDEBAR_CLOSED,
    withoutAnimation: false
  })

  // 디바이스 타입
  const device = ref<DeviceEnum>(DeviceEnum.Desktop)

  // 사이드바 opened 상태 감시
  watch(
    () => sidebar.opened,
    (opened) => {
      handleSidebarStatus(opened)
    }
  )

  // 사이드바 토글
  const toggleSidebar = (withoutAnimation: boolean) => {
    sidebar.opened = !sidebar.opened
    sidebar.withoutAnimation = withoutAnimation
  }

  // 사이드바 닫기
  const closeSidebar = (withoutAnimation: boolean) => {
    sidebar.opened = false
    sidebar.withoutAnimation = withoutAnimation
  }

  // 디바이스 타입 변경
  const toggleDevice = (value: DeviceEnum) => {
    device.value = value
  }

  return { device, sidebar, toggleSidebar, closeSidebar, toggleDevice }
})

/**
 * @description SPA 애플리케이션에서 pinia 인스턴스가 활성화되기 전에 store를 사용할 수 있습니다
 * @description SSR 애플리케이션에서 setup 외부에서 store를 사용할 수 있습니다
 */
export function useAppStoreOutside() {
  return useAppStore(pinia)
}
