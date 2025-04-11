import type { AxiosResponse } from "axios"
import type { FileData, PageQuery, PageResult } from "./type"
import { request } from "@/http/axios"
import axios from "axios"

/**
 * 获取文件列表
 * @param params 查询参数
 */
export function getFileListApi(params: PageQuery & { name?: string }) {
  return request<{ data: PageResult<FileData>, code: number, message: string }>({
    url: "/api/v1/files",
    method: "get",
    params
  })
}

/**
 * 下载文件 - 使用流式下载
 * @param fileId 文件ID
 * @param onDownloadProgress 下载进度回调
 */
export function downloadFileApi(
  fileId: string,
  onDownloadProgress?: (progressEvent: any) => void
): Promise<AxiosResponse<Blob>> {
  console.log(`发起文件下载请求: ${fileId}`)
  const source = axios.CancelToken.source()

  return request({
    url: `/api/v1/files/${fileId}/download`,
    method: "get",
    responseType: "blob",
    timeout: 300000,
    onDownloadProgress,
    cancelToken: source.token,
    validateStatus: (_status) => {
      // 允许所有状态码，以便在前端统一处理错误
      return true
    }
  }).then((response: unknown) => {
    const axiosResponse = response as AxiosResponse<Blob>
    console.log(`下载响应: ${axiosResponse.status}`, axiosResponse.data)
    // 确保响应对象包含必要的属性
    if (axiosResponse.data instanceof Blob && axiosResponse.data.size > 0) {
      // 如果是成功的Blob响应，确保状态码为200
      if (!axiosResponse.status) axiosResponse.status = 200
      return axiosResponse
    }
    return axiosResponse
  }).catch((error: any) => {
    console.error("下载请求失败:", error)
    // 将错误信息转换为统一格式
    if (error.response) {
      error.response.data = {
        message: error.response.data?.message || "服务器错误"
      }
    }
    return Promise.reject(error)
  }) as Promise<AxiosResponse<Blob>>
}

/**
 * 取消下载
 */
export function cancelDownload() {
  if (axios.isCancel(Error)) {
    axios.CancelToken.source().cancel("用户取消下载")
  }
}

/**
 * 删除文件
 * @param fileId 文件ID
 */
export function deleteFileApi(fileId: string) {
  return request<{ code: number, message: string }>({
    url: `/api/v1/files/${fileId}`,
    method: "delete"
  })
}

/**
 * 批量删除文件
 * @param fileIds 文件ID数组
 */
export function batchDeleteFilesApi(fileIds: string[]) {
  return request<{ code: number, message: string }>({
    url: "/api/v1/files/batch",
    method: "delete",
    data: { ids: fileIds }
  })
}

/**
 * 上传文件
 */
export function uploadFileApi(formData: FormData) {
  return request<{
    code: number
    data: Array<{
      name: string
      size: number
      type: string
      status: string
    }>
    message: string
  }>({
    url: "/api/v1/files/upload",
    method: "post",
    data: formData,
    headers: {
      "Content-Type": "multipart/form-data"
    }
  })
}
