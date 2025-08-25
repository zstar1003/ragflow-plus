import type { UploadUserFile } from "element-plus"
import { uploadFileApiV2, uploadLargeFile } from "@@/apis/files/upload"
import { ElMessage } from "element-plus"
import { computed, reactive, readonly, ref } from "vue"

/**
 * 파일 업로드 상태 열거형
 */
export enum UploadStatus {
  PENDING = "pending",
  UPLOADING = "uploading",
  SUCCESS = "success",
  ERROR = "error",
  CANCELLED = "cancelled"
}

/**
 * 업로드 파일 항목 인터페이스
 */
export interface UploadFileItem {
  id: string
  file: File
  name: string
  size: number
  status: UploadStatus
  progress: number
  error?: string
  uploadedAt?: Date
}

/**
 * 파일 업로드 설정 인터페이스
 */
export interface FileUploadConfig {
  /** 최대 동시 업로드 수 */
  maxConcurrent?: number
  /** 대용량 파일 임계값(바이트), 이 크기를 초과하면 청크 업로드 사용 */
  largeFileThreshold?: number
  /** 청크 크기(바이트) */
  chunkSize?: number
  /** 업로드 타임아웃 시간(밀리초) */
  timeout?: number
  /** 자동 업로드 시작 여부 */
  autoUpload?: boolean
  /** 업로드 성공 콜백 */
  onSuccess?: (fileItem: UploadFileItem) => void
  /** 업로드 실패 콜백 */
  onError?: (fileItem: UploadFileItem, error: Error) => void
  /** 모든 파일 업로드 완료 콜백 */
  onComplete?: (results: UploadFileItem[]) => void
}

/**
 * 기본 설정
 */
const DEFAULT_CONFIG: Required<FileUploadConfig> = {
  maxConcurrent: 3,
  largeFileThreshold: 10 * 1024 * 1024, // 10MB
  chunkSize: 5 * 1024 * 1024, // 5MB
  timeout: 300000, // 5분
  autoUpload: false,
  onSuccess: () => {},
  onError: () => {},
  onComplete: () => {}
}

/**
 * 파일 업로드 Composable
 * 큐 관리, 진행률 추적, 오류 처리 등을 포함한 완전한 파일 업로드 기능 제공
 */
export function useFileUpload(config: FileUploadConfig = {}) {
  // 설정 병합
  const finalConfig = reactive({ ...DEFAULT_CONFIG, ...config })

  // 업로드 큐
  const uploadQueue = ref<UploadFileItem[]>([])

  // 현재 업로드 중인 파일 수
  const uploadingCount = ref(0)

  // 업로드 상태
  const isUploading = computed(() => uploadingCount.value > 0)

  // 전체 진행률
  const totalProgress = computed(() => {
    if (uploadQueue.value.length === 0) return 0
    const totalProgress = uploadQueue.value.reduce((sum, item) => sum + item.progress, 0)
    return Math.round(totalProgress / uploadQueue.value.length)
  })

  // 통계 정보
  const stats = computed(() => {
    const total = uploadQueue.value.length
    const pending = uploadQueue.value.filter(item => item.status === UploadStatus.PENDING).length
    const uploading = uploadQueue.value.filter(item => item.status === UploadStatus.UPLOADING).length
    const success = uploadQueue.value.filter(item => item.status === UploadStatus.SUCCESS).length
    const error = uploadQueue.value.filter(item => item.status === UploadStatus.ERROR).length
    const cancelled = uploadQueue.value.filter(item => item.status === UploadStatus.CANCELLED).length

    return { total, pending, uploading, success, error, cancelled }
  })

  /**
   * 고유 ID 생성
   */
  function generateId(): string {
    return `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * 업로드 큐에 파일 추가
   */
  function addFiles(files: File[] | UploadUserFile[]): UploadFileItem[] {
    const fileItems: UploadFileItem[] = []

    files.forEach((file) => {
      const rawFile = "raw" in file ? file.raw : file as File
      if (!rawFile) return

      const fileItem: UploadFileItem = {
        id: generateId(),
        file: rawFile,
        name: rawFile.name,
        size: rawFile.size,
        status: UploadStatus.PENDING,
        progress: 0
      }

      fileItems.push(fileItem)
      uploadQueue.value.push(fileItem)
    })

    // 자동 업로드가 활성화된 경우 즉시 업로드 시작
    if (finalConfig.autoUpload) {
      startUpload()
    }

    return fileItems
  }

  /**
   * 파일 제거
   */
  function removeFile(id: string): boolean {
    const index = uploadQueue.value.findIndex(item => item.id === id)
    if (index === -1) return false

    const fileItem = uploadQueue.value[index]

    // 업로드 중인 경우 먼저 취소
    if (fileItem.status === UploadStatus.UPLOADING) {
      cancelFile(id)
    }

    uploadQueue.value.splice(index, 1)
    return true
  }

  /**
   * 파일 업로드 취소
   */
  function cancelFile(id: string): boolean {
    const fileItem = uploadQueue.value.find(item => item.id === id)
    if (!fileItem) return false

    if (fileItem.status === UploadStatus.UPLOADING) {
      fileItem.status = UploadStatus.CANCELLED
      uploadingCount.value--
    }

    return true
  }

  /**
   * 업로드 재시도
   */
  function retryFile(id: string): void {
    const fileItem = uploadQueue.value.find(item => item.id === id)
    if (!fileItem) return

    if (fileItem.status === UploadStatus.ERROR || fileItem.status === UploadStatus.CANCELLED) {
      fileItem.status = UploadStatus.PENDING
      fileItem.progress = 0
      fileItem.error = undefined

      if (finalConfig.autoUpload) {
        startUpload()
      }
    }
  }

  /**
   * 단일 파일 업로드
   */
  /**
   * 단일 파일 업로드
   */
  async function uploadSingleFile(fileItem: UploadFileItem): Promise<void> {
    if (fileItem.status !== UploadStatus.PENDING) return

    fileItem.status = UploadStatus.UPLOADING
    fileItem.progress = 0
    uploadingCount.value++

    // 취소 플래그 추가
    let isCancelled = false
    const checkCancellation = () => {
      isCancelled = fileItem.status === UploadStatus.CANCELLED
      return isCancelled
    }

    try {
      const formData = new FormData()
      formData.append("files", fileItem.file)

      // 파일 크기에 따라 업로드 방식 선택
      if (fileItem.size > finalConfig.largeFileThreshold) {
        // 대용량 파일 청크 업로드
        await uploadLargeFile(fileItem.file, {
          chunkSize: finalConfig.chunkSize,
          timeout: finalConfig.timeout,
          onProgress: (progress) => {
            if (!checkCancellation()) {
              fileItem.progress = progress
            }
          }
        })
      } else {
        // 일반 파일 업로드
        await uploadFileApiV2(formData, {
          timeout: finalConfig.timeout,
          onProgress: (progress) => {
            if (!checkCancellation()) {
              fileItem.progress = progress
            }
          }
        })
      }

      // 취소되었는지 확인
      if (checkCancellation()) {
        return
      }

      fileItem.status = UploadStatus.SUCCESS
      fileItem.progress = 100
      fileItem.uploadedAt = new Date()

      finalConfig.onSuccess(fileItem)
      ElMessage.success(`파일 "${fileItem.name}" 업로드 성공`)
    } catch (error) {
      // 취소되었는지 확인
      if (checkCancellation()) {
        return
      }

      fileItem.status = UploadStatus.ERROR
      fileItem.error = error instanceof Error ? error.message : "업로드 실패"

      finalConfig.onError(fileItem, error instanceof Error ? error : new Error("업로드 실패"))
      ElMessage.error(`파일 "${fileItem.name}" 업로드 실패: ${fileItem.error}`)
    } finally {
      uploadingCount.value--
    }
  }

  /**
   * 업로드 시작
   */
  async function startUpload(): Promise<void> {
    const pendingFiles = uploadQueue.value.filter(item => item.status === UploadStatus.PENDING)

    if (pendingFiles.length === 0) {
      return
    }

    // 동시 실행 수 제어
    const uploadPromises: Promise<void>[] = []

    for (const fileItem of pendingFiles) {
      // 현재 업로드 수가 최대 동시 실행 수보다 작을 때까지 대기
      while (uploadingCount.value >= finalConfig.maxConcurrent) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }

      const uploadPromise = uploadSingleFile(fileItem)
      uploadPromises.push(uploadPromise)
    }

    // 모든 업로드 완료 대기
    await Promise.allSettled(uploadPromises)

    // 완료 콜백 실행
    finalConfig.onComplete(uploadQueue.value)
  }

  /**
   * 큐 비우기
   */
  function clearQueue(): void {
    // 업로드 중인 모든 파일 취소
    uploadQueue.value
      .filter(item => item.status === UploadStatus.UPLOADING)
      .forEach(item => cancelFile(item.id))

    uploadQueue.value = []
  }

  /**
   * 완료된 파일 지우기
   */
  function clearCompleted(): void {
    uploadQueue.value = uploadQueue.value.filter(
      item => item.status !== UploadStatus.SUCCESS && item.status !== UploadStatus.ERROR
    )
  }

  return {
    // 상태
    uploadQueue: readonly(uploadQueue),
    isUploading: readonly(isUploading),
    totalProgress: readonly(totalProgress),
    stats: readonly(stats),

    // 설정
    config: finalConfig,

    // 메서드
    addFiles,
    removeFile,
    cancelFile,
    retryFile,
    startUpload,
    clearQueue,
    clearCompleted
  }
}
