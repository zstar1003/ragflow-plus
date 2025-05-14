<script lang="ts" setup>
import type { FormInstance } from "element-plus"
import { addTeamMemberApi, getTableDataApi, getTeamMembersApi, getUsersApi, removeTeamMemberApi } from "@@/apis/teams"
import { usePagination } from "@@/composables/usePagination"
import { CirclePlus, Refresh, Search, UserFilled } from "@element-plus/icons-vue"
import { computed } from "vue" // 导入 computed

defineOptions({
  name: "TeamManagement"
})

const loading = ref<boolean>(false)
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination()

// 团队数据结构
interface TeamData {
  id: number
  name: string
  ownerName: string
  memberCount: number
  createTime: string
  updateTime: string
}

// 团队成员数据结构
interface TeamMember {
  userId: number
  username: string
  role: string
  joinTime: string
}

//  删
function handleDelete() {
  ElMessage.success("如需解散该团队，可直接删除负责人账号")
}

const tableData = ref<TeamData[]>([])

const searchData = reactive({
  name: ""
})

// 排序状态
const sortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc" // 默认排序顺序 (最新创建的在前)
})

// 存储多选的表格数据
const multipleSelection = ref<TeamData[]>([])

function getTableData() {
  loading.value = true

  getTableDataApi({
    currentPage: paginationData.currentPage,
    size: paginationData.pageSize,
    name: searchData.name,
    sort_by: sortData.sortBy,
    sort_order: sortData.sortOrder
  }).then(({ data }) => {
    paginationData.total = data.total
    tableData.value = data.list.map((item: any) => ({
      id: item.id,
      name: item.name,
      ownerName: item.ownerName,
      memberCount: item.memberCount,
      createTime: item.createTime,
      updateTime: item.updateTime
    }))
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

const searchFormRef = ref<FormInstance | null>(null)
function resetSearch() {
  searchFormRef.value?.resetFields()
  handleSearch()
}

// 表格多选事件处理
function handleSelectionChange(selection: TeamData[]) {
  multipleSelection.value = selection
}
// 团队成员管理相关
const memberDialogVisible = ref<boolean>(false)
const currentTeam = ref<TeamData | null>(null)
const teamMembers = ref<TeamMember[]>([])
const memberLoading = ref<boolean>(false)
// 添加成员相关状态
const addMemberDialogVisible = ref<boolean>(false)
const userList = ref<{ id: number, username: string }[]>([])
const userLoading = ref<boolean>(false)
const selectedUser = ref<number | undefined>(undefined)
const selectedRole = ref<string>("normal")

// 计算属性：过滤出可添加的用户（不在当前团队成员列表中的用户）
const availableUsers = computed(() => {
  const memberUserIds = new Set(teamMembers.value.map(member => member.userId))
  return userList.value.filter(user => !memberUserIds.has(user.id))
})

function handleManageMembers(row: TeamData) {
  currentTeam.value = row
  memberDialogVisible.value = true
  getTeamMembers(row.id)
}

// 获取团队成员列表
function getTeamMembers(teamId: number) {
  memberLoading.value = true
  getTeamMembersApi(teamId)
    .then((response: any) => {
      if (response.data && Array.isArray(response.data.list)) {
        teamMembers.value = response.data.list
      } else if (Array.isArray(response.data)) {
        teamMembers.value = response.data
      } else {
        teamMembers.value = []
      }
    })
    .catch(() => {
      teamMembers.value = []
    })
    .finally(() => {
      memberLoading.value = false
    })
}

// 添加成员
function handleAddMember() {
  // 打开添加成员对话框
  addMemberDialogVisible.value = true
  // 获取可添加的用户列表
  getUserList()
}

// 获取用户列表
function getUserList() {
  userLoading.value = true
  // 调用 getUsersApi 时传递 size 参数以获取所有用户
  getUsersApi({ size: 99999 }).then((res: any) => {
    if (res.data) {
      userList.value = res.data.list
    } else {
      userList.value = []
    }
  }).catch(() => {
    userList.value = []
  }).finally(() => {
    userLoading.value = false
  })
}

// 确认添加成员
function confirmAddMember() {
  if (!selectedUser.value) {
    ElMessage.warning("请选择要添加的用户")
    return
  }

  if (!currentTeam.value) {
    ElMessage.error("当前团队信息不存在")
    return
  }

  // 调用添加成员API
  addTeamMemberApi({
    teamId: currentTeam.value.id,
    userId: selectedUser.value,
    role: selectedRole.value
  }).then(() => {
    ElMessage.success("添加成员成功")
    // 关闭对话框
    addMemberDialogVisible.value = false
    // 重新获取成员列表
    getTeamMembers(currentTeam.value!.id)
    // 刷新团队列表（更新成员数量）
    getTableData()
    // 重置选择
    selectedUser.value = undefined
    selectedRole.value = "normal"
  }).catch((error) => {
    console.error("添加成员失败:", error)
    ElMessage.error("添加成员失败")
  })
}

// 移除成员
function handleRemoveMember(member: TeamMember) {
  ElMessageBox.confirm(`确认将 ${member.username} 从团队中移除吗？`, "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning"
  }).then(() => {
    if (!currentTeam.value || !currentTeam.value.id) {
      ElMessage.error("当前团队信息不存在")
      return
    }
    removeTeamMemberApi({
      teamId: currentTeam.value.id,
      memberId: member.userId
    }).then(() => {
      ElMessage.success("成员移除成功")
      // 重新获取成员列表
      if (currentTeam.value) {
        getTeamMembers(currentTeam.value.id)
      }
      getTableData()
    })
  })
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
</script>

<template>
  <div class="app-container">
    <el-card v-loading="loading" shadow="never" class="search-wrapper">
      <el-form ref="searchFormRef" :inline="true" :model="searchData">
        <el-form-item prop="name" label="团队名称">
          <el-input v-model="searchData.name" placeholder="请输入" />
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
        <el-table :data="tableData" @selection-change="handleSelectionChange" @sort-change="handleSortChange">
          <el-table-column type="selection" width="50" align="center" />
          <el-table-column prop="name" label="团队名称" align="center" sortable="custom"/>
          <el-table-column prop="ownerName" label="负责人" align="center" sortable="custom"/>
          <el-table-column prop="memberCount" label="成员数量" align="center" sortable="custom"/>
          <el-table-column prop="createTime" label="创建时间" align="center" sortable="custom"/>
          <el-table-column prop="updateTime" label="更新时间" align="center" sortable="custom"/>
          <el-table-column fixed="right" label="操作" width="220" align="center">
            <template #default="scope">
              <el-button type="success" text bg size="small" :icon="UserFilled" @click="handleManageMembers(scope.row)">
                成员管理
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

    <!-- 团队成员管理 -->
    <el-dialog
      v-model="memberDialogVisible"
      :title="`${currentTeam?.name || ''} - 成员管理`"
      width="50%"
    >
      <div v-if="currentTeam">
        <div class="team-info">
          <p><strong>团队名称：</strong>{{ currentTeam.name }}</p>
          <p><strong>负责人：</strong>{{ currentTeam.ownerName }}</p>
        </div>

        <div class="member-toolbar">
          <el-button type="primary" :icon="CirclePlus" size="small" @click="handleAddMember">
            添加成员
          </el-button>
        </div>

        <el-table :data="teamMembers" style="width: 100%" v-loading="memberLoading">
          <el-table-column prop="username" label="用户名" align="center" />
          <el-table-column prop="role" label="角色" align="center">
            <template #default="scope">
              {{ scope.row.role === 'owner' ? '拥有者' : (scope.row.role === 'normal' ? '普通成员' : scope.row.role) }}
            </template>
          </el-table-column>
          <el-table-column prop="joinTime" label="加入时间" align="center" />
          <el-table-column fixed="right" label="操作" width="150" align="center">
            <template #default="scope">
              <el-button
                type="danger"
                text
                bg
                size="small"
                @click="handleRemoveMember(scope.row)"
                :disabled="scope.row.role === 'owner'"
              >
                移除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="teamMembers.length === 0" class="empty-data">
          <el-empty description="暂无成员数据" />
        </div>
      </div>
      <template #footer>
        <el-button @click="memberDialogVisible = false">
          关闭
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加成员对话框 -->
    <el-dialog
      v-model="addMemberDialogVisible"
      title="添加团队成员"
      width="30%"
    >
      <div v-loading="userLoading">
        <el-form label-width="80px">
          <el-form-item label="选择用户">
            <!-- 修改 placeholder 属性，使其动态绑定 -->
            <el-select
              v-model="selectedUser"
              :placeholder="availableUsers.length > 0 ? '请选择用户' : '(当前无添加的用户数据)'"
              style="width: 100%"
              :disabled="availableUsers.length === 0"
            >
              <el-option
                v-for="user in availableUsers"
                :key="user.id"
                :label="user.username"
                :value="user.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="角色">
            <el-radio-group v-model="selectedRole">
              <el-radio label="normal">
                普通成员
              </el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="addMemberDialogVisible = false">
          取消
        </el-button>
        <el-button type="primary" @click="confirmAddMember" :disabled="!selectedUser">
          确认
        </el-button>
      </template>
    </el-dialog>
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

.team-info {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.member-toolbar {
  margin-bottom: 15px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.empty-data {
  margin-top: 20px;
  text-align: center;
}
</style>
