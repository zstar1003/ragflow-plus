import { uploadRequest } from "@/http/upload-axios"

/**
 * 文件上传配置接口
 */
interface UploadConfig {
  onProgress?: (progress: number) => void
  timeout?: number
  chunkSize?: number
}

/**
 * 优化的文件上传API
 * 支持进度回调、自定义超时、错误重试
 */
export function uploadFileApiV2(
  formData: FormData,
  config: UploadConfig = {}
) {
  const { onProgress, timeout = 300000 } = config

  return uploadRequest<{
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
    timeout,
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onProgress(progress)
      }
    }
  })
}

/**
 * 分块上传大文件
 * 将大文件分割成小块进行上传，提高成功率
 */
export async function uploadLargeFile(
  file: File,
  config: UploadConfig & { parentId?: string } = {}
) {
  const { chunkSize = 5 * 1024 * 1024, onProgress, parentId } = config // 默认5MB分块

  // 小文件直接上传
  if (file.size <= chunkSize) {
    const formData = new FormData()
    formData.append("file", file)
    if (parentId) formData.append("parent_id", parentId)

    return uploadFileApiV2(formData, { onProgress })
  }

  // 大文件分块上传
  const totalChunks = Math.ceil(file.size / chunkSize)
  const uploadId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

  for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
    const start = chunkIndex * chunkSize
    const end = Math.min(start + chunkSize, file.size)
    const chunk = file.slice(start, end)

    const formData = new FormData()
    formData.append("chunk", chunk)
    formData.append("chunkIndex", chunkIndex.toString())
    formData.append("totalChunks", totalChunks.toString())
    formData.append("uploadId", uploadId)
    formData.append("fileName", file.name)
    if (parentId) formData.append("parent_id", parentId)

    try {
      await uploadRequest({
        url: "/api/v1/files/upload/chunk",
        method: "post",
        data: formData,
        timeout: 60000, // 单个分块1分钟超时
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const chunkProgress = (progressEvent.loaded / progressEvent.total) * 100
            const totalProgress = ((chunkIndex + chunkProgress / 100) / totalChunks) * 100
            onProgress(Math.round(totalProgress))
          }
        }
      })
    } catch (error) {
      // 分块上传失败，尝试重试
      console.error(`分块 ${chunkIndex + 1}/${totalChunks} 上传失败:`, error)
      throw new Error(`文件上传失败：分块 ${chunkIndex + 1} 上传出错`)
    }
  }

  // 合并分块
  return uploadRequest({
    url: "/api/v1/files/upload/merge",
    method: "post",
    data: { uploadId, fileName: file.name, totalChunks, parentId }
  })
}
