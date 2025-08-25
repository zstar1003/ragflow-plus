import type { App, Directive } from "vue"
import { useUserStore } from "@/pinia/stores/user"
import { isArray } from "@@/utils/validate"

/**
 * @name 권한 지시어
 * @description 권한 판단 함수 checkPermission 기능과 유사
 */
const permission: Directive = {
  mounted(el, binding) {
    const { value: permissionRoles } = binding
    const { roles } = useUserStore()
    if (isArray(permissionRoles) && permissionRoles.length > 0) {
      const hasPermission = roles.some(role => permissionRoles.includes(role))
      hasPermission || el.parentNode?.removeChild(el)
    } else {
      throw new Error(`매개변수는 배열이어야 하며 길이가 0보다 커야 합니다. 참조: v-permission="['admin', 'editor']"`)
    }
  }
}

export function installPermissionDirective(app: App) {
  app.directive("permission", permission)
}
