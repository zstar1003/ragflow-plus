<script lang="ts" setup>
import type { FormInstance, UploadRawFile, UploadUserFile } from "element-plus"
import { batchDeleteFilesApi, deleteFileApi, getFileListApi } from "@@/apis/files"
import { UploadStatus, useFileUpload } from "@@/composables/useFileUpload"
import { usePagination } from "@@/composables/usePagination"
import { Delete, Download, FolderAdd, Refresh, Search, Upload } from "@element-plus/icons-vue"
import { ElLoading, ElMessage, ElMessageBox } from "element-plus"
import { computed, onActivated, onMounted, reactive, ref, watch } from "vue"
import "element-plus/dist/index.css"
import "element-plus/theme-chalk/el-message-box.css"
import "element-plus/theme-chalk/el-message.css"

defineOptions({
  name: "File"
})

const loading = ref<boolean>(false)
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination()
const uploadDialogVisible = ref(false)
const uploadFileList = ref<UploadUserFile[]>([])
const folderInputRef = ref<HTMLInputElement | null>(null)

const {
  uploadQueue,
  isUploading,
  totalProgress,
  stats,
  addFiles,
  removeFile,
  retryFile,
  startUpload,
  clearCompleted
} = useFileUpload({
  autoUpload: false,
  maxConcurrent: 2,
  onSuccess: () => {
    getTableData()
  },
  onComplete: (results) => {
    const successCount = results.filter(item => item.status === UploadStatus.SUCCESS).length
    const errorCount = results.filter(item => item.status === UploadStatus.ERROR).length

    if (errorCount === 0) {
      ElMessage.success(`${successCount}개 파일 업로드 성공`)
    } else {
      ElMessage.warning(`업로드 완료: 성공 ${successCount}개, 실패 ${errorCount}개`)
    }

    setTimeout(() => {
      clearCompleted()
      uploadDialogVisible.value = false
      uploadFileList.value = []
    }, 200)
  }
})

const uploadLoading = computed(() => isUploading.value)

interface FileData {
  id: string
  name: string
  size: number
  type: string
  kb_id: string
  location: string
  create_time?: number
}

const tableData = ref<FileData[]>([])
const searchFormRef = ref<FormInstance | null>(null)
const searchData = reactive({
  name: ""
})

const sortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc"
})

const multipleSelection = ref<FileData[]>([])

function getTableData() {
  loading.value = true
  getFileListApi({
    currentPage: paginationData.currentPage,
    size: paginationData.pageSize,
    name: searchData.name,
    sort_by: sortData.sortBy,
    sort_order: sortData.sortOrder
  }).then(({ data }) => {
    paginationData.total = data.total
    tableData.value = data.list
    multipleSelection.value = []
  }).catch(() => {
    tableData.value = []
  }).finally(() => {
    loading.value = false
  })
}

function handleSearch() {
  if (paginationData.currentPage === 1) {
    getTableData()
  } else {
    paginationData.currentPage = 1
  }
}

function resetSearch() {
  searchFormRef.value?.resetFields()
  handleSearch()
}

function openUploadDialog() {
  uploadDialogVisible.value = true
}

function submitUpload() {
  if (uploadFileList.value.length === 0) {
    ElMessage.warning("업로드할 파일이나 폴더를 선택해주세요")
    return
  }

  const filesToUpload = uploadFileList.value.map(uf => uf.raw as File).filter(Boolean)
  if (filesToUpload.length > 0) {
    addFiles(filesToUpload)
    startUpload()
  } else {
    ElMessage.warning("업로드할 유효한 파일이 없습니다")
  }
}

function triggerFolderUpload() {
  folderInputRef.value?.click()
}

function handleFolderFilesSelected(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    const newUploadUserFiles: UploadUserFile[] = []
    for (let i = 0; i < input.files.length; i++) {
      const file = input.files[i] as File
      const fileName = (file as any).webkitRelativePath || file.name

      if (file.name === ".DS_Store" || (file.name.startsWith("._") && file.size === 4096)) {
        console.warn(`플레이스홀더 파일 건너뛰기: ${fileName}`)
        continue
      }
      if (file.size === 0 && !file.type) {
        console.warn(`타입이 없는 0바이트 파일 건너뛰기: ${fileName}`)
        continue
      }
      const fileWithUid = file as UploadRawFile
      fileWithUid.uid = Date.now() + Math.random() * 1000 + i

      const uploadUserFile: UploadUserFile = {
        name: fileName,
        raw: fileWithUid,
        size: file.size,
        uid: fileWithUid.uid,
        status: "ready"
      }
      newUploadUserFiles.push(uploadUserFile)
    }
    uploadFileList.value = [...uploadFileList.value, ...newUploadUserFiles]
    if (!uploadDialogVisible.value && newUploadUserFiles.length > 0) {
      uploadDialogVisible.value = true
    }
  }

  if (input) {
    input.value = ""
  }
}

async function handleDownload(row: FileData) {
  const loadingInstance = ElLoading.service({
    lock: true,
    text: "다운로드 준비 중...",
    background: "rgba(0, 0, 0, 0.7)"
  })

  try {
    console.log(`파일 다운로드 시작: ${row.id} ${row.name}`)

    const response = await fetch(`/api/v1/files/${row.id}/download`, {
      method: "GET",
      headers: {
        Accept: "application/octet-stream"
      }
    })

    if (!response.ok) {
      throw new Error(`서버 오류 반환: ${response.status} ${response.statusText}`)
    }
    const blob = await response.blob()

    if (!blob || blob.size === 0) {
      throw new Error("파일 내용이 비어있습니다")
    }
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = row.name

    document.body.appendChild(link)
    link.click()

    setTimeout(() => {
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      ElMessage.success(`파일 "${row.name}" 다운로드 성공`)
    }, 100)
  } catch (error: any) {
    console.error("파일 다운로드 중 오류 발생:", error)
    ElMessage.error(`파일 다운로드 실패: ${error?.message || "알 수 없는 오류"}`)
  } finally {
    loadingInstance.close()
  }
}

function handleDelete(row: FileData) {
  ElMessageBox.confirm(
    `파일 "${row.name}"을(를) 삭제하시겠습니까?`,
    "삭제 확인",
    {
      confirmButtonText: "확인",
      cancelButtonText: "취소",
      type: "warning",
      dangerouslyUseHTMLString: true,
      center: true,
      customClass: "delete-confirm-dialog",
      distinguishCancelAndClose: true,
      showClose: false,
      closeOnClickModal: false,
      closeOnPressEscape: true,
      roundButton: true,
      beforeClose: (action, instance, done) => {
        if (action === "confirm") {
          instance.confirmButtonLoading = true
          instance.confirmButtonText = "삭제 중..."

          loading.value = true
          deleteFileApi(row.id)
            .then(() => {
              ElMessage.success("삭제 성공")
              getTableData()
              done()
            })
            .catch((error) => {
              ElMessage.error(`삭제 실패: ${error?.message || "알 수 없는 오류"}`)
              done()
            })
            .finally(() => {
              instance.confirmButtonLoading = false
              loading.value = false
            })
        } else {
          done()
        }
      }
    }
  ).catch(() => {
    // User cancelled delete
  })
}

function handleBatchDelete() {
  if (multipleSelection.value.length === 0) {
    ElMessage.warning("최소 하나의 파일을 선택해주세요")
    return
  }

  ElMessageBox.confirm(
    `선택한 <strong>${multipleSelection.value.length}</strong>개 파일을 삭제하시겠습니까?<br><span style="color: #F56C6C; font-size: 12px;">이 작업은 되돌릴 수 없습니다</span>`,
    "일괄 삭제 확인",
    {
      confirmButtonText: "확인",
      cancelButtonText: "취소",
      type: "warning",
      dangerouslyUseHTMLString: true,
      center: true,
      customClass: "delete-confirm-dialog",
      distinguishCancelAndClose: true,
      showClose: false,
      closeOnClickModal: false,
      closeOnPressEscape: true,
      roundButton: true,
      beforeClose: (action, instance, done) => {
        if (action === "confirm") {
          instance.confirmButtonLoading = true
          instance.confirmButtonText = "삭제 중..."

          loading.value = true
          const ids = multipleSelection.value.map(item => item.id)
          batchDeleteFilesApi(ids)
            .then(() => {
              ElMessage.success(`${multipleSelection.value.length}개 파일 삭제 성공`)
              getTableData()
              done()
            })
            .catch((error) => {
              ElMessage.error(`일괄 삭제 실패: ${error?.message || "알 수 없는 오류"}`)
              done()
            })
            .finally(() => {
              instance.confirmButtonLoading = false
              loading.value = false
            })
        } else {
          done()
        }
      }
    }
  ).catch(() => {
    // User cancelled delete
  })
}

function handleSelectionChange(selection: FileData[]) {
  multipleSelection.value = selection
}

function formatFileSize(size: number) {
  if (size === undefined || size === null) {
    return "N/A"
  }
  if (size < 1024) {
    return `${size} B`
  } else if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(2)} KB`
  } else if (size < 1024 * 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(2)} MB`
  } else {
    return `${(size / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }
}

function handleSortChange({ prop }: { prop: string, order: string | null }) {
  if (sortData.sortBy === prop) {
    sortData.sortOrder = sortData.sortOrder === "asc" ? "desc" : "asc"
  } else {
    sortData.sortBy = prop
    sortData.sortOrder = "asc"
  }
  getTableData()
}

watch([() => paginationData.currentPage, () => paginationData.pageSize], getTableData, { immediate: true })

onMounted(() => {
  getTableData()
})

onActivated(() => {
  getTableData()
})

function handleElUploadChange(_file: UploadUserFile, newFileList: UploadUserFile[]) {
  uploadFileList.value = newFileList
}

function closeUploadDialog() {
  uploadDialogVisible.value = false
  uploadFileList.value = []
}
</script>

<template>
  <div class="app-container">
    <input
      ref="folderInputRef"
      type="file"
      webkitdirectory
      directory
      multiple
      style="display: none"
      @change="handleFolderFilesSelected"
    >

    <el-card v-loading="loading" shadow="never" class="search-wrapper">
      <el-form ref="searchFormRef" :inline="true" :model="searchData">
        <el-form-item prop="name" label="파일명">
          <el-input v-model="searchData.name" placeholder="입력해주세요" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">
            검색
          </el-button>
          <el-button :icon="Refresh" @click="resetSearch">
            초기화
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    <el-card v-loading="loading" shadow="never">
      <div class="toolbar-wrapper">
        <div>
          <el-button
            type="primary"
            :icon="Upload"
            @click="openUploadDialog"
          >
            파일 업로드
          </el-button>
          <!-- Removed separate "Upload Folder" button from toolbar -->
          <el-button
            type="danger"
            :icon="Delete"
            :disabled="multipleSelection.length === 0"
            @click="handleBatchDelete"
          >
            일괄 삭제
          </el-button>
        </div>
      </div>
      <el-dialog
        v-model="uploadDialogVisible"
        title="파일 또는 폴더 업로드"
        width="50%"
        @close="closeUploadDialog"
      >
        <el-alert
          v-if="uploadFileList.length === 0 && !isUploading"
          title="파일 또는 전체 폴더를 선택해주세요"
          type="info"
          show-icon
          :closable="false"
          description="아래 영역에 파일을 드래그하거나, 파일 선택을 클릭하거나, 힌트의 링크를 클릭하여 전체 폴더를 선택해 업로드할 수 있습니다."
          style="margin-bottom: 20px;"
        />

        <el-upload
          v-if="!isUploading"
          v-model:file-list="uploadFileList"
          multiple
          :auto-upload="false"
          drag
          action="#"
          :on-change="handleElUploadChange"
          :on-remove="handleElUploadChange"
        >
          <el-icon class="el-icon--upload">
            <Upload />
          </el-icon>
          <div class="el-upload__text">
            여기에 파일을 드래그하거나 <em>클릭하여 파일 선택</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              전체 폴더를 업로드하려면 <el-link type="primary" :icon="FolderAdd" @click.stop="triggerFolderUpload">
                여기를 클릭하여 폴더 선택
              </el-link>
              <span v-if="uploadFileList.length > 0">현재 {{ uploadFileList.length }}개 항목이 선택되었습니다.</span>
            </div>
          </template>
        </el-upload>

        <div v-if="uploadQueue.length > 0 || isUploading" class="upload-progress-section">
          <div class="upload-stats">
            <span>전체 진행률: {{ totalProgress }}%</span>
            <span>성공: {{ stats.success }}</span>
            <span>실패: {{ stats.error }}</span>
            <span>대기: {{ stats.pending }}</span>
          </div>

          <div class="upload-file-list">
            <div
              v-for="fileItem in uploadQueue"
              :key="fileItem.id"
              class="upload-file-item"
              :class="`status-${fileItem.status}`"
            >
              <div class="file-info">
                <span class="file-name" :title="fileItem.name">{{ fileItem.name }}</span>
                <span class="file-size">({{ formatFileSize(fileItem.size) }})</span>
              </div>
              <div class="file-progress">
                <el-progress
                  :percentage="fileItem.progress"
                  :status="fileItem.status === UploadStatus.SUCCESS ? 'success' : fileItem.status === UploadStatus.ERROR ? 'exception' : undefined"
                  :color="fileItem.status === UploadStatus.UPLOADING ? '#409eff' : undefined"
                  :show-text="false"
                  :stroke-width="4"
                />
                <span class="progress-text">{{ fileItem.progress }}%</span>
              </div>
              <div class="file-actions">
                <el-button
                  v-if="fileItem.status === UploadStatus.ERROR"
                  type="primary"
                  size="small"
                  text
                  @click="retryFile(fileItem.id)"
                >
                  재시도
                </el-button>
                <el-button
                  v-if="fileItem.status !== UploadStatus.UPLOADING"
                  type="danger"
                  size="small"
                  text
                  @click="removeFile(fileItem.id)"
                >
                  제거
                </el-button>
              </div>
            </div>
          </div>
        </div>
        <template #footer>
          <el-button @click="closeUploadDialog">
            취소
          </el-button>
          <el-button
            type="primary"
            :loading="uploadLoading"
            :disabled="uploadFileList.length === 0 || isUploading"
            @click="submitUpload"
          >
            {{ uploadLoading ? '업로드 중...' : (uploadFileList.length > 0 ? `${uploadFileList.length}개 항목 업로드 확인` : '업로드 확인') }}
          </el-button>
        </template>
      </el-dialog>
      <div class="table-wrapper">
        <el-table :data="tableData" @selection-change="handleSelectionChange" @sort-change="handleSortChange">
          >
          <el-table-column type="selection" width="50" align="center" />
          <el-table-column label="번호" align="center" width="80">
            <template #default="scope">
              {{ (paginationData.currentPage - 1) * paginationData.pageSize + scope.$index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="name" label="문서명" align="center" sortable="custom" show-overflow-tooltip />
          <el-table-column label="크기" align="center" width="120" sortable="custom" prop="size">
            <template #default="scope">
              {{ formatFileSize(scope.row.size) }}
            </template>
          </el-table-column>
          <el-table-column prop="type" label="유형" align="center" width="120" sortable="custom" />
          <el-table-column prop="create_date" label="생성 시간" align="center" width="180" sortable="custom" />
          <el-table-column fixed="right" label="작업" width="180" align="center">
            <template #default="scope">
              <el-button type="primary" text bg size="small" :icon="Download" @click="handleDownload(scope.row)">
                다운로드
              </el-button>
              <el-button type="danger" text bg size="small" :icon="Delete" @click="handleDelete(scope.row)">
                삭제
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="pager-wrapper">
        <el-pagination
          background
          :layout="paginationData.layout"
          :page-sizes="paginationData.pageSizes"
          :total="paginationData.total"
          :page-size="paginationData.pageSize"
          :current-page="paginationData.currentPage"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style lang="scss" scoped>
.el-alert {
  margin-bottom: 20px;
}

.search-wrapper {
  margin-bottom: 20px;
  :deep(.el-card__body) {
    padding-bottom: 2px;
  }
}

.toolbar-wrapper {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.table-wrapper {
  margin-bottom: 20px;
}

.pager-wrapper {
  display: flex;
  justify-content: flex-end;
}

.el-upload__tip {
  margin-top: 10px; // Increased margin for better spacing
  line-height: 1.6; // Improved line height
  font-size: 13px; // Slightly larger font for tip
  color: #606266;

  .el-link {
    // Style for the folder upload link
    font-size: inherit; // Inherit font size from parent
    vertical-align: baseline; // Align with surrounding text
    margin: 0 2px; // Small horizontal margin
  }
}

.upload-progress-section {
  margin-top: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.upload-stats {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
  font-size: 14px;
  color: #606266;
  flex-wrap: wrap;
}

.upload-file-list {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #eee;
  padding: 5px;
  border-radius: 4px;
}

.upload-file-item {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  margin-bottom: 8px;
  background-color: white;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
  transition: all 0.3s;
  font-size: 13px;
}

.upload-file-item:last-child {
  margin-bottom: 0;
}

.upload-file-item.status-uploading {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.upload-file-item.status-success {
  border-color: #67c23a;
  background-color: #f0f9eb;
}

.upload-file-item.status-error {
  border-color: #f56c6c;
  background-color: #fef0f0;
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.file-name {
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
  line-height: 1.4;
}

.file-size {
  color: #909399;
  font-size: 11px;
  line-height: 1.2;
}

.file-progress {
  flex: 0 0 150px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 10px;
}
.file-progress .el-progress {
  flex-grow: 1;
}

.progress-text {
  font-size: 11px;
  color: #606266;
  min-width: 30px;
  text-align: right;
}

.file-actions {
  flex: 0 0 auto;
  display: flex;
  gap: 5px;
}
.file-actions .el-button {
  padding: 4px 8px;
}
</style>

<style>
/* Global styles from original, ensure they are present */
.el-message-box {
  max-width: 500px !important;
  width: auto !important;
  min-width: 420px;
  border-radius: 8px;
  overflow: visible;
}
.delete-confirm-dialog {
  max-width: 500px !important;
  width: auto !important;
  min-width: 420px;
  border-radius: 8px;
  overflow: visible;
}

.delete-confirm-dialog .el-message-box__header {
  padding: 15px 20px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #ebeef5;
  border-radius: 8px 8px 0 0;
}

.delete-confirm-dialog .el-message-box__title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.delete-confirm-dialog .el-message-box__content {
  padding: 20px;
  max-height: 300px;
  overflow-y: auto;
  word-break: break-word;
}

.delete-confirm-dialog .el-message-box__message {
  font-size: 16px;
  line-height: 1.6;
  color: #606266;
  padding: 0;
  margin: 0;
  word-wrap: break-word;
}

.delete-confirm-dialog .el-message-box__message p {
  margin: 0;
  padding: 0;
}

.delete-confirm-dialog .el-message-box__btns {
  padding: 12px 20px;
  border-top: 1px solid #ebeef5;
  border-radius: 0 0 8px 8px;
  background-color: #f8f9fa;
}

.delete-confirm-dialog .el-button {
  padding: 9px 20px;
  font-size: 14px;
  border-radius: 4px;
  transition: all 0.3s;
}

.delete-confirm-dialog .el-button--primary {
  background-color: #f56c6c;
  border-color: #f56c6c;
}

.delete-confirm-dialog .el-button--primary:hover,
.delete-confirm-dialog .el-button--primary:focus {
  background-color: #f78989;
  border-color: #f78989;
}

.delete-confirm-dialog .el-message-box__status {
  display: none !important;
}

.toolbar-wrapper {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.toolbar-wrapper .el-button {
  margin-right: 10px;
}
.toolbar-wrapper .el-button:last-child {
  margin-right: 0;
}

.upload-dialog .el-upload-dragger {
  width: 100%;
  padding: 20px;
}
</style>
