import { getActiveThemeName, setActiveThemeName } from "@@/utils/cache/local-storage"
import { setCssVar } from "@@/utils/css"

const DEFAULT_THEME_NAME = "normal"

type DefaultThemeName = typeof DEFAULT_THEME_NAME

/** 등록된 테마 이름, 그 중 DefaultThemeName은 필수입니다 */
export type ThemeName = DefaultThemeName | "dark" | "dark-blue"

interface ThemeList {
  title: string
  name: ThemeName
}

/** 테마 목록 */
const themeList: ThemeList[] = [
  {
    title: "기본",
    name: DEFAULT_THEME_NAME
  },
  {
    title: "다크",
    name: "dark"
  },
  {
    title: "딥블루",
    name: "dark-blue"
  }
]

/** 현재 적용 중인 테마 이름 */
const activeThemeName = ref<ThemeName>(getActiveThemeName() || DEFAULT_THEME_NAME)

/** 테마 설정 */
function setTheme({ clientX, clientY }: MouseEvent, value: ThemeName) {
  const maxRadius = Math.hypot(
    Math.max(clientX, window.innerWidth - clientX),
    Math.max(clientY, window.innerHeight - clientY)
  )
  setCssVar("--v3-theme-x", `${clientX}px`)
  setCssVar("--v3-theme-y", `${clientY}px`)
  setCssVar("--v3-theme-r", `${maxRadius}px`)
  const handler = () => {
    activeThemeName.value = value
  }
  document.startViewTransition ? document.startViewTransition(handler) : handler()
}

/** html 루트 요소에 class 추가 */
function addHtmlClass(value: ThemeName) {
  document.documentElement.classList.add(value)
}

/** html 루트 요소에서 다른 테마 class 제거 */
function removeHtmlClass(value: ThemeName) {
  const otherThemeNameList = themeList.map(item => item.name).filter(name => name !== value)
  document.documentElement.classList.remove(...otherThemeNameList)
}

/** 초기화 */
function initTheme() {
  // watchEffect로 부작용 수집
  watchEffect(() => {
    const value = activeThemeName.value
    removeHtmlClass(value)
    addHtmlClass(value)
    setActiveThemeName(value)
  })
}

/** 테마 Composable */
export function useTheme() {
  return { themeList, activeThemeName, initTheme, setTheme }
}
