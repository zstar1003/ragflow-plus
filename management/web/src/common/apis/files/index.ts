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
): Promise<Blob> {
  return request<Blob>({
    url: `/api/v1/files/${fileId}/download`,
    method: "get",
    responseType: "blob",
    timeout: 300000,
    onDownloadProgress,
    headers: {
      Accept: "application/octet-stream"
    }
  })
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
