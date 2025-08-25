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

// 팀 데이터 구조
interface TeamData {
  id: number
  name: string
  ownerName: string
  memberCount: number
  createTime: string
  updateTime: string
}

// 팀 멤버 데이터 구조
interface TeamMember {
  userId: number
  username: string
  role: string
  joinTime: string
}

//  삭제
function handleDelete() {
  ElMessage.success("팀을 해산하려면, 팀장의 계정을 삭제하세요")
}

const tableData = ref<TeamData[]>([])

const searchData = reactive({
  name: ""
})

// 정렬 상태
const sortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc" // 默认排序顺序 (最新创建的在前)
})

// 다중 선택된 테이블 데이터 저장
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

// 테이블 다중 선택 이벤트 처리
function handleSelectionChange(selection: TeamData[]) {
  multipleSelection.value = selection
}
// 팀 멤버 관리 관련
const memberDialogVisible = ref<boolean>(false)
const currentTeam = ref<TeamData | null>(null)
const teamMembers = ref<TeamMember[]>([])
const memberLoading = ref<boolean>(false)
// 멤버 추가 관련 상태
const addMemberDialogVisible = ref<boolean>(false)
const userList = ref<{ id: number, username: string }[]>([])
const userLoading = ref<boolean>(false)
const selectedUser = ref<number | undefined>(undefined)
const selectedRole = ref<string>("normal")

// 계산 속성: 현재 팀 멤버가 아닌 추가 가능한 사용자 목록
const availableUsers = computed(() => {
  const memberUserIds = new Set(teamMembers.value.map(member => member.userId))
  return userList.value.filter(user => !memberUserIds.has(user.id))
})

function handleManageMembers(row: TeamData) {
  currentTeam.value = row
  memberDialogVisible.value = true
  getTeamMembers(row.id)
}

// 팀 멤버 목록 가져오기
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

// 멤버 추가
function handleAddMember() {
  // 멤버 추가 다이얼로그 열기
  addMemberDialogVisible.value = true
  // 获取可添加的用户列表
  getUserList()
}

// 사용자 목록 가져오기
function getUserList() {
  userLoading.value = true
  // getUsersApi 호출 시 size 파라미터로 전체 사용자 조회
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

// 멤버 추가 확인
function confirmAddMember() {
  if (!selectedUser.value) {
    ElMessage.warning("추가할 사용자를 선택하세요")
    return
  }

  if (!currentTeam.value) {
    ElMessage.error("현재 팀 정보가 없습니다")
    return
  }

  // 调用添加成员API
  addTeamMemberApi({
    teamId: currentTeam.value.id,
    userId: selectedUser.value,
    role: selectedRole.value
  }).then(() => {
    ElMessage.success("멤버가 성공적으로 추가되었습니다")
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
    console.error("멤버 추가 실패:", error)
    ElMessage.error("멤버 추가에 실패했습니다")
  })
}

// 멤버 제거
function handleRemoveMember(member: TeamMember) {
  ElMessageBox.confirm(`정말로 ${member.username}님을 팀에서 제거하시겠습니까?`, "알림", {
    confirmButtonText: "확인",
    cancelButtonText: "취소",
    type: "warning"
  }).then(() => {
    if (!currentTeam.value || !currentTeam.value.id) {
      ElMessage.error("현재 팀 정보가 없습니다")
      return
    }
    removeTeamMemberApi({
      teamId: currentTeam.value.id,
      memberId: member.userId
    }).then(() => {
      ElMessage.success("멤버가 성공적으로 제거되었습니다")
      // 멤버 목록 다시 가져오기
      if (currentTeam.value) {
        getTeamMembers(currentTeam.value.id)
      }
      getTableData()
    })
  })
}

/**
 * @description 테이블 정렬 변경 이벤트 처리(오름차순/내림차순만 허용)
 * @param {object} sortInfo 정렬 정보 객체, prop과 order 포함
 * @param {string} sortInfo.prop 정렬할 필드명
 * @param {string | null} sortInfo.order 정렬 순서('ascending', 'descending', null)
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

// 페이지네이션 파라미터 변경 감지
watch([() => paginationData.currentPage, () => paginationData.pageSize], getTableData, { immediate: true })
</script>

<template>
  <div class="app-container">
    <el-card v-loading="loading" shadow="never" class="search-wrapper">
      <el-form ref="searchFormRef" :inline="true" :model="searchData">
        <el-form-item prop="name" label="팀명">
          <el-input v-model="searchData.name" placeholder="입력하세요" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">
            조회
          </el-button>
          <el-button :icon="Refresh" @click="resetSearch">
            초기화
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-loading="loading" shadow="never">
      <div class="table-wrapper">
        <el-table :data="tableData" @selection-change="handleSelectionChange" @sort-change="handleSortChange">
          <el-table-column type="selection" width="50" align="center" />
          <el-table-column prop="name" label="팀명" align="center" sortable="custom"/>
          <el-table-column prop="ownerName" label="팀장" align="center" sortable="custom"/>
          <el-table-column prop="memberCount" label="멤버 수" align="center" sortable="custom"/>
          <el-table-column prop="createTime" label="생성일" align="center" sortable="custom"/>
          <el-table-column prop="updateTime" label="수정일" align="center" sortable="custom"/>
          <el-table-column fixed="right" label="작업" width="220" align="center">
            <template #default="scope">
              <el-button type="success" text bg size="small" :icon="UserFilled" @click="handleManageMembers(scope.row)">
                멤버 관리
              </el-button>
              <el-button type="danger" text bg size="small" @click="handleDelete()">
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

  <!-- 팀 멤버 관리 -->
    <el-dialog
      v-model="memberDialogVisible"
      :title="`${currentTeam?.name || ''} - 멤버 관리`"
      width="50%"
    >
      <div v-if="currentTeam">
        <div class="team-info">
          <p><strong>팀명: </strong>{{ currentTeam.name }}</p>
          <p><strong>팀장: </strong>{{ currentTeam.ownerName }}</p>
        </div>

        <div class="member-toolbar">
          <el-button type="primary" :icon="CirclePlus" size="small" @click="handleAddMember">
            멤버 추가
          </el-button>
        </div>

        <el-table :data="teamMembers" style="width: 100%" v-loading="memberLoading">
          <el-table-column prop="username" label="사용자명" align="center" />
          <el-table-column prop="role" label="역할" align="center">
            <template #default="scope">
              {{ scope.row.role === 'owner' ? '팀장' : (scope.row.role === 'normal' ? '일반 멤버' : scope.row.role) }}
            </template>
          </el-table-column>
          <el-table-column prop="joinTime" label="가입일" align="center" />
          <el-table-column fixed="right" label="작업" width="150" align="center">
            <template #default="scope">
              <el-button
                type="danger"
                text
                bg
                size="small"
                @click="handleRemoveMember(scope.row)"
                :disabled="scope.row.role === 'owner'"
              >
                제거
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="teamMembers.length === 0" class="empty-data">
          <el-empty description="멤버 데이터가 없습니다" />
        </div>
      </div>
      <template #footer>
        <el-button @click="memberDialogVisible = false">
          닫기
        </el-button>
      </template>
    </el-dialog>

  <!-- 멤버 추가 다이얼로그 -->
    <el-dialog
      v-model="addMemberDialogVisible"
      title="팀 멤버 추가"
      width="30%"
    >
      <div v-loading="userLoading">
        <el-form label-width="80px">
          <el-form-item label="사용자 선택">
            <!-- placeholder 속성 동적 바인딩 -->
            <el-select
              v-model="selectedUser"
              :placeholder="availableUsers.length > 0 ? '사용자를 선택하세요' : '(추가 가능한 사용자가 없습니다)'"
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
          <el-form-item label="역할">
            <el-radio-group v-model="selectedRole">
              <el-radio label="normal">
                일반 멤버
              </el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="addMemberDialogVisible = false">
          취소
        </el-button>
        <el-button type="primary" @click="confirmAddMember" :disabled="!selectedUser">
          확인
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
