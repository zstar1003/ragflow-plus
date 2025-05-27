import type { UploadUserFile } from "element-plus"
import { uploadFileApiV2, uploadLargeFile } from "@@/apis/files/upload"
import { ElMessage } from "element-plus"
import { computed, reactive, readonly, ref } from "vue"

/**
 * 文件上传状态枚举
 */
export enum UploadStatus {
  PENDING = "pending",
  UPLOADING = "uploading",
  SUCCESS = "success",
  ERROR = "error",
  CANCELLED = "cancelled"
}

/**
 * 上传文件项接口
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
 * 文件上传配置接口
 */
export interface FileUploadConfig {
  /** 最大并发上传数 */
  maxConcurrent?: number
  /** 大文件阈值（字节），超过此大小使用分块上传 */
  largeFileThreshold?: number
  /** 分块大小（字节） */
  chunkSize?: number
  /** 上传超时时间（毫秒） */
  timeout?: number
  /** 是否自动开始上传 */
  autoUpload?: boolean
  /** 上传成功回调 */
  onSuccess?: (fileItem: UploadFileItem) => void
  /** 上传失败回调 */
  onError?: (fileItem: UploadFileItem, error: Error) => void
  /** 所有文件上传完成回调 */
  onComplete?: (results: UploadFileItem[]) => void
}

/**
 * 默认配置
 */
const DEFAULT_CONFIG: Required<FileUploadConfig> = {
  maxConcurrent: 3,
  largeFileThreshold: 10 * 1024 * 1024, // 10MB
  chunkSize: 5 * 1024 * 1024, // 5MB
  timeout: 300000, // 5分钟
  autoUpload: false,
  onSuccess: () => {},
  onError: () => {},
  onComplete: () => {}
}

/**
 * 文件上传 Composable
 * 提供完整的文件上传功能，包括队列管理、进度跟踪、错误处理等
 */
export function useFileUpload(config: FileUploadConfig = {}) {
  // 合并配置
  const finalConfig = reactive({ ...DEFAULT_CONFIG, ...config })

  // 上传队列
  const uploadQueue = ref<UploadFileItem[]>([])

  // 当前上传中的文件数量
  const uploadingCount = ref(0)

  // 上传状态
  const isUploading = computed(() => uploadingCount.value > 0)

  // 总体进度
  const totalProgress = computed(() => {
    if (uploadQueue.value.length === 0) return 0
    const totalProgress = uploadQueue.value.reduce((sum, item) => sum + item.progress, 0)
    return Math.round(totalProgress / uploadQueue.value.length)
  })

  // 统计信息
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
   * 生成唯一ID
   */
  function generateId(): string {
    return `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * 添加文件到上传队列
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

    // 如果启用自动上传，立即开始上传
    if (finalConfig.autoUpload) {
      startUpload()
    }

    return fileItems
  }

  /**
   * 移除文件
   */
  function removeFile(id: string): boolean {
    const index = uploadQueue.value.findIndex(item => item.id === id)
    if (index === -1) return false

    const fileItem = uploadQueue.value[index]

    // 如果正在上传，先取消
    if (fileItem.status === UploadStatus.UPLOADING) {
      cancelFile(id)
    }

    uploadQueue.value.splice(index, 1)
    return true
  }

  /**
   * 取消文件上传
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
   * 重试上传
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
   * 上传单个文件
   */
  /**
   * 上传单个文件
   */
  async function uploadSingleFile(fileItem: UploadFileItem): Promise<void> {
    if (fileItem.status !== UploadStatus.PENDING) return

    fileItem.status = UploadStatus.UPLOADING
    fileItem.progress = 0
    uploadingCount.value++

    // 添加取消标志
    let isCancelled = false
    const checkCancellation = () => {
      isCancelled = fileItem.status === UploadStatus.CANCELLED
      return isCancelled
    }

    try {
      const formData = new FormData()
      formData.append("files", fileItem.file)

      // 根据文件大小选择上传方式
      if (fileItem.size > finalConfig.largeFileThreshold) {
        // 大文件分块上传
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
        // 普通文件上传
        await uploadFileApiV2(formData, {
          timeout: finalConfig.timeout,
          onProgress: (progress) => {
            if (!checkCancellation()) {
              fileItem.progress = progress
            }
          }
        })
      }

      // 检查是否被取消
      if (checkCancellation()) {
        return
      }

      fileItem.status = UploadStatus.SUCCESS
      fileItem.progress = 100
      fileItem.uploadedAt = new Date()

      finalConfig.onSuccess(fileItem)
      ElMessage.success(`文件 "${fileItem.name}" 上传成功`)
    } catch (error) {
      // 检查是否被取消
      if (checkCancellation()) {
        return
      }

      fileItem.status = UploadStatus.ERROR
      fileItem.error = error instanceof Error ? error.message : "上传失败"

      finalConfig.onError(fileItem, error instanceof Error ? error : new Error("上传失败"))
      ElMessage.error(`文件 "${fileItem.name}" 上传失败: ${fileItem.error}`)
    } finally {
      uploadingCount.value--
    }
  }

  /**
   * 开始上传
   */
  async function startUpload(): Promise<void> {
    const pendingFiles = uploadQueue.value.filter(item => item.status === UploadStatus.PENDING)

    if (pendingFiles.length === 0) {
      return
    }

    // 控制并发数量
    const uploadPromises: Promise<void>[] = []

    for (const fileItem of pendingFiles) {
      // 等待当前上传数量小于最大并发数
      while (uploadingCount.value >= finalConfig.maxConcurrent) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }

      const uploadPromise = uploadSingleFile(fileItem)
      uploadPromises.push(uploadPromise)
    }

    // 等待所有上传完成
    await Promise.allSettled(uploadPromises)

    // 触发完成回调
    finalConfig.onComplete(uploadQueue.value)
  }

  /**
   * 清空队列
   */
  function clearQueue(): void {
    // 取消所有正在上传的文件
    uploadQueue.value
      .filter(item => item.status === UploadStatus.UPLOADING)
      .forEach(item => cancelFile(item.id))

    uploadQueue.value = []
  }

  /**
   * 清空已完成的文件
   */
  function clearCompleted(): void {
    uploadQueue.value = uploadQueue.value.filter(
      item => item.status !== UploadStatus.SUCCESS && item.status !== UploadStatus.ERROR
    )
  }

  return {
    // 状态
    uploadQueue: readonly(uploadQueue),
    isUploading: readonly(isUploading),
    totalProgress: readonly(totalProgress),
    stats: readonly(stats),

    // 配置
    config: finalConfig,

    // 方法
    addFiles,
    removeFile,
    cancelFile,
    retryFile,
    startUpload,
    clearQueue,
    clearCompleted
  }
}
