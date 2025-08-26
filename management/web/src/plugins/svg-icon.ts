import type { App } from "vue"
import SvgIcon from "~virtual/svg-component"

export function installSvgIcon(app: App) {
  // SvgIcon 컴포넌트 등록
  app.component("SvgIcon", SvgIcon)
}
