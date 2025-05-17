<script lang="ts" setup>
import type { TableData } from "@@/apis/configs/type"
import type { FormInstance } from "element-plus"
import { getTableDataApi } from "@@/apis/configs"
import { usePagination } from "@@/composables/usePagination"
import { Refresh, Search } from "@element-plus/icons-vue"

defineOptions({
  // 命名当前组件
  name: "UserConfig"
})

const loading = ref<boolean>(false)
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination()

// #region 增
// const DEFAULT_FORM_DATA: CreateOrUpdateTableRequestData = {
//   id: undefined,
//   username: "",
//   chatModel: "",
//   embeddingModel: ""
// }
// const dialogVisible = ref<boolean>(false)
// const formData = ref<CreateOrUpdateTableRequestData>(cloneDeep(DEFAULT_FORM_DATA))

// 删除响应
function handleDelete() {
  ElMessage.success("如需删除用户配置信息，请直接在前台登录用户账号进行操作")
}

// 修改
function handleUpdate() {
  ElMessage.success("如需修改用户配置信息，请直接在前台登录用户账号进行操作")
}

// 处理修改表单提交
// function submitForm() {
//   loading.value = true
//   updateTableDataApi(formData.value)
//     .then(() => {
//       ElMessage.success("修改成功")
//       dialogVisible.value = false
//       getTableData() // 刷新表格数据
//     })
//     .catch(() => {
//       ElMessage.error("修改失败")
//     })
//     .finally(() => {
//       loading.value = false
//     })
// }

// 查
const tableData = ref<TableData[]>([])
const searchFormRef = ref<FormInstance | null>(null)
const searchData = reactive({
  username: ""
})

// 存储多选的表格数据
const multipleSelection = ref<TableData[]>([])

function getTableData() {
  loading.value = true
  getTableDataApi({
    currentPage: paginationData.currentPage,
    size: paginationData.pageSize,
    username: searchData.username
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
function handleSearch() {
  paginationData.currentPage === 1 ? getTableData() : (paginationData.currentPage = 1)
}
function resetSearch() {
  searchFormRef.value?.resetFields()
  handleSearch()
}

// 表格多选事件处理
function handleSelectionChange(selection: TableData[]) {
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
        <el-form-item prop="username" label="用户名">
          <el-input v-model="searchData.username" placeholder="请输入" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">
            查询
          </el-button>
          <el-button :icon="Refresh" @click="resetSearch">
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    <el-card v-loading="loading" shadow="never">
      <div class="table-wrapper">
        <el-table :data="tableData" @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="50" align="center" />
          <el-table-column prop="username" label="用户名" align="center" />
          <el-table-column prop="chatModel" label="聊天模型" align="center" />
          <el-table-column prop="embeddingModel" label="嵌入模型" align="center" />
          <el-table-column prop="updateTime" label="更新时间" align="center" />
          <el-table-column fixed="right" label="操作" width="150" align="center">
            <template #default="">
              <el-button type="primary" text bg size="small" @click="handleUpdate">
                修改
              </el-button>
              <el-button type="danger" text bg size="small" @click="handleDelete()">
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

    <!-- 修改对话框 -->
    <!-- <el-dialog v-model="dialogVisible" title="修改配置" width="30%">
      <el-form :model="formData" label-width="100px">
        <el-form-item label="用户名">
          <el-input v-model="formData.username" disabled />
        </el-form-item>
        <el-form-item label="聊天模型">
          <el-input v-model="formData.chatModel" />
        </el-form-item>
        <el-form-item label="嵌入模型">
          <el-input v-model="formData.embeddingModel" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">
          取消
        </el-button>
        <el-button type="primary" @click="submitForm">
          确认
        </el-button>
      </template>
    </el-dialog> -->
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
