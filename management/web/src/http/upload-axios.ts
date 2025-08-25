import type { AxiosInstance, AxiosRequestConfig } from "axios"
import { getToken } from "@@/utils/cache/cookies"
import axios from "axios"
import { merge } from "lodash-es"

/**
 * 파일 업로드 전용 axios 인스턴스 생성
 * 더 긴 타임아웃 시간과 업로드 진행률 지원 제공
 */
function createUploadInstance() {
  const instance = axios.create()

  // 요청 인터셉터
  instance.interceptors.request.use(
    (config) => {
      // 대용량 파일 업로드를 위해 더 긴 타임아웃 시간 설정
      if (!config.timeout) {
        config.timeout = 300000 // 5분
      }
      return config
    },
    error => Promise.reject(error)
  )

  // 응답 인터셉터
  instance.interceptors.response.use(
    response => response.data,
    (error) => {
      if (error.code === "ECONNABORTED" && error.message.includes("timeout")) {
        ElMessage.error("파일 업로드 시간 초과, 네트워크 연결을 확인하거나 더 작은 파일을 업로드해 보세요")
      }
      return Promise.reject(error)
    }
  )

  return instance
}

/**
 * 파일 업로드 전용 요청 메서드 생성
 * @param instance axios 인스턴스
 */
function createUploadRequest(instance: AxiosInstance) {
  return <T>(config: AxiosRequestConfig & {
    onUploadProgress?: (progressEvent: any) => void
    timeout?: number
  }): Promise<T> => {
    const token = getToken()

    const defaultConfig: AxiosRequestConfig = {
      baseURL: import.meta.env.VITE_BASE_URL,
      headers: {
        Authorization: token ? `Bearer ${token}` : undefined
      },
      timeout: config.timeout || 300000, // 기본 5분
      withCredentials: false,
      // 업로드 진행률 콜백
      onUploadProgress: config.onUploadProgress
    }

    const mergeConfig = merge(defaultConfig, config)
    return instance(mergeConfig)
  }
}

/** 파일 업로드 전용 인스턴스 */
const uploadInstance = createUploadInstance()

/** 파일 업로드 전용 요청 메서드 */
export const uploadRequest = createUploadRequest(uploadInstance)
