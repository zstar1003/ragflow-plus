<script lang="ts" setup>
import type { FormInstance, UploadUserFile } from "element-plus"
import { batchDeleteFilesApi, deleteFileApi, getFileListApi } from "@@/apis/files"
import { UploadStatus, useFileUpload } from "@@/composables/useFileUpload"
import { usePagination } from "@@/composables/usePagination"
import { Delete, Download, Refresh, Search, Upload } from "@element-plus/icons-vue"
import { ElLoading, ElMessage, ElMessageBox } from "element-plus"
import { reactive, ref } from "vue"
import "element-plus/dist/index.css"
import "element-plus/theme-chalk/el-message-box.css"
import "element-plus/theme-chalk/el-message.css"

defineOptions({
  // 命名当前组件
  name: "File"
})

const loading = ref<boolean>(false)
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination()
const uploadDialogVisible = ref(false)
const uploadFileList = ref<UploadUserFile[]>([])

// 使用新的文件上传 composable
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
    // 上传成功后刷新文件列表
    getTableData()
  },
  onComplete: (results) => {
    // 所有文件上传完成
    const successCount = results.filter(item => item.status === UploadStatus.SUCCESS).length
    const errorCount = results.filter(item => item.status === UploadStatus.ERROR).length

    if (errorCount === 0) {
      ElMessage.success(`成功上传 ${successCount} 个文件`)
    } else {
      ElMessage.warning(`上传完成：成功 ${successCount} 个，失败 ${errorCount} 个`)
    }

    // 清理已完成的文件
    setTimeout(() => {
      clearCompleted()
      uploadDialogVisible.value = false
      uploadFileList.value = []
    }, 2000)
  }
})

// 计算上传按钮的加载状态
const uploadLoading = computed(() => isUploading.value)

// 定义文件数据类型
interface FileData {
  id: string
  name: string
  size: number
  type: string
  kb_id: string
  location: string
  create_time?: number
}

// 查询文件列表
const tableData = ref<FileData[]>([])
const searchFormRef = ref<FormInstance | null>(null)
const searchData = reactive({
  name: ""
})

// 排序状态
const sortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc" // 默认排序顺序 (最新创建的在前)
})

// 存储多选的表格数据
const multipleSelection = ref<FileData[]>([])

// 获取文件列表数据
function getTableData() {
  loading.value = true
  // 调用获取文件列表API
  getFileListApi({
    currentPage: paginationData.currentPage,
    size: paginationData.pageSize,
    name: searchData.name,
    sort_by: sortData.sortBy,
    sort_order: sortData.sortOrder
  }).then(({ data }) => {
    paginationData.total = data.total
    tableData.value = data.list
    // 清空选中数据
    multipleSelection.value = []
  }).catch(() => {
    tableData.value = []
  }).finally(() => {
    loading.value = false
  })
}

// 搜索处理
function handleSearch() {
  paginationData.currentPage === 1 ? getTableData() : (paginationData.currentPage = 1)
}

// 重置搜索
function resetSearch() {
  searchFormRef.value?.resetFields()
  handleSearch()
}

// 添加上传方法
function handleUpload() {
  uploadDialogVisible.value = true
}

/**
 * 提交上传
 * 使用新的文件上传系统
 */
function submitUpload() {
  if (uploadFileList.value.length === 0) {
    ElMessage.warning("请选择要上传的文件")
    return
  }

  // 将文件添加到上传队列
  const files = uploadFileList.value.map(file => file.raw).filter(Boolean) as File[]
  addFiles(files)

  // 开始上传
  startUpload()
}

// 下载文件
async function handleDownload(row: FileData) {
  const loadingInstance = ElLoading.service({
    lock: true,
    text: "正在准备下载...",
    background: "rgba(0, 0, 0, 0.7)"
  })

  try {
    console.log(`开始下载文件: ${row.id} ${row.name}`)

    // 直接使用fetch API进行文件下载
    const response = await fetch(`/api/v1/files/${row.id}/download`, {
      method: "GET",
      headers: {
        Accept: "application/octet-stream"
      }
    })

    if (!response.ok) {
      throw new Error(`服务器返回错误: ${response.status} ${response.statusText}`)
    }

    // 获取文件数据
    const blob = await response.blob()

    if (!blob || blob.size === 0) {
      throw new Error("文件内容为空")
    }

    // 创建下载链接
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = row.name

    // 触发下载
    document.body.appendChild(link)
    link.click()

    // 清理资源
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

// 删除文件
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
              getTableData() // 刷新表格数据
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
    // 用户取消删除操作
  })
}

// 批量删除文件
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
              getTableData() // 刷新表格数据
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
    // 用户取消删除操作
  })
}

// 表格多选事件处理
function handleSelectionChange(selection: FileData[]) {
  multipleSelection.value = selection
}

// 格式化文件大小
function formatFileSize(size: number) {
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

/**
 * @description 处理表格排序变化事件（只允许正序和倒序切换）
 * @param {object} sortInfo 排序信息对象，包含 prop 和 order
 * @param {string} sortInfo.prop 排序的字段名
 * @param {string | null} sortInfo.order 排序的顺序 ('ascending', 'descending', null)
 */
function handleSortChange({ prop }: { prop: string, order: string | null }) {
  // 如果点击的是同一个字段，则切换排序顺序
  if (sortData.sortBy === prop) {
    // 当前为正序则切换为倒序，否则切换为正序
    sortData.sortOrder = sortData.sortOrder === "asc" ? "desc" : "asc"
  } else {
    // 切换字段时，默认正序
    sortData.sortBy = prop
    sortData.sortOrder = "asc"
  }
  getTableData()
}

// 监听分页参数的变化
watch([() => paginationData.currentPage, () => paginationData.pageSize], getTableData, { immediate: true })

// 确保页面挂载和激活时获取数据
onMounted(() => {
  getTableData()
})

// 当从其他页面切换回来时刷新数据
onActivated(() => {
  getTableData()
})
</script>

<template>
  <div class="app-container">
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
            @click="handleUpload"
          >
            上传文件
          </el-button>
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
      <!-- 上传对话框 -->
      <el-dialog
        v-model="uploadDialogVisible"
        title="上传文件"
        width="30%"
      >
        <el-upload
          v-model:file-list="uploadFileList"
          multiple
          :auto-upload="false"
          drag
        >
          <el-icon class="el-icon--upload">
            <Upload />
          </el-icon>
          <div class="el-upload__text">
            拖拽文件到此处或<em>点击上传</em>
          </div>
        </el-upload>

        <!-- 上传进度显示 -->
        <div v-if="uploadQueue.length > 0" class="upload-progress-section">
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
                <span class="file-name">{{ fileItem.name }}</span>
                <span class="file-size">({{ formatFileSize(fileItem.size) }})</span>
              </div>
              <div class="file-progress">
                <el-progress
                  :percentage="fileItem.progress"
                  :status="fileItem.status === 'success' ? 'success' : fileItem.status === 'error' ? 'exception' : undefined"
                  :show-text="false"
                  :stroke-width="4"
                />
                <span class="progress-text">{{ fileItem.progress }}%</span>
              </div>
              <div class="file-actions">
                <el-button
                  v-if="fileItem.status === 'error'"
                  type="primary"
                  size="small"
                  text
                  @click="retryFile(fileItem.id)"
                >
                  重试
                </el-button>
                <el-button
                  v-if="fileItem.status !== 'uploading'"
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
          <el-button @click="uploadDialogVisible = false">
            取消
          </el-button>
          <el-button
            type="primary"
            :loading="uploadLoading"
            :disabled="uploadFileList.length === 0"
            @click="submitUpload"
          >
            {{ uploadLoading ? '上传中...' : '确认上传' }}
          </el-button>
        </template>
      </el-dialog>
      <div class="table-wrapper">
        <el-table :data="tableData" @selection-change="handleSelectionChange" @sort-change="handleSortChange">
          <el-table-column type="selection" width="50" align="center" />
          <el-table-column label="序号" align="center" width="80">
            <template #default="scope">
              {{ (paginationData.currentPage - 1) * paginationData.pageSize + scope.$index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="name" label="文档名" align="center" sortable="custom" />
          <el-table-column label="大小" align="center" width="120" sortable="custom">
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
</style>

<style>
/* 全局样式 - 确保弹窗样式正确 */
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

  .el-button {
    margin-right: 10px;
  }
}

.upload-dialog {
  .el-upload-dragger {
    width: 100%;
    padding: 20px;
  }
}

/* 上传进度相关样式 */
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
}

.upload-file-list {
  max-height: 300px;
  overflow-y: auto;
}

.upload-file-item {
  display: flex;
  align-items: center;
  padding: 10px;
  margin-bottom: 8px;
  background-color: white;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
  transition: all 0.3s;
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
  background-color: #f0f9ff;
}

.upload-file-item.status-error {
  border-color: #f56c6c;
  background-color: #fef0f0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-weight: 500;
  color: #303133;
  margin-right: 8px;
}

.file-size {
  color: #909399;
  font-size: 12px;
}

.file-progress {
  flex: 0 0 200px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 15px;
}

.progress-text {
  font-size: 12px;
  color: #606266;
  min-width: 35px;
}

.file-actions {
  flex: 0 0 auto;
  display: flex;
  gap: 5px;
}
</style>
