/** 포커스 Composable */
export function useFocus() {
  // 포커스 여부
  const isFocus = ref<boolean>(false)

  // 포커스 잃기
  const handleBlur = () => {
    isFocus.value = false
  }

  // 포커스 얻기
  const handleFocus = () => {
    isFocus.value = true
  }

  return { isFocus, handleBlur, handleFocus }
}
