import type { AxiosInstance, AxiosRequestConfig } from "axios"
import { useUserStore } from "@/pinia/stores/user"
import { getToken } from "@@/utils/cache/cookies"
import axios from "axios"
import { get, merge } from "lodash-es"

/** 로그아웃하고 페이지를 강제로 새로고침 (로그인 페이지로 리디렉션) */
function logout() {
  useUserStore().logout()
  location.reload()
}

/** 요청 인스턴스 생성 */
function createInstance() {
  // axios 인스턴스를 instance로 명명하여 생성
  const instance = axios.create()
  // 요청 인터셉터
  instance.interceptors.request.use(
    // 전송 전
    config => config,
    // 전송 실패
    error => Promise.reject(error)
  )
  // 응답 인터셉터 (구체적인 비즈니스에 따라 적절히 조정)
  instance.interceptors.response.use(
    (response) => {
      // console.log("API Response:", response)
      // apiData는 api가 반환하는 데이터
      const apiData = response.data
      // 바이너리 데이터는 직접 반환
      const responseType = response.request?.responseType
      if (responseType === "blob" || responseType === "arraybuffer") return apiData
      // 이 code는 백엔드와 약정한 비즈니스 code
      const code = apiData.code
      // code가 없으면 프로젝트 백엔드에서 개발한 api가 아님을 의미
      if (code === undefined) {
        ElMessage.error("본 시스템의 인터페이스가 아닙니다")
        return Promise.reject(new Error("본 시스템의 인터페이스가 아닙니다"))
      }
      switch (code) {
        case 0:
          // 본 시스템은 code === 0을 사용하여 비즈니스 오류가 없음을 표시
          return apiData
        case 401:
          // Token 만료 시
          return logout()
        default:
          // 올바르지 않은 code
          ElMessage.error(apiData.message || "Error")
          return Promise.reject(new Error("Error"))
      }
    },
    (error) => {
      // status는 HTTP 상태 코드
      const status = get(error, "response.status")
      const message = get(error, "response.data.message")
      switch (status) {
        case 400:
          error.message = "요청 오류"
          break
        case 401:
          // Token 만료 시
          error.message = message || "권한 없음"
          logout()
          break
        case 403:
          error.message = message || "접근 거부"
          break
        case 404:
          error.message = "요청 주소 오류"
          break
        case 408:
          error.message = "요청 시간 초과"
          break
        case 500:
          error.message = "서버 내부 오류"
          break
        case 501:
          error.message = "서비스 미구현"
          break
        case 502:
          error.message = "게이트웨이 오류"
          break
        case 503:
          error.message = "서비스 사용 불가"
          break
        case 504:
          error.message = "게이트웨이 시간 초과"
          break
        case 505:
          error.message = "HTTP 버전이 지원되지 않음"
          break
      }
      ElMessage.error(error.message)
      return Promise.reject(error)
    }
  )
  return instance
}

/** 요청 메서드 생성 */
function createRequest(instance: AxiosInstance) {
  return <T>(config: AxiosRequestConfig): Promise<T> => {
    const token = getToken()
    // console.log("Request config:", config)
    // 기본 설정
    const defaultConfig: AxiosRequestConfig = {
      // 인터페이스 주소
      baseURL: import.meta.env.VITE_BASE_URL,
      // 요청 헤더
      headers: {
        // Token 포함
        "Authorization": token ? `Bearer ${token}` : undefined,
        "Content-Type": "application/json"
      },
      // 요청 본문
      data: {},
      // 요청 시간 초과
      timeout: 5000,
      // 크로스 도메인 요청 시 쿠키 포함 여부
      withCredentials: false
    }
    // 기본 설정 defaultConfig와 전달받은 사용자 정의 설정 config를 병합하여 mergeConfig 생성
    const mergeConfig = merge(defaultConfig, config)
    return instance(mergeConfig)
  }
}

/** 요청에 사용되는 인스턴스 */
const instance = createInstance()

/** 요청에 사용되는 메서드 */
export const request = createRequest(instance)
