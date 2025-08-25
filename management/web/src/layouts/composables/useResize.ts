import { useAppStore } from "@/pinia/stores/app"
import { useRouteListener } from "@@/composables/useRouteListener"
import { DeviceEnum } from "@@/constants/app-key"

/** Bootstrap의 반응형 디자인을 참고하여 최대 모바일 너비를 992로 설정 */
const MAX_MOBILE_WIDTH = 992

/**
 * @name 브라우저 너비 변화 Composable
 * @description 브라우저 너비 변화에 따라 Layout 레이아웃 변경
 */
export function useResize() {
  const appStore = useAppStore()
  const { listenerRouteChange } = useRouteListener()

  // 현재 기기가 모바일인지 판단하는 함수
  const isMobile = () => {
    const rect = document.body.getBoundingClientRect()
    return rect.width - 1 < MAX_MOBILE_WIDTH
  }

  // 창 크기 변경 이벤트를 처리하는 함수
  const resizeHandler = () => {
    if (!document.hidden) {
      const _isMobile = isMobile()
      appStore.toggleDevice(_isMobile ? DeviceEnum.Mobile : DeviceEnum.Desktop)
      _isMobile && appStore.closeSidebar(true)
    }
  }

  // 라우트 변경 감지, 기기 유형에 따라 레이아웃 조정
  listenerRouteChange(() => {
    if (appStore.device === DeviceEnum.Mobile && appStore.sidebar.opened) {
      appStore.closeSidebar(false)
    }
  })

  // 컴포넌트 마운트 전 창 크기 변경 이벤트 리스너 추가
  onBeforeMount(() => {
    window.addEventListener("resize", resizeHandler)
  })

  // 컴포넌트 마운트 후 창 크기에 따라 기기 유형 판단 및 레이아웃 조정
  onMounted(() => {
    if (isMobile()) {
      appStore.toggleDevice(DeviceEnum.Mobile)
      appStore.closeSidebar(true)
    }
  })

  // 컴포넌트 언마운트 전 창 크기 변경 이벤트 리스너 제거
  onBeforeUnmount(() => {
    window.removeEventListener("resize", resizeHandler)
  })
}
