import type { LoadingOptions } from "element-plus"

interface UseFullscreenLoading {
  <T extends (...args: Parameters<T>) => ReturnType<T>>(
    fn: T,
    options?: LoadingOptions
  ): (...args: Parameters<T>) => Promise<ReturnType<T>>
}

interface LoadingInstance {
  close: () => void
}

const DEFAULT_OPTIONS = {
  lock: true,
  text: "로딩 중..."
}

/**
 * @name 전체화면 로딩 Composable
 * @description 함수 fn을 전달하면, 실행 주기 동안 「전체화면」 Loading을 추가합니다
 * @param fn 실행할 함수
 * @param options LoadingOptions
 * @returns 새로운 함수를 반환하며, 해당 함수는 Promise를 반환합니다
 */
export const useFullscreenLoading: UseFullscreenLoading = (fn, options = {}) => {
  let loadingInstance: LoadingInstance
  return async (...args) => {
    try {
      loadingInstance = ElLoading.service({ ...DEFAULT_OPTIONS, ...options })
      return await fn(...args)
    } finally {
      loadingInstance.close()
    }
  }
}
