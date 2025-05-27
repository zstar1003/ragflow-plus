import type { AxiosInstance, AxiosRequestConfig } from "axios"
import { getToken } from "@@/utils/cache/cookies"
import axios from "axios"
import { merge } from "lodash-es"

/**
 * 创建专用于文件上传的axios实例
 * 具有更长的超时时间和上传进度支持
 */
function createUploadInstance() {
  const instance = axios.create()

  // 请求拦截器
  instance.interceptors.request.use(
    (config) => {
      // 为大文件上传设置更长的超时时间
      if (!config.timeout) {
        config.timeout = 300000 // 5分钟
      }
      return config
    },
    error => Promise.reject(error)
  )

  // 响应拦截器
  instance.interceptors.response.use(
    response => response.data,
    (error) => {
      if (error.code === "ECONNABORTED" && error.message.includes("timeout")) {
        ElMessage.error("文件上传超时，请检查网络连接或尝试上传较小的文件")
      }
      return Promise.reject(error)
    }
  )

  return instance
}

/**
 * 创建文件上传专用请求方法
 * @param instance axios实例
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
      timeout: config.timeout || 300000, // 默认5分钟
      withCredentials: false,
      // 上传进度回调
      onUploadProgress: config.onUploadProgress
    }

    const mergeConfig = merge(defaultConfig, config)
    return instance(mergeConfig)
  }
}

/** 文件上传专用实例 */
const uploadInstance = createUploadInstance()

/** 文件上传专用请求方法 */
export const uploadRequest = createUploadRequest(uploadInstance)
