<script lang="ts" setup>
import type { SequentialBatchTaskProgress } from "@@/apis/kbs/document"
import type { FormInstance } from "element-plus"
import DocumentParseProgress from "@/layouts/components/DocumentParseProgress/index.vue"
import {
  deleteDocumentApi,
  getDocumentListApi,
  getFileListApi,
  getSequentialBatchParseProgressApi,
  runDocumentParseApi,
  startSequentialBatchParseAsyncApi
} from "@@/apis/kbs/document"
import {
  batchDeleteKnowledgeBaseApi,
  createKnowledgeBaseApi,
  deleteKnowledgeBaseApi,
  getKnowledgeBaseListApi,
  getSystemEmbeddingConfigApi,
  setSystemEmbeddingConfigApi
} from "@@/apis/kbs/knowledgebase"
import { getTableDataApi } from "@@/apis/tables"
import { usePagination } from "@@/composables/usePagination"
import { CaretRight, Delete, Edit, Loading, Plus, Refresh, Search, Setting, View } from "@element-plus/icons-vue"

import axios from "axios"
import { ElMessage, ElMessageBox } from "element-plus"
import { nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from "vue"
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
  permission: "me",
  creator_id: ""
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
  ],
  creator_id: [
    { required: true, message: "请选择创建人", trigger: "change" }
  ]
}

const knowledgeBaseFormRef = ref<FormInstance | null>(null)

// 查询知识库列表
const tableData = ref<KnowledgeBaseData[]>([])
const searchFormRef = ref<FormInstance | null>(null)
const searchData = reactive({
  name: ""
})

// 排序状态
const sortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc" // 默认排序顺序
})

// 文档列表排序状态
const docSortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc" // 默认排序顺序
})

// 文件列表排序状态
const fileSortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc" // 默认排序顺序
})

const editDialogVisible = ref(false)
const editForm = reactive({
  id: "",
  name: "",
  permission: "me"
})
const editLoading = ref(false)

// 处理修改知识库
function handleEdit(row: KnowledgeBaseData) {
  editDialogVisible.value = true
  editForm.id = row.id
  editForm.name = row.name
  editForm.permission = row.permission
}

// 提交修改
function submitEdit() {
  editLoading.value = true
  // 调用修改知识库API
  axios.put(`/api/v1/knowledgebases/${editForm.id}`, {
    permission: editForm.permission
  })
    .then(() => {
      ElMessage.success("知识库权限修改成功")
      editDialogVisible.value = false
      // 刷新知识库列表
      getTableData()
    })
    .catch((error) => {
      ElMessage.error(`修改知识库权限失败: ${error?.message || "未知错误"}`)
    })
    .finally(() => {
      editLoading.value = false
    })
}

// 存储多选的表格数据
const multipleSelection = ref<KnowledgeBaseData[]>([])

// 获取知识库列表数据
function getTableData() {
  loading.value = true
  // 调用获取知识库列表API
  getKnowledgeBaseListApi({
    currentPage: paginationData.currentPage,
    size: paginationData.pageSize,
    name: searchData.name,
    sort_by: sortData.sortBy,
    sort_order: sortData.sortOrder
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
  getUserList() // 获取用户列表
}

// 获取用户列表
function getUserList() {
  userLoading.value = true
  // 复用用户管理页面的API
  getTableDataApi({
    currentPage: 1,
    size: 1000, // 获取足够多的用户
    username: "",
    email: "",
    sort_by: "create_date",
    sort_order: "desc"
  }).then(({ data }) => {
    userList.value = data.list.map((user: any) => ({
      id: user.id,
      username: user.username
    }))
  }).catch(() => {
    userList.value = []
    ElMessage.error("获取用户列表失败")
  }).finally(() => {
    userLoading.value = false
  })
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
const batchParsingLoading = ref(false) // 批量解析加载状态
const currentKnowledgeBase = ref<KnowledgeBaseData | null>(null)
const documentLoading = ref(false)
const documentList = ref<any[]>([])

// 顺序批量任务轮询相关状态
const batchPollingInterval = ref<NodeJS.Timeout | null>(null) // 定时器 ID
const isBatchPolling = ref(false) // 是否正在轮询批量任务
const batchProgress = ref<SequentialBatchTaskProgress | null>(null) // 存储批量任务进度信息
// 计算批量解析按钮是否禁用
const isBatchParseDisabled = computed(() => {
  // 如果正在轮询批量任务，则禁用
  if (isBatchPolling.value) return true
  // 如果文档列表为空，或者所有文档都已完成，则禁用
  if (!documentList.value || documentList.value.length === 0) return true
  return documentList.value.every(doc => doc.status === "3")
})

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
    name: "",
    sort_by: docSortData.sortBy,
    sort_order: docSortData.sortOrder
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

/**
 * @description 处理文档表格排序变化事件
 * @param {object} sortInfo 排序信息对象，包含 prop 和 order
 * @param {string} sortInfo.prop 排序的字段名
 * @param {string | null} sortInfo.order 排序的顺序 ('ascending', 'descending', null)
 */
function handleDocSortChange({ prop }: { prop: string, order: string | null }) {
  // 如果点击的是同一个字段，则切换排序顺序
  if (docSortData.sortBy === prop) {
    // 当前为正序则切换为倒序，否则切换为正序
    docSortData.sortOrder = docSortData.sortOrder === "asc" ? "desc" : "asc"
  } else {
    // 切换字段时，默认正序
    docSortData.sortBy = prop
    docSortData.sortOrder = "asc"
  }
  getDocumentList()
}

// 修改handleView方法
function handleView(row: KnowledgeBaseData) {
  currentKnowledgeBase.value = row
  viewDialogVisible.value = true
  // 重置文档分页
  docPaginationData.currentPage = 1
  batchProgress.value = null
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

// handleParseDocument 方法
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

// 处理批量文档解析 (调用同步 API)
function handleBatchParse() {
  if (!currentKnowledgeBase.value) return

  const kbId = currentKnowledgeBase.value.id
  const kbName = currentKnowledgeBase.value.name

  ElMessageBox.confirm(
    `确定要为知识库 "${kbName}" 启动后台批量解析吗？<br><strong style="color: #E6A23C;">该过程将在后台运行，您可以稍后查看结果或关闭此窗口。</strong>`,
    "启动批量解析确认",
    {
      confirmButtonText: "确定启动",
      cancelButtonText: "取消",
      type: "warning",
      dangerouslyUseHTMLString: true // 允许使用 HTML 标签
    }
  ).then(async () => {
    batchParsingLoading.value = true // 标记“正在启动”状态
    batchProgress.value = null
    try {
      const res = await startSequentialBatchParseAsyncApi(kbId)

      if (res.code === 0 && res.data) {
        // 后端成功接收了启动请求
        ElMessage.success(res.data.message || `已成功启动批量解析任务`)
        // --- 关键：启动轮询来监控进度 ---
        startBatchPolling()
        // 可以在启动后稍微延迟一下再刷新列表，尝试显示“解析中”的状态
        setTimeout(getDocumentList, 1500)
      } else {
        // 启动 API 本身调用失败，或后端返回了错误
        const errorMsg = res.data?.message || res.message || "启动批量解析任务失败"
        ElMessage.error(errorMsg)
        batchParsingLoading.value = false // 启动失败，取消“正在启动”状态
      }
    } catch (error: any) {
      // 请求启动 API 时发生网络错误或其他异常
      ElMessage.error(`启动批量解析任务时出错: ${error?.message || "网络错误"}`)
      console.error("启动批量解析任务失败:", error)
      batchParsingLoading.value = false // 启动异常，取消“正在启动”状态
    } finally {
      // 只有在 *没有* 成功启动轮询的情况下，才将 batchParsingLoading 设置为 false
      // 如果轮询已开始，则由 isBatchPolling 状态控制按钮和界面的显示
      if (!isBatchPolling.value) {
        batchParsingLoading.value = false
      }
    }
  }).catch(() => {
    // 用户点击了“取消”按钮
    ElMessage.info("已取消批量解析操作")
  })
}
// 开始轮询批量任务进度
function startBatchPolling() {
  // 如果已经在轮询或者没有当前知识库，则不执行
  if (isBatchPolling.value || !currentKnowledgeBase.value) return

  console.log("开始轮询知识库的批量解析进度:", currentKnowledgeBase.value.id)
  isBatchPolling.value = true
  // 设置一个初始状态，给用户即时反馈
  batchProgress.value = { status: "running", message: "正在启动批量解析任务...", total: 0, current: 0 }

  // 以防万一，先清除可能存在的旧定时器
  if (batchPollingInterval.value) {
    clearInterval(batchPollingInterval.value)
  }

  // 立即执行一次获取进度，然后设置定时器
  fetchBatchProgress()
  batchPollingInterval.value = setInterval(fetchBatchProgress, 5000) // 每 5 秒查询一次进度
}

// 停止轮询批量任务进度
function stopBatchPolling() {
  if (batchPollingInterval.value) {
    console.log("停止批量解析进度轮询。")
    clearInterval(batchPollingInterval.value)
    batchPollingInterval.value = null
  }
  // 保留最后一次的状态信息用于显示
  isBatchPolling.value = false
  batchParsingLoading.value = false
}

// 获取并更新批量任务进度
async function fetchBatchProgress() {
  // 如果详情对话框已关闭或没有当前知识库，则停止轮询
  if (!currentKnowledgeBase.value || !viewDialogVisible.value) {
    stopBatchPolling()
    return
  }

  try {
    // 调用获取进度的 API
    const res = await getSequentialBatchParseProgressApi(currentKnowledgeBase.value.id)

    if (res.code === 0 && res.data) {
      // 更新进度状态
      batchProgress.value = res.data
      console.log("获取到批量进度:", batchProgress.value)

      // 检查任务是否已完成或失败
      if (batchProgress.value.status === "completed" || batchProgress.value.status === "failed") {
        stopBatchPolling() // 停止轮询
        // 显示最终结果提示
        ElMessage({
          message: batchProgress.value.message || (batchProgress.value.status === "completed" ? "批量解析已完成" : "批量解析失败"),
          type: batchProgress.value.status === "completed" ? "success" : "error"
        })
        // 刷新文档列表以显示最新状态
        getDocumentList()
        // 刷新知识库列表（文档数、分块数可能变化）
        getTableData()
      }
    } else {
      // API 调用成功但返回了错误码，或者没有数据
      console.error("获取批量进度失败:", res.message || res.data?.message)
      // 可以在界面上提示获取进度时遇到问题
      if (batchProgress.value) { // 确保 batchProgress 不是 null
        batchProgress.value.message = `获取进度时出错: ${res.message || "请稍后..."}`
      }
    }
  } catch (error: any) {
    // 网络错误或其他请求异常
    console.error("请求批量进度API失败:", error)
    // 可以在界面上提示网络问题
    if (batchProgress.value) { // 确保 batchProgress 不是 null
      batchProgress.value.message = `获取进度时网络错误: ${error.message || "请检查网络连接..."}`
    }
    // 根据策略决定是否停止轮询，例如连续多次失败后停止
    // stopBatchPolling();
  }
}

// 添加解析完成和失败的处理函数
function handleParseComplete() {
  ElMessage.success("文档解析完成")
  getDocumentList() // 刷新文档列表
  getTableData() // 刷新知识库列表
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
        // 刷新知识库列表
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
    name: "",
    sort_by: fileSortData.sortBy,
    sort_order: fileSortData.sortOrder
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

/**
 * @description 处理文件表格排序变化事件
 * @param {object} sortInfo 排序信息对象，包含 prop 和 order
 * @param {string} sortInfo.prop 排序的字段名
 * @param {string | null} sortInfo.order 排序的顺序 ('ascending', 'descending', null)
 */
function handleFileSortChange({ prop }: { prop: string, order: string | null }) {
  // 如果点击的是同一个字段，则切换排序顺序
  if (fileSortData.sortBy === prop) {
    // 当前为正序则切换为倒序，否则切换为正序
    fileSortData.sortOrder = fileSortData.sortOrder === "asc" ? "desc" : "asc"
  } else {
    // 切换字段时，默认正序
    fileSortData.sortBy = prop
    fileSortData.sortOrder = "asc"
  }
  getFileList()
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

// 系统 Embedding 配置逻辑
const configModalVisible = ref(false)
const configFormRef = ref<FormInstance>() // 表单引用
const configFormLoading = ref(false) // 表单加载状态
const configSubmitLoading = ref(false) // 提交按钮加载状态

const configForm = reactive({
  llm_name: "",
  api_base: "",
  api_key: ""
})

// 简单的 URL 校验规则
function validateUrl(rule: any, value: any, callback: any) {
  if (!value) {
    return callback(new Error("请输入模型 API 地址"))
  }
  // 允许 http, https 开头，允许 IP 地址和域名，允许端口
  // 修正：允许路径，但不允许查询参数或片段
  const urlPattern = /^(https?:\/\/)?([a-zA-Z0-9.-]+|\[[a-fA-F0-9:]+\])(:\d+)?(\/[^?#]*)?$/
  if (!urlPattern.test(value)) {
    callback(new Error("请输入有效的 Base URL (例如 http://host:port 或 https://domain/path)"))
  } else {
    callback()
  }
}

const configFormRules = reactive({
  llm_name: [{ required: true, message: "请输入模型名称", trigger: "blur" }],
  api_base: [{ required: true, validator: validateUrl, trigger: "blur" }]
  // api_key 不是必填项
})

// 显示配置模态框
async function showConfigModal() {
  configModalVisible.value = true
  configFormLoading.value = true
  // 重置表单可能需要在 nextTick 中执行，确保 DOM 更新完毕
  await nextTick()
  configFormRef.value?.resetFields() // 清空上次的输入和校验状态

  try {
    // 确认 API 函数名称是否正确，并添加类型断言
    const res = await getSystemEmbeddingConfigApi() as ApiResponse<{ llm_name?: string, api_base?: string, api_key?: string }>
    if (res.code === 0 && res.data) {
      configForm.llm_name = res.data.llm_name || ""
      configForm.api_base = res.data.api_base || ""
      // 注意：API Key 通常不应在 GET 请求中返回，如果后端不返回，这里会是空字符串
      configForm.api_key = res.data.api_key || ""
    } else if (res.code !== 0) {
      ElMessage.error(res.message || "获取配置失败")
    } else {
      // code === 0 但 data 为空，说明没有配置
      console.log("当前未配置嵌入模型。")
    }
  } catch (error: any) {
    ElMessage.error(error.message || "获取配置请求失败")
    console.error("获取配置失败:", error)
  } finally {
    configFormLoading.value = false
  }
}

// 处理模态框关闭
function handleModalClose() {
  // 可以在这里再次重置表单，以防用户未保存直接关闭
  configFormRef.value?.resetFields()
}

// 处理配置提交
async function handleConfigSubmit() {
  if (!configFormRef.value) return
  // 使用 .then() .catch() 处理 validate 的 Promise
  configFormRef.value.validate().then(async () => {
    // 验证通过
    configSubmitLoading.value = true
    try {
      const payload = {
        llm_name: configForm.llm_name.trim(),
        api_base: configForm.api_base.trim(),
        api_key: configForm.api_key
      }
      // 确认 API 函数名称是否正确，并添加类型断言
      const res = await setSystemEmbeddingConfigApi(payload) as ApiResponse<any> // 使用类型断言并指定泛型参数为any
      if (res.code === 0) {
        ElMessage.success("连接验证成功！")
        configModalVisible.value = false
      } else {
        // 后端应在 res.message 中返回错误信息，包括连接测试失败的原因
        ElMessage.error(res.message || "连接验证失败")
      }
    } catch (error: any) {
      ElMessage.error(error.message || "连接验证请求失败")
      console.error("连接验证失败:", error)
    } finally {
      configSubmitLoading.value = false
    }
  }).catch((errorFields) => {
    // 验证失败
    console.log("表单验证失败!", errorFields)
    // 这里不需要返回 false，validate 的 Promise reject 就表示失败了
  })
}

// 根据状态决定 Alert 类型
function getAlertType(status: any) {
  switch (status) {
    case "failed":
    case "not_found": // 'not_found' 可能也视为一种错误
      return "error"
    case "completed":
      return "success"
    case "cancelled":
      return "warning" // 取消可以视为警告或信息，看需求
    case "running":
    case "starting":
    case "cancelling":
    default:
      return "info"
  }
}

// 判断是否是加载中状态
function isLoadingStatus(status: string) {
  return ["running", "starting", "cancelling"].includes(status)
}

// 判断是否应该显示进度计数 (例如，启动中或任务未找到时可能不适合显示 0/0)
function shouldShowProgressCount(status: string) {
  return !["starting", "not_found"].includes(status)
}

// 用户列表相关状态
const userList = ref<{ id: number, username: string }[]>([])
const userLoading = ref(false)
</script>

<template>
  <div>
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

          <div>
            <el-button type="primary" :icon="Setting" @click="showConfigModal">
              嵌入模型配置
            </el-button>
          </div>
        </div>

        <div class="table-wrapper">
          <el-table :data="tableData" @selection-change="handleSelectionChange" @sort-change="handleSortChange">
            <el-table-column type="selection" width="50" align="center" />
            <el-table-column label="序号" align="center" width="80">
              <template #default="scope">
                {{ (paginationData.currentPage - 1) * paginationData.pageSize + scope.$index + 1 }}
              </template>
            </el-table-column>
            <el-table-column prop="name" label="知识库名称" align="center" min-width="120" sortable="custom" />
            <el-table-column prop="description" label="描述" align="center" min-width="180" show-overflow-tooltip />
            <el-table-column prop="doc_num" label="文档数量" align="center" width="120" />
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
            <el-table-column label="创建时间" align="center" width="180" sortable="custom">
              <template #default="scope">
                {{ scope.row.create_date }}
              </template>
            </el-table-column>
            <el-table-column fixed="right" label="操作" width="300" align="center">
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
                  type="warning"
                  text
                  bg
                  size="small"
                  :icon="Edit"
                  @click="handleEdit(scope.row)"
                >
                  修改
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
        append-to-body
        :close-on-click-modal="!batchParsingLoading"
        :close-on-press-escape="!batchParsingLoading"
        :show-close="!batchParsingLoading"
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
              <!-- 批量解析按钮 -->
              <el-button
                type="warning"
                :icon="CaretRight"
                :loading="batchParsingLoading && !isBatchPolling"
                @click="handleBatchParse"
                :disabled="isBatchParseDisabled || batchParsingLoading"
              >
                <!-- 根据是否在轮询显示不同文本 -->
                {{ isBatchPolling ? '正在批量解析...' : (batchParsingLoading ? '正在启动...' : '批量解析') }}
              </el-button>
            </div>
          </div>
          <!-- 进度显示 -->
          <div v-if="batchProgress" class="batch-progress">
            <el-alert
              :title="batchProgress.message || '正在处理...'"
              :type="getAlertType(batchProgress.status)"
              :closable="false"
              show-icon
              class="batch-progress-alert"
            >
              <!-- 加载图标：仅在进行中相关状态 ('running', 'starting', 'cancelling') 显示 -->
              <template #icon v-if="isLoadingStatus(batchProgress.status)">
                <el-icon class="is-loading">
                  <Loading />
                </el-icon>
              </template>

              <!-- 默认插槽：用于显示额外的进度详情 -->
              <div class="batch-progress-details">
                <!-- 显示处理进度 (当前项 / 总项数) -->
                <!-- 仅当总数大于0且状态不是 'starting' 或 'not_found' 时显示比较有意义 -->
                <template v-if="batchProgress.total > 0 && shouldShowProgressCount(batchProgress.status)">
                  <p>
                    处理进度: {{ batchProgress.current ?? 0 }} / {{ batchProgress.total }}
                  </p>
                </template>

                <!-- 占位符：如果没有显示进度计数，则显示一个占位符防止高度塌陷 -->
                <template v-else>
                  <p /> <!-- 使用不换行空格确保最小高度 -->
                </template>
              </div>
            </el-alert>
          </div>
          <!-- === 结束进度显示 === -->

          <div class="document-table-wrapper" v-loading="documentLoading || (isBatchPolling && !batchProgress)">
            <el-table :data="documentList" style="width: 100%" @sort-change="handleDocSortChange">
              <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip sortable="custom" />
              <el-table-column prop="chunk_num" label="分块数" width="100" align="center" />
              <el-table-column prop="create_date" label="上传日期" width="180" align="center" sortable="custom">
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
          <el-form-item label="创建人" prop="creator_id">
            <el-select
              v-model="knowledgeBaseForm.creator_id"
              placeholder="请选择创建人"
              style="width: 100%"
              filterable
              :loading="userLoading"
            >
              <el-option
                v-for="user in userList"
                :key="user.id"
                :label="user.username"
                :value="user.id"
              />
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

      <!-- 修改知识库对话框 -->
      <el-dialog
        v-model="editDialogVisible"
        title="修改知识库权限"
        width="40%"
      >
        <el-form
          label-width="120px"
        >
          <el-form-item label="知识库名称">
            <span>{{ editForm.name }}</span>
          </el-form-item>
          <el-form-item label="权限设置">
            <el-select v-model="editForm.permission" placeholder="请选择权限">
              <el-option label="个人" value="me" />
              <el-option label="团队" value="team" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <div style="color: #909399; font-size: 12px; line-height: 1.5;">
              个人权限：仅自己可见和使用<br>
              团队权限：团队成员可见和使用
            </div>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="editDialogVisible = false">
            取消
          </el-button>
          <el-button
            type="primary"
            :loading="editLoading"
            @click="submitEdit"
          >
            确认修改
          </el-button>
        </template>
      </el-dialog>

      <!-- 文档对话框 -->
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
            @sort-change="handleFileSortChange"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="name" label="文件名" min-width="180" show-overflow-tooltip sortable="custom" />
            <el-table-column prop="size" label="大小" width="100" align="center" sortable="custom">
              <template #default="scope">
                {{ formatFileSize(scope.row.size) }}
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="100" align="center">
              <template #default="scope">
                {{ formatFileType(scope.row.type) }}
              </template>
            </el-table-column>
            <el-table-column prop="create_date" label="创建时间" align="center" width="180" sortable="custom">
              <template #default="scope">
                {{ scope.row.create_date }}
              </template>
            </el-table-column>
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

      <!-- 系统 Embedding 配置模态框 -->
      <el-dialog
        v-model="configModalVisible"
        title="嵌入模型配置"
        width="500px"
        :close-on-click-modal="false"
        @close="handleModalClose"
        append-to-body
      >
        <el-form
          ref="configFormRef"
          :model="configForm"
          :rules="configFormRules"
          label-width="120px"
          v-loading="configFormLoading"
        >
          <el-form-item label="模型名称" prop="llm_name">
            <el-input v-model="configForm.llm_name" placeholder="请先在前台进行配置" disabled />
            <div class="form-tip">
              与模型服务中部署的名称一致
            </div>
          </el-form-item>
          <el-form-item label="模型 API 地址" prop="api_base">
            <el-input v-model="configForm.api_base" placeholder="请先在前台进行配置" disabled />
            <div class="form-tip">
              模型的 Base URL
            </div>
          </el-form-item>
          <el-form-item label="API Key (可选)" prop="api_key">
            <el-input v-model="configForm.api_key" type="password" show-password placeholder="请先在前台进行配置" disabled />
            <div class="form-tip">
              如果模型服务需要认证，请提供
            </div>
          </el-form-item>
          <el-form-item>
            <div style="color: #909399; font-size: 12px; line-height: 1.5;">
              此配置将作为知识库解析时默认的 Embedding 模型。
            </div>
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="configModalVisible = false">取消</el-button>
            <el-button type="primary" @click="handleConfigSubmit" :loading="configSubmitLoading">
              测试连接
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
  </div>
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
  justify-content: space-between; // 确保左右两边对齐
  align-items: center; // 垂直居中对齐
  margin-bottom: 20px;
}

.table-wrapper {
  margin-bottom: 20px;
}

.pager-wrapper {
  display: flex;
  justify-content: flex-end;
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
  .left-buttons {
    display: flex;
    gap: 10px;
  }
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

.form-tip {
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
  margin-top: 4px;
}

.batch-progress {
  margin-bottom: 20px; // 与下方表格的间距
  margin-top: 5px; // 与上方按钮行的间距
  padding: 0 10px; // 左右留一些边距
}

.batch-progress-alert {
  // 可以给 Alert 添加一些效果，例如轻微的边框或背景
  // background-color: #f8f8f9; // 非常浅的背景色
  border: 1px solid #e9e9eb;
  border-radius: 4px;

  // 调整内部 icon 和 title/description 的对齐方式
  :deep(.el-alert__content) {
    display: flex;
    align-items: center; // 垂直居中对齐 Title 和 Icon (如果默认图标显示)
  }
  :deep(.el-alert__title) {
    margin-right: 15px; // 标题和右侧详情之间加点距离
  }

  // 自定义加载图标样式
  .el-icon.is-loading {
    margin-right: 8px; // 图标和标题之间的距离
    font-size: 16px; // 图标大小
  }
}

.batch-progress-details {
  font-size: 12px;
  line-height: 1.5;
  color: #606266; // 常规细节文字颜色

  p {
    margin: 0; // 移除段落默认边距
    min-height: 18px; // 保证有内容或占位符时有最小高度
  }

  .error-detail {
    color: #f56c6c; // 错误详情用醒目的红色
    font-weight: 500; // 可以稍微加粗
  }
}

// 确保旋转动画
@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// 加载图标继承动画
.el-tag .el-icon.is-loading,
.batch-progress-alert .el-icon.is-loading {
  margin-right: 4px;
  vertical-align: middle;
  animation: rotating 2s linear infinite;
}
</style>
