import type { App } from "vue"
import * as ElementPlusIconsVue from "@element-plus/icons-vue"

export function installElementPlusIcons(app: App) {
  // 모든 Element Plus Icons 등록
  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }
}
