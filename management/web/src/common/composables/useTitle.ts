import { useLocale } from "./useLocale"

/** 项目标题 */
const VITE_APP_TITLE = import.meta.env.VITE_APP_TITLE ?? "V3 Admin Vite"
const dynamicTitle = ref<string>("")
const { t } = useLocale()

/** 设置标题，保留原始路由标题以响应语言变化 */
function setTitle(title?: string) {
  dynamicTitle.value = title ?? ""
}

watchEffect(() => {
  document.title = dynamicTitle.value ? `${VITE_APP_TITLE} | ${t(dynamicTitle.value)}` : VITE_APP_TITLE
})

export function useTitle() {
  return { setTitle }
}
