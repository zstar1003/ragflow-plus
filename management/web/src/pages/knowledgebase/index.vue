<script lang="ts" setup>
import type { FormInstance } from "element-plus"
import DocumentParseProgress from "@/layouts/components/DocumentParseProgress/index.vue"
import {
  deleteDocumentApi,
  getDocumentListApi,
  getFileListApi,
  runDocumentParseApi
} from "@@/apis/kbs/document"
import {
  batchDeleteKnowledgeBaseApi,
  createKnowledgeBaseApi,
  deleteKnowledgeBaseApi,
  getKnowledgeBaseListApi
} from "@@/apis/kbs/knowledgebase"
import { usePagination } from "@@/composables/usePagination"
import { CaretRight, Delete, Plus, Refresh, Search, View } from "@element-plus/icons-vue"
import axios from "axios"
import { ElMessage, ElMessageBox } from "element-plus"
import { onActivated, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue"
import "element-plus/dist/index.css"
import "element-plus/theme-chalk/el-message-box.css"
import "element-plus/theme-chalk/el-message.css"

defineOptions({
  // 命名当前组件
  name: "KnowledgeBase"
})

const loading = ref<boolean>(false)
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination()
const createDialogVisible = ref(false)
const uploadLoading = ref(false)
const showParseProgress = ref(false)
const currentDocId = ref("")

// 添加清理函数
function cleanupResources() {
  // 重置所有状态
  if (multipleSelection.value) {
    multipleSelection.value = []
  }

  loading.value = false
  documentLoading.value = false
  fileLoading.value = false
  uploadLoading.value = false

  // 关闭所有对话框
  viewDialogVisible.value = false
  createDialogVisible.value = false
  addDocumentDialogVisible.value = false
  showParseProgress.value = false
}

// 在组件停用时清理资源
onDeactivated(() => {
  cleanupResources()
})

// 在组件卸载前清理资源
onBeforeUnmount(() => {
  cleanupResources()
})

// 定义知识库数据类型
interface KnowledgeBaseData {
  id: string
  name: string
  description: string
  doc_num: number
  create_time: number
  create_date: string
  avatar?: string
  language: string
  permission: string
  chunk_num: number
  token_num: number
}

// 新建知识库表单
const knowledgeBaseForm = reactive({
  name: "",
  description: "",
  language: "Chinese",
  permission: "me"
})

// 定义API返回数据的接口
interface FileListResponse {
  list: any[]
  total: number
}

interface ApiResponse<T> {
  data: T
  code: number
  message: string
}

interface ListResponse {
  list: any[]
  total: number
}

// 表单验证规则
const knowledgeBaseFormRules = {
  name: [
    { required: true, message: "请输入知识库名称", trigger: "blur" },
    { min: 2, max: 50, message: "长度在 2 到 50 个字符", trigger: "blur" }
  ],
  description: [
    { max: 200, message: "描述不能超过200个字符", trigger: "blur" }
  ]
}

const knowledgeBaseFormRef = ref<FormInstance | null>(null)

// 查询知识库列表
const tableData = ref<KnowledgeBaseData[]>([])
const searchFormRef = ref<FormInstance | null>(null)
const searchData = reactive({
  name: ""
})

// 存储多选的表格数据
const multipleSelection = ref<KnowledgeBaseData[]>([])

// 获取知识库列表数据
function getTableData() {
  loading.value = true
  // 调用获取知识库列表API
  getKnowledgeBaseListApi({
    currentPage: paginationData.currentPage,
    size: paginationData.pageSize,
    name: searchData.name
  }).then((response) => {
    const result = response as ApiResponse<ListResponse>
    paginationData.total = result.data.total
    tableData.value = result.data.list
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

// 打开新建知识库对话框
function handleCreate() {
  createDialogVisible.value = true
}

// 提交新建知识库
async function submitCreate() {
  if (!knowledgeBaseFormRef.value) return

  await knowledgeBaseFormRef.value.validate(async (valid) => {
    if (valid) {
      uploadLoading.value = true
      try {
        await createKnowledgeBaseApi(knowledgeBaseForm)
        ElMessage.success("知识库创建成功")
        getTableData()
        createDialogVisible.value = false
        // 重置表单
        knowledgeBaseFormRef.value?.resetFields()
      } catch (error: unknown) {
        let errorMessage = "创建失败"
        if (error instanceof Error) {
          errorMessage += `: ${error.message}`
        }
        ElMessage.error(errorMessage)
      } finally {
        uploadLoading.value = false
      }
    }
  })
}

// 查看知识库详情
const viewDialogVisible = ref(false)
const currentKnowledgeBase = ref<KnowledgeBaseData | null>(null)
const documentLoading = ref(false)
const documentList = ref<any[]>([])

// 文档列表分页
const docPaginationData = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0,
  pageSizes: [10, 20, 50, 100],
  layout: "total, sizes, prev, pager, next, jumper"
})

// 处理文档分页变化
function handleDocCurrentChange(page: number) {
  docPaginationData.currentPage = page
  getDocumentList()
}

function handleDocSizeChange(size: number) {
  docPaginationData.pageSize = size
  docPaginationData.currentPage = 1
  getDocumentList()
}

// 获取知识库下的文档列表
function getDocumentList() {
  if (!currentKnowledgeBase.value) return

  documentLoading.value = true
  getDocumentListApi({
    kb_id: currentKnowledgeBase.value.id,
    currentPage: docPaginationData.currentPage,
    size: docPaginationData.pageSize,
    name: ""
  }).then((response) => {
    const result = response as ApiResponse<ListResponse>
    documentList.value = result.data.list
    docPaginationData.total = result.data.total
  }).catch((error) => {
    ElMessage.error(`获取文档列表失败: ${error?.message || "未知错误"}`)
    documentList.value = []
  }).finally(() => {
    documentLoading.value = false
  })
}

// 修改handleView方法
function handleView(row: KnowledgeBaseData) {
  currentKnowledgeBase.value = row
  viewDialogVisible.value = true
  // 重置文档分页
  docPaginationData.currentPage = 1
  // 获取文档列表
  getDocumentList()
}

// 格式化解析状态
function formatParseStatus(progress: number) {
  if (progress === 0) return "未解析"
  if (progress === 1) return "已完成"
  return `解析中 ${Math.floor(progress * 100)}%`
}

// 获取解析状态对应的标签类型
function getParseStatusType(progress: number) {
  if (progress === 0) return "info"
  if (progress === 1) return "success"
  return "warning"
}

// 修改 handleParseDocument 方法
function handleParseDocument(row: any) {
  // 先判断是否已完成解析
  if (row.progress === 1) {
    ElMessage.warning("文档已完成解析，无需再重复解析")
    return
  }

  ElMessageBox.confirm(
    `确定要解析文档 "${row.name}" 吗？`,
    "解析确认",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "info"
    }
  ).then(() => {
    runDocumentParseApi(row.id)
      .then(() => {
        ElMessage.success("解析任务已提交")
        // 设置当前文档ID并显示解析进度对话框
        currentDocId.value = row.id
        showParseProgress.value = true
        // 刷新文档列表
        getDocumentList()
      })
      .catch((error) => {
        ElMessage.error(`解析任务提交失败: ${error?.message || "未知错误"}`)
      })
  }).catch(() => {
    // 用户取消操作
  })
}

// 添加解析完成和失败的处理函数
function handleParseComplete() {
  ElMessage.success("文档解析完成")
  getDocumentList() // 刷新文档列表
  getTableData() // 刷新知识库列表（因为文档数量可能变化）
}

function handleParseFailed(error: string) {
  ElMessage.error(`文档解析失败: ${error || "未知错误"}`)
  getDocumentList() // 刷新文档列表以更新状态
}

// 处理移除文档
function handleRemoveDocument(row: any) {
  ElMessageBox.confirm(
    `确定要从知识库中移除文档 "${row.name}" 吗？<br><span style="color: #909399; font-size: 12px;">该操作只是移除知识库文件，不会删除原始文件</span>`,
    "移除确认",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
      dangerouslyUseHTMLString: true
    }
  ).then(() => {
    deleteDocumentApi(row.id)
      .then(() => {
        ElMessage.success("文档已从知识库移除")
        // 刷新文档列表
        getDocumentList()
        // 刷新知识库列表（因为文档数量会变化）
        getTableData()
      })
      .catch((error) => {
        ElMessage.error(`移除文档失败: ${error?.message || "未知错误"}`)
      })
  }).catch(() => {
    // 用户取消操作
  })
}

// 添加文档对话框
const addDocumentDialogVisible = ref(false)
const selectedFiles = ref<string[]>([])
const fileLoading = ref(false)
const fileList = ref<any[]>([])
const filePaginationData = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0,
  pageSizes: [10, 20, 50, 100],
  layout: "total, sizes, prev, pager, next, jumper"
})

// 处理添加文档
function handleAddDocument() {
  addDocumentDialogVisible.value = true
  // 重置选择
  selectedFiles.value = []
  // 获取文件列表
  getFileList()
}

// 获取文件列表
function getFileList() {
  fileLoading.value = true
  // 调用获取文件列表的API
  getFileListApi({
    currentPage: filePaginationData.currentPage,
    size: filePaginationData.pageSize,
    name: ""
  }).then((response) => {
    const typedResponse = response as ApiResponse<FileListResponse>
    fileList.value = typedResponse.data.list
    filePaginationData.total = typedResponse.data.total
  }).catch((error) => {
    ElMessage.error(`获取文件列表失败: ${error?.message || "未知错误"}`)
    fileList.value = []
  }).finally(() => {
    fileLoading.value = false
  })
}

// 处理文件选择变化
function handleFileSelectionChange(selection: any[]) {
  // 使用Array.from和JSON方法双重确保转换为普通数组
  selectedFiles.value = JSON.parse(JSON.stringify(Array.from(selection).map(item => item.id)))
}

// 添加一个请求锁变量
const isAddingDocument = ref(false)
const messageShown = ref(false) // 添加这一行，将 messageShown 提升为组件级别的变量

// 修改 confirmAddDocument 函数
async function confirmAddDocument() {
  // 检查是否已经在处理请求
  if (isAddingDocument.value) {
    console.log("正在处理添加文档请求，请勿重复点击")
    return
  }

  if (selectedFiles.value.length === 0) {
    ElMessage.warning("请至少选择一个文件")
    return
  }

  if (!currentKnowledgeBase.value) return

  try {
    // 设置请求锁
    isAddingDocument.value = true
    messageShown.value = false // 重置消息显示标志，使用组件级别的变量
    console.log("开始添加文档请求...", selectedFiles.value)

    // 直接处理文件ID，不再弹出确认对话框
    const fileIds = JSON.parse(JSON.stringify([...selectedFiles.value]))

    // 发送API请求 - 移除不必要的内层 try/catch
    const response = await axios.post(
      `/api/v1/knowledgebases/${currentKnowledgeBase.value.id}/documents`,
      { file_ids: fileIds }
    )

    console.log("API原始响应:", response)

    // 检查响应状态
    if (response.data && (response.data.code === 0 || response.data.code === 201)) {
      // 成功处理
      if (!messageShown.value) {
        messageShown.value = true
        console.log("显示成功消息")
        ElMessage.success("文档添加成功")
      }

      addDocumentDialogVisible.value = false
      getDocumentList()
      getTableData()
    } else {
      // 处理错误响应
      throw new Error(response.data?.message || "添加文档失败")
    }
  } catch (error: any) {
    // API调用失败
    console.error("API请求失败详情:", {
      error: error?.toString(),
      stack: error?.stack,
      response: error?.response?.data,
      request: error?.request,
      config: error?.config
    })

    // 添加更详细的错误日志
    console.log("错误详情:", error)
    if (error.response) {
      console.log("响应数据:", error.response.data)
      console.log("响应状态:", error.response.status)
    }

    ElMessage.error(`添加文档失败: ${error?.message || "未知错误"}`)
  } finally {
    // 无论成功失败，都解除请求锁
    console.log("添加文档请求完成，解除锁定", new Date().toISOString())
    setTimeout(() => {
      isAddingDocument.value = false
    }, 500) // 增加延迟，防止快速点击
  }
}

// 格式化文件大小
function formatFileSize(size: number) {
  if (!size) return "0 B"

  const units = ["B", "KB", "MB", "GB", "TB"]
  let index = 0
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024
    index++
  }

  return `${size.toFixed(2)} ${units[index]}`
}

// 格式化文件类型
function formatFileType(type: string) {
  const typeMap: Record<string, string> = {
    pdf: "PDF",
    doc: "Word",
    docx: "Word",
    xls: "Excel",
    xlsx: "Excel",
    ppt: "PPT",
    pptx: "PPT",
    txt: "文本",
    md: "Markdown",
    jpg: "图片",
    jpeg: "图片",
    png: "图片"
  }

  return typeMap[type.toLowerCase()] || type
}

// 删除知识库
function handleDelete(row: KnowledgeBaseData) {
  ElMessageBox.confirm(
    `确定要删除知识库 "${row.name}" 吗？删除后将无法恢复，且其中的所有文档也将被删除。`,
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
          deleteKnowledgeBaseApi(row.id)
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

// 批量删除知识库
function handleBatchDelete() {
  if (multipleSelection.value.length === 0) {
    ElMessage.warning("请至少选择一个知识库")
    return
  }

  ElMessageBox.confirm(
    `确定要删除选中的 <strong>${multipleSelection.value.length}</strong> 个知识库吗？<br><span style="color: #F56C6C; font-size: 12px;">此操作不可恢复，且其中的所有文档也将被删除</span>`,
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
          batchDeleteKnowledgeBaseApi(ids)
            .then(() => {
              ElMessage.success(`成功删除 ${multipleSelection.value.length} 个知识库`)
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
function handleSelectionChange(selection: KnowledgeBaseData[]) {
  multipleSelection.value = selection
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
        <el-form-item prop="name" label="知识库名称">
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
            :icon="Plus"
            @click="handleCreate"
          >
            新建知识库
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

      <div class="table-wrapper">
        <el-table :data="tableData" @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="50" align="center" />
          <el-table-column label="序号" align="center" width="80">
            <template #default="scope">
              {{ (paginationData.currentPage - 1) * paginationData.pageSize + scope.$index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="name" label="知识库名称" align="center" min-width="120" />
          <el-table-column prop="description" label="描述" align="center" min-width="180" show-overflow-tooltip />
          <el-table-column prop="doc_num" label="文档数量" align="center" width="100" />
          <!-- 添加语言列 -->
          <el-table-column label="语言" align="center" width="100">
            <template #default="scope">
              <el-tag type="info" size="small">
                {{ scope.row.language === 'Chinese' ? '中文' : '英文' }}
              </el-tag>
            </template>
          </el-table-column>
          <!-- 添加权限列 -->
          <el-table-column label="权限" align="center" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.permission === 'me' ? 'success' : 'warning'" size="small">
                {{ scope.row.permission === 'me' ? '个人' : '团队' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" align="center" width="180">
            <template #default="scope">
              {{ scope.row.create_date }}
            </template>
          </el-table-column>
          <el-table-column fixed="right" label="操作" width="180" align="center">
            <template #default="scope">
              <el-button
                type="primary"
                text
                bg
                size="small"
                :icon="View"
                @click="handleView(scope.row)"
              >
                查看
              </el-button>
              <el-button
                type="danger"
                text
                bg
                size="small"
                :icon="Delete"
                @click="handleDelete(scope.row)"
              >
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

    <!-- 知识库详情对话框 -->
    <el-dialog
      v-model="viewDialogVisible"
      :title="`知识库详情 - ${currentKnowledgeBase?.name || ''}`"
      width="80%"
    >
      <div v-if="currentKnowledgeBase">
        <div class="kb-info-header">
          <div>
            <span class="kb-info-label">知识库ID:</span> {{ currentKnowledgeBase.id }}
          </div>
          <div>
            <span class="kb-info-label">文档总数:</span> {{ currentKnowledgeBase.doc_num }}
          </div>
          <div>
            <span class="kb-info-label">语言:</span>
            <el-tag type="info" size="small">
              {{ currentKnowledgeBase.language === 'Chinese' ? '中文' : '英文' }}
            </el-tag>
          </div>
          <div>
            <span class="kb-info-label">权限:</span>
            <el-tag :type="currentKnowledgeBase.permission === 'me' ? 'success' : 'warning'" size="small">
              {{ currentKnowledgeBase.permission === 'me' ? '个人' : '团队' }}
            </el-tag>
          </div>
        </div>

        <div class="document-table-header">
          <div class="left-buttons">
            <el-button type="primary" @click="handleAddDocument">
              添加文档
            </el-button>
          </div>
        </div>

        <div class="document-table-wrapper" v-loading="documentLoading">
          <el-table :data="documentList" style="width: 100%">
            <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="chunk_num" label="分块数" width="100" align="center" />
            <el-table-column label="上传日期" width="180" align="center">
              <template #default="scope">
                {{ scope.row.create_date }}
              </template>
            </el-table-column>
            <el-table-column label="解析状态" width="120" align="center">
              <template #default="scope">
                <el-tag :type="getParseStatusType(scope.row.progress)">
                  {{ formatParseStatus(scope.row.progress) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" align="center">
              <template #default="scope">
                <el-button
                  type="success"
                  size="small"
                  :icon="CaretRight"
                  @click="handleParseDocument(scope.row)"
                >
                  解析
                </el-button>
                <el-button
                  type="danger"
                  size="small"
                  :icon="Delete"
                  @click="handleRemoveDocument(scope.row)"
                >
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页控件 -->
          <div class="pagination-container">
            <el-pagination
              v-model:current-page="docPaginationData.currentPage"
              v-model:page-size="docPaginationData.pageSize"
              :page-sizes="docPaginationData.pageSizes"
              :layout="docPaginationData.layout"
              :total="docPaginationData.total"
              @size-change="handleDocSizeChange"
              @current-change="handleDocCurrentChange"
            />
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 新建知识库对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="新建知识库"
      width="40%"
    >
      <el-form
        ref="knowledgeBaseFormRef"
        :model="knowledgeBaseForm"
        :rules="knowledgeBaseFormRules"
        label-width="100px"
      >
        <el-form-item label="知识库名称" prop="name">
          <el-input v-model="knowledgeBaseForm.name" placeholder="请输入知识库名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="knowledgeBaseForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入知识库描述"
          />
        </el-form-item>
        <el-form-item label="语言" prop="language">
          <el-select v-model="knowledgeBaseForm.language" placeholder="请选择语言">
            <el-option label="中文" value="Chinese" />
            <el-option label="英文" value="English" />
          </el-select>
        </el-form-item>
        <el-form-item label="权限" prop="permission">
          <el-select v-model="knowledgeBaseForm.permission" placeholder="请选择权限">
            <el-option label="个人" value="me" />
            <el-option label="团队" value="team" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="uploadLoading"
          @click="submitCreate"
        >
          确认创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加文档对话框 -->
    <el-dialog
      v-model="addDocumentDialogVisible"
      title="添加文档到知识库"
      width="70%"
    >
      <div v-loading="fileLoading">
        <el-table
          :data="fileList"
          style="width: 100%"
          @selection-change="handleFileSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="name" label="文件名" min-width="180" show-overflow-tooltip />
          <el-table-column prop="size" label="大小" width="100" align="center">
            <template #default="scope">
              {{ formatFileSize(scope.row.size) }}
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" width="100" align="center">
            <template #default="scope">
              {{ formatFileType(scope.row.type) }}
            </template>
          </el-table-column>
          <!-- 移除上传日期列 -->
        </el-table>

        <!-- 分页控件 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="filePaginationData.currentPage"
            v-model:page-size="filePaginationData.pageSize"
            :page-sizes="filePaginationData.pageSizes"
            :layout="filePaginationData.layout"
            :total="filePaginationData.total"
            @size-change="(size) => { filePaginationData.pageSize = size; filePaginationData.currentPage = 1; getFileList(); }"
            @current-change="(page) => { filePaginationData.currentPage = page; getFileList(); }"
          />
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="addDocumentDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :disabled="isAddingDocument"
            @click.stop.prevent="confirmAddDocument"
          >
            {{ isAddingDocument ? '处理中...' : '确定' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
  <DocumentParseProgress
    :document-id="currentDocId"
    :visible="showParseProgress"
    @close="showParseProgress = false"
    @parse-complete="handleParseComplete"
    @parse-failed="handleParseFailed"
  />
</template>

<style lang="scss" scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 94%;
}
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

.document-table-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
  margin-top: 16px;
}

.kb-info-header {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 20px;
  padding: 16px;
  background-color: #f5f7fa;
  border-radius: 4px;

  .kb-info-label {
    color: #606266;
    font-weight: 500;
    margin-right: 8px;
  }
}

.document-table-wrapper {
  margin-top: 20px;
}

.document-table-header {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 16px;
  margin-top: 16px;
}

.pagination-container {
  margin-top: 20px;
  margin-bottom: 20px;
  display: flex;
  justify-content: flex-end;
}

.delete-confirm-dialog {
  :deep(.el-message-box__message) {
    text-align: center;
  }
}
</style>
