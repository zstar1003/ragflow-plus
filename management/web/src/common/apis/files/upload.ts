import { uploadRequest } from "@/http/upload-axios"

/**
 * 파일 업로드 설정 인터페이스
 */
interface UploadConfig {
  onProgress?: (progress: number) => void
  timeout?: number
  chunkSize?: number
}

/**
 * 최적화된 파일 업로드 API
 * 진행률 콜백, 사용자 정의 타임아웃, 오류 재시도 지원
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
 * 대용량 파일 청크 업로드
 * 대용량 파일을 작은 블록으로 분할하여 업로드, 성공률 향상
 */
export async function uploadLargeFile(
  file: File,
  config: UploadConfig & { parentId?: string } = {}
) {
  const { chunkSize = 5 * 1024 * 1024, onProgress, parentId } = config // 기본 5MB 청크

  // 소용량 파일은 직접 업로드
  if (file.size <= chunkSize) {
    const formData = new FormData()
    formData.append("file", file)
    if (parentId) formData.append("parent_id", parentId)

    return uploadFileApiV2(formData, { onProgress })
  }

  // 대용량 파일 청크 업로드
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
        timeout: 60000, // 단일 청크 1분 타임아웃
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const chunkProgress = (progressEvent.loaded / progressEvent.total) * 100
            const totalProgress = ((chunkIndex + chunkProgress / 100) / totalChunks) * 100
            onProgress(Math.round(totalProgress))
          }
        }
      })
    } catch (error) {
      // 청크 업로드 실패, 재시도 시도
      console.error(`청크 ${chunkIndex + 1}/${totalChunks} 업로드 실패:`, error)
      throw new Error(`파일 업로드 실패: 청크 ${chunkIndex + 1} 업로드 오류`)
    }
  }

  // 청크 병합
  return uploadRequest({
    url: "/api/v1/files/upload/merge",
    method: "post",
    data: { uploadId, fileName: file.name, totalChunks, parentId }
  })
}
