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
      ElMessage.success(`成功上传 ${successCount} 个文件`)
    } else {
      ElMessage.warning(`上传完成：成功 ${successCount} 个，失败 ${errorCount} 个`)
    }

    setTimeout(() => {
      clearCompleted()
      uploadDialogVisible.value = false
      uploadFileList.value = []
    }, 2000)
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
    ElMessage.warning("请选择要上传的文件或文件夹")
    return
  }

  const filesToUpload = uploadFileList.value.map(uf => uf.raw as File).filter(Boolean)
  if (filesToUpload.length > 0) {
    addFiles(filesToUpload)
    startUpload()
  } else {
    ElMessage.warning("没有有效的文件可上传")
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
        console.warn(`Skipping placeholder file: ${fileName}`)
        continue
      }
      if (file.size === 0 && !file.type) {
        console.warn(`Skipping zero-byte file with no type: ${fileName}`)
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
    // Append new files instead of overwriting, in case some files were already selected via el-upload
    uploadFileList.value = [...uploadFileList.value, ...newUploadUserFiles]
    if (!uploadDialogVisible.value && newUploadUserFiles.length > 0) {
      uploadDialogVisible.value = true // Open dialog if not already open
    }
  }

  if (input) {
    input.value = ""
  }
}

async function handleDownload(row: FileData) {
  const loadingInstance = ElLoading.service({
    lock: true,
    text: "正在准备下载...",
    background: "rgba(0, 0, 0, 0.7)"
  })

  try {
    console.log(`开始下载文件: ${row.id} ${row.name}`)

    const response = await fetch(`/api/v1/files/${row.id}/download`, {
      method: "GET",
      headers: {
        Accept: "application/octet-stream"
      }
    })

    if (!response.ok) {
      throw new Error(`服务器返回错误: ${response.status} ${response.statusText}`)
    }
    const blob = await response.blob()

    if (!blob || blob.size === 0) {
      throw new Error("文件内容为空")
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
      ElMessage.success(`文件 "${row.name}" 下载成功`)
    }, 100)
  } catch (error: any) {
    console.error("下载文件时发生错误:", error)
    ElMessage.error(`文件下载失败: ${error?.message || "未知错误"}`)
  } finally {
    loadingInstance.close()
  }
}

function handleDelete(row: FileData) {
  ElMessageBox.confirm(
    `确定要删除文件 "${row.name}" 吗？`,
    "删除确认",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
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
          instance.confirmButtonText = "删除中..."

          loading.value = true
          deleteFileApi(row.id)
            .then(() => {
              ElMessage.success("删除成功")
              getTableData()
              done()
            })
            .catch((error) => {
              ElMessage.error(`删除失败: ${error?.message || "未知错误"}`)
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
    ElMessage.warning("请至少选择一个文件")
    return
  }

  ElMessageBox.confirm(
    `确定要删除选中的 <strong>${multipleSelection.value.length}</strong> 个文件吗？<br><span style="color: #F56C6C; font-size: 12px;">此操作不可恢复</span>`,
    "批量删除确认",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
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
          instance.confirmButtonText = "删除中..."

          loading.value = true
          const ids = multipleSelection.value.map(item => item.id)
          batchDeleteFilesApi(ids)
            .then(() => {
              ElMessage.success(`成功删除 ${multipleSelection.value.length} 个文件`)
              getTableData()
              done()
            })
            .catch((error) => {
              ElMessage.error(`批量删除失败: ${error?.message || "未知错误"}`)
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
  // When files are added/removed via el-upload's UI (drag & drop, or its own "click to select")
  // its internal list `newFileList` will be up-to-date.
  // We directly assign it to keep our `uploadFileList` in sync.
  uploadFileList.value = newFileList
}
// on-remove is also covered by on-change in el-plus for v-model:file-list
// function handleElUploadRemove(_file: UploadUserFile, newFileList: UploadUserFile[]) {
//   uploadFileList.value = newFileList
// }

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
        <el-form-item prop="name" label="文件名">
          <el-input v-model="searchData.name" placeholder="请输入" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">
            搜索
          </el-button>
          <el-button :icon="Refresh" @click="resetSearch">
            重置
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
            上传文件
          </el-button>
          <!-- Removed separate "Upload Folder" button from toolbar -->
          <el-button
            type="danger"
            :icon="Delete"
            :disabled="multipleSelection.length === 0"
            @click="handleBatchDelete"
          >
            批量删除
          </el-button>
        </div>
      </div>
      <el-dialog
        v-model="uploadDialogVisible"
        title="上传文件或文件夹"
        width="50%"
        @close="closeUploadDialog"
      >
        <el-alert
          v-if="uploadFileList.length === 0 && !isUploading"
          title="请选择文件或整个文件夹"
          type="info"
          show-icon
          :closable="false"
          description="您可以通过下方区域拖拽文件、点击选择文件，或点击提示中的链接来选择整个文件夹进行上传。"
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
            拖拽文件到此处或<em>点击选择文件</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              若要上传整个文件夹，请 <el-link type="primary" :icon="FolderAdd" @click.stop="triggerFolderUpload">
                点击此处选择文件夹
              </el-link>
              <span v-if="uploadFileList.length > 0">当前已选择 {{ uploadFileList.length }} 个项目。</span>
            </div>
          </template>
        </el-upload>

        <div v-if="uploadQueue.length > 0 || isUploading" class="upload-progress-section">
          <div class="upload-stats">
            <span>总进度: {{ totalProgress }}%</span>
            <span>成功: {{ stats.success }}</span>
            <span>失败: {{ stats.error }}</span>
            <span>等待: {{ stats.pending }}</span>
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
                  重试
                </el-button>
                <el-button
                  v-if="fileItem.status !== UploadStatus.UPLOADING"
                  type="danger"
                  size="small"
                  text
                  @click="removeFile(fileItem.id)"
                >
                  移除
                </el-button>
              </div>
            </div>
          </div>
        </div>
        <template #footer>
          <el-button @click="closeUploadDialog">
            取消
          </el-button>
          <el-button
            type="primary"
            :loading="uploadLoading"
            :disabled="uploadFileList.length === 0 || isUploading"
            @click="submitUpload"
          >
            {{ uploadLoading ? '上传中...' : (uploadFileList.length > 0 ? `确认上传 ${uploadFileList.length} 项` : '确认上传') }}
          </el-button>
        </template>
      </el-dialog>
      <div class="table-wrapper">
        <el-table :data="tableData" @selection-change="handleSelectionChange" @sort-change="handleSortChange">
          >
          <el-table-column type="selection" width="50" align="center" />
          <el-table-column label="序号" align="center" width="80">
            <template #default="scope">
              {{ (paginationData.currentPage - 1) * paginationData.pageSize + scope.$index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="name" label="文档名" align="center" sortable="custom" show-overflow-tooltip />
          <el-table-column label="大小" align="center" width="120" sortable="custom" prop="size">
            <template #default="scope">
              {{ formatFileSize(scope.row.size) }}
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" align="center" width="120" sortable="custom" />
          <el-table-column prop="create_date" label="创建时间" align="center" width="180" sortable="custom" />
          <el-table-column fixed="right" label="操作" width="180" align="center">
            <template #default="scope">
              <el-button type="primary" text bg size="small" :icon="Download" @click="handleDownload(scope.row)">
                下载
              </el-button>
              <el-button type="danger" text bg size="small" :icon="Delete" @click="handleDelete(scope.row)">
                删除
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
