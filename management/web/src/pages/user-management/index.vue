<script lang="ts" setup>
import type { CreateOrUpdateTableRequestData, TableData } from "@@/apis/tables/type"
import type { FormInstance, FormRules } from "element-plus"
import { createTableDataApi, deleteTableDataApi, getTableDataApi, resetPasswordApi, updateTableDataApi } from "@@/apis/tables"
import { usePagination } from "@@/composables/usePagination"
import { CirclePlus, Delete, Edit, Key, Refresh, RefreshRight, Search } from "@element-plus/icons-vue"
import { cloneDeep } from "lodash-es"

defineOptions({
  // 현재 컴포넌트 이름 지정
  name: "UserManagement"
})

const loading = ref<boolean>(false)
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination()

// #region 추가
const DEFAULT_FORM_DATA: CreateOrUpdateTableRequestData = {
  id: undefined,
  username: "",
  email: "",
  password: ""
}
const dialogVisible = ref<boolean>(false)
const formRef = ref<FormInstance | null>(null)
const formData = ref<CreateOrUpdateTableRequestData>(cloneDeep(DEFAULT_FORM_DATA))
const formRules: FormRules<CreateOrUpdateTableRequestData> = {
  username: [{ required: true, trigger: "blur", message: "사용자 이름을 입력하세요" }],
  email: [
    { required: true, trigger: "blur", message: "이메일을 입력하세요" },
    {
      type: "email",
      message: "올바른 이메일 형식을 입력하세요",
      trigger: ["blur", "change"]
    }
  ],
  password: [{ required: true, trigger: "blur", message: "비밀번호를 입력하세요" }]
}
// #region 비밀번호 재설정
const resetPasswordDialogVisible = ref<boolean>(false)
const resetPasswordFormRef = ref<FormInstance | null>(null)
const currentUserId = ref<string | undefined>(undefined) // 현재 비밀번호를 재설정할 사용자의 ID 저장
const resetPasswordFormData = reactive({
  password: ""
})
const resetPasswordFormRules: FormRules = {
  password: [
    { required: true, message: "새 비밀번호를 입력하세요", trigger: "blur" }
  ]
}
// #endregion
function handleCreateOrUpdate() {
  formRef.value?.validate((valid) => {
    if (!valid) {
      ElMessage.error("로그인 검증에 실패했습니다")
      return
    }
    loading.value = true
    const api = formData.value.id === undefined ? createTableDataApi : updateTableDataApi
    api(formData.value).then(() => {
      ElMessage.success("작업이 성공적으로 완료되었습니다")
      dialogVisible.value = false
      getTableData()
    }).finally(() => {
      loading.value = false
    })
  })
}
function resetForm() {
  formRef.value?.clearValidate()
  formData.value = cloneDeep(DEFAULT_FORM_DATA)
}
// #endregion

// #region 비밀번호 재설정 처리
/**
 * 비밀번호 재설정 다이얼로그 열기
 * @param {TableData} row - 현재 행의 사용자 데이터
 */
function handleResetPassword(row: TableData) {
  currentUserId.value = row.id
  resetPasswordFormData.password = "" // 이전 입력값 초기화
  resetPasswordDialogVisible.value = true
  // 이전 검증 상태 초기화
  nextTick(() => {
    resetPasswordFormRef.value?.clearValidate()
  })
}

/**
 * 비밀번호 재설정 폼 제출
 */
function submitResetPassword() {
  resetPasswordFormRef.value?.validate((valid) => {
    if (!valid) {
      ElMessage.error("폼 검증에 실패했습니다")
      return
    }
    if (currentUserId.value === undefined) {
      ElMessage.error("사용자 ID가 없어 비밀번호를 재설정할 수 없습니다")
      return
    }
    loading.value = true
    // 백엔드 API 호출로 비밀번호 재설정
    resetPasswordApi(currentUserId.value, resetPasswordFormData.password)
      .then(() => {
        ElMessage.success("비밀번호가 성공적으로 재설정되었습니다")
        resetPasswordDialogVisible.value = false
      })
      .catch((error: any) => {
        console.error("비밀번호 재설정 실패:", error)
        ElMessage.error("비밀번호 재설정에 실패했습니다")
      })
      .finally(() => {
        loading.value = false
      })
  })
}

/**
 * 비밀번호 재설정 다이얼로그 닫을 때 상태 초기화
 */
function resetPasswordDialogClosed() {
  currentUserId.value = undefined
  resetPasswordFormRef.value?.resetFields() // 폼 필드 초기화
}
// #endregion

// #region 삭제
function handleDelete(row: TableData) {
  ElMessageBox.confirm(`사용자: ${row.username}을(를) 삭제 중입니다. 삭제하시겠습니까?`, "알림", {
    confirmButtonText: "확인",
    cancelButtonText: "취소",
    type: "warning"
  }).then(() => {
    deleteTableDataApi(row.id).then(() => {
      ElMessage.success("삭제가 완료되었습니다")
      getTableData()
    })
  })
}
// #endregion

// #region 수정
function handleUpdate(row: TableData) {
  dialogVisible.value = true
  formData.value = cloneDeep(row)
}
// #endregion

// #region 조회
const tableData = ref<TableData[]>([])
const searchFormRef = ref<FormInstance | null>(null)
const searchData = reactive({
  username: "",
  email: ""
})

// 정렬 상태
const sortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc" // 기본 정렬 순서 (최신 생성순)
})

// 다중 선택된 테이블 데이터 저장
const multipleSelection = ref<TableData[]>([])

function getTableData() {
  loading.value = true
  getTableDataApi({
    currentPage: paginationData.currentPage,
    size: paginationData.pageSize,
    username: searchData.username,
    email: searchData.email,
    sort_by: sortData.sortBy,
    sort_order: sortData.sortOrder
  }).then(({ data }) => {
    paginationData.total = data.total
    tableData.value = data.list
    // 선택된 데이터 초기화
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

// 테이블 다중 선택 이벤트 처리
function handleSelectionChange(selection: TableData[]) {
  multipleSelection.value = selection
}

// 일괄 삭제 메서드
function handleBatchDelete() {
  if (multipleSelection.value.length === 0) {
    ElMessage.warning("최소 한 개의 레코드를 선택하세요")
    return
  }
  ElMessageBox.confirm(`선택한 ${multipleSelection.value.length}개의 레코드를 삭제하시겠습니까?`, "알림", {
    confirmButtonText: "확인",
    cancelButtonText: "취소",
    type: "warning"
  }).then(async () => {
    loading.value = true
    try {
      // 여러 삭제 요청을 병렬로 처리
      await Promise.all(
        multipleSelection.value.map(row => deleteTableDataApi(row.id))
      )
      ElMessage.success("일괄 삭제가 완료되었습니다")
      getTableData()
    } catch {
      ElMessage.error("일괄 삭제에 실패했습니다")
    } finally {
      loading.value = false
    }
  })
}
// #endregion

/**
 * @description 테이블 정렬 변경 이벤트 처리(오름차순/내림차순만 허용)
 * @param {object} sortInfo 정렬 정보 객체, prop과 order 포함
 * @param {string} sortInfo.prop 정렬할 필드명
 * @param {string | null} sortInfo.order 정렬 순서('ascending', 'descending', null)
 */
function handleSortChange({ prop }: { prop: string, order: string | null }) {
  // 같은 필드를 클릭하면 정렬 순서 변경
  if (sortData.sortBy === prop) {
    // 현재가 오름차순이면 내림차순으로, 아니면 오름차순으로
    sortData.sortOrder = sortData.sortOrder === "asc" ? "desc" : "asc"
  } else {
    // 필드 변경 시 기본 오름차순
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
        <el-form-item prop="username" label="사용자명">
          <el-input v-model="searchData.username" placeholder="입력하세요" />
        </el-form-item>
        <el-form-item prop="email" label="이메일">
          <el-input v-model="searchData.email" placeholder="입력하세요" />
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
      <div class="toolbar-wrapper">
        <div>
          <el-button type="primary" :icon="CirclePlus" @click="dialogVisible = true">
            사용자 추가
          </el-button>
          <el-button type="danger" :icon="Delete" @click="handleBatchDelete">
            일괄 삭제
          </el-button>
        </div>
        <div>
          <el-tooltip content="현재 페이지 새로고침">
            <el-button type="primary" :icon="RefreshRight" circle @click="getTableData" />
          </el-tooltip>
        </div>
      </div>
      <div class="table-wrapper">
        <el-table :data="tableData" @selection-change="handleSelectionChange" @sort-change="handleSortChange">
          <el-table-column type="selection" width="50" align="center" />
          <el-table-column prop="username" label="사용자명" align="center" sortable="custom" />
          <el-table-column prop="email" label="이메일" align="center" sortable="custom" />
          <el-table-column prop="createTime" label="생성일" align="center" sortable="custom" />
          <el-table-column prop="updateTime" label="수정일" align="center" sortable="custom" />
          <el-table-column fixed="right" label="작업" width="300" align="center">
            <template #default="scope">
              <el-button type="primary" text bg size="small" :icon="Edit" @click="handleUpdate(scope.row)">
                사용자명 수정
              </el-button>
              <el-button type="warning" text bg size="small" :icon="Key" @click="handleResetPassword(scope.row)">
                비밀번호 재설정
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
    <!-- 추가/수정 -->
    <el-dialog
      v-model="dialogVisible"
      :title="formData.id === undefined ? '사용자 추가' : '사용자 수정'"
      width="30%"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px" label-position="left">
        <el-form-item prop="username" label="사용자명">
          <el-input v-model="formData.username" placeholder="입력하세요" />
        </el-form-item>
        <el-form-item v-if="formData.id === undefined" prop="email" label="이메일">
          <el-input v-model="formData.email" placeholder="입력하세요" />
        </el-form-item>
        <el-form-item v-if="formData.id === undefined" prop="password" label="비밀번호">
          <el-input v-model="formData.password" placeholder="입력하세요" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">
          취소
        </el-button>
        <el-button type="primary" :loading="loading" @click="handleCreateOrUpdate">
          확인
        </el-button>
      </template>
    </el-dialog>

    <!-- 비밀번호 재설정 다이얼로그 -->
    <el-dialog
      v-model="resetPasswordDialogVisible"
      title="비밀번호 재설정"
      width="30%"
      @closed="resetPasswordDialogClosed"
    >
      <el-form ref="resetPasswordFormRef" :model="resetPasswordFormData" :rules="resetPasswordFormRules" label-width="100px" label-position="left">
        <el-form-item prop="password" label="새 비밀번호">
          <el-input v-model="resetPasswordFormData.password" type="password" show-password placeholder="새 비밀번호를 입력하세요" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPasswordDialogVisible = false">
          취소
        </el-button>
        <el-button type="primary" :loading="loading" @click="submitResetPassword">
          재설정 확인
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
</style>
