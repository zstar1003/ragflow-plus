<script lang="ts" setup>
import type { FormInstance, UploadUserFile } from "element-plus"
import { batchDeleteFilesApi, deleteFileApi, getFileListApi, uploadFileApi } from "@@/apis/files"
import { usePagination } from "@@/composables/usePagination"
import { Delete, Download, Refresh, Search, Upload } from "@element-plus/icons-vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { ref } from "vue"
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
const uploadLoading = ref(false)

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

// 存储多选的表格数据
const multipleSelection = ref<FileData[]>([])

// 获取文件列表数据
function getTableData() {
  loading.value = true
  // 调用获取文件列表API
  getFileListApi({
    currentPage: paginationData.currentPage,
    size: paginationData.pageSize,
    name: searchData.name
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

async function submitUpload() {
  uploadLoading.value = true
  try {
    const formData = new FormData()
    uploadFileList.value.forEach((file) => {
      if (file.raw) {
        formData.append("files", file.raw)
      }
    })

    await uploadFileApi(formData)
    ElMessage.success("文件上传成功")
    getTableData()
    uploadDialogVisible.value = false
    uploadFileList.value = []
  } catch (error: unknown) {
    let errorMessage = "上传失败"
    if (error instanceof Error) {
      errorMessage += `: ${error.message}`
    }
    ElMessage.error(errorMessage)
  } finally {
    uploadLoading.value = false
  }
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
        <template #footer>
          <el-button @click="uploadDialogVisible = false">
            取消
          </el-button>
          <el-button
            type="primary"
            :loading="uploadLoading"
            @click="submitUpload"
          >
            确认上传
          </el-button>
        </template>
      </el-dialog>
      <div class="table-wrapper">
        <el-table :data="tableData" @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="50" align="center" />
          <el-table-column label="序号" align="center" width="80">
            <template #default="scope">
              {{ (paginationData.currentPage - 1) * paginationData.pageSize + scope.$index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="name" label="文档名" align="center" />
          <el-table-column label="大小" align="center" width="120">
            <template #default="scope">
              {{ formatFileSize(scope.row.size) }}
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" align="center" width="120" />
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
</style>
