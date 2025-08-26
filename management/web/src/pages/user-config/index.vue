<script lang="ts" setup>
import type { TableData } from "@@/apis/configs/type"
import type { FormInstance } from "element-plus"
import { getTableDataApi } from "@@/apis/configs"
import { usePagination } from "@@/composables/usePagination"
import { Refresh, Search } from "@element-plus/icons-vue"

defineOptions({
  // 현재 컴포넌트 이름 지정
  name: "UserConfig"
})

const loading = ref<boolean>(false)
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination()

// #region 추가
// const DEFAULT_FORM_DATA: CreateOrUpdateTableRequestData = {
//   id: undefined,
//   username: "",
//   chatModel: "",
//   embeddingModel: ""
// }
// const dialogVisible = ref<boolean>(false)
// const formData = ref<CreateOrUpdateTableRequestData>(cloneDeep(DEFAULT_FORM_DATA))

// 삭제 응답
function handleDelete() {
  ElMessage.success("사용자 설정 정보를 삭제하려면, 프론트에서 해당 사용자 계정으로 로그인하여 진행하세요")
}

// 수정
function handleUpdate() {
  ElMessage.success("사용자 설정 정보를 수정하려면, 프론트에서 해당 사용자 계정으로 로그인하여 진행하세요")
}

// 수정 폼 제출 처리
// function submitForm() {
//   loading.value = true
//   updateTableDataApi(formData.value)
//     .then(() => {
//       ElMessage.success("수정이 완료되었습니다")
//       dialogVisible.value = false
//       getTableData() // 테이블 데이터 새로고침
//     })
//     .catch(() => {
//       ElMessage.error("수정에 실패했습니다")
//     })
//     .finally(() => {
//       loading.value = false
//     })
// }

// 조회
const tableData = ref<TableData[]>([])
const searchFormRef = ref<FormInstance | null>(null)
const searchData = reactive({
  username: ""
})

// 다중 선택된 테이블 데이터 저장
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

// 페이지네이션 파라미터 변경 감지
watch([() => paginationData.currentPage, () => paginationData.pageSize], getTableData, { immediate: true })

// 페이지가 마운트되거나 활성화될 때 데이터 가져오기
onMounted(() => {
  getTableData()
})

// 다른 페이지에서 돌아올 때 데이터 새로고침
onActivated(() => {
  getTableData()
})
</script>

<template>
  <div class="app-container">
    <el-card v-loading="loading" shadow="never" class="search-wrapper">
      <el-form ref="searchFormRef" :inline="true" :model="searchData">
        <el-form-item prop="username" label="사용자명">
          <el-input v-model="searchData.username" placeholder="입력하세요" />
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
        <el-table :data="tableData" @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="50" align="center" />
          <el-table-column prop="username" label="사용자명" align="center" />
          <el-table-column prop="chatModel" label="채팅 모델" align="center" />
          <el-table-column prop="embeddingModel" label="임베딩 모델" align="center" />
          <el-table-column prop="updateTime" label="수정일" align="center" />
          <el-table-column fixed="right" label="작업" width="150" align="center">
            <template #default="">
              <el-button type="primary" text bg size="small" @click="handleUpdate">
                수정
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

  <!-- 수정 다이얼로그 -->
    <!-- <el-dialog v-model="dialogVisible" title="설정 수정" width="30%">
      <el-form :model="formData" label-width="100px">
        <el-form-item label="사용자명">
          <el-input v-model="formData.username" disabled />
        </el-form-item>
        <el-form-item label="채팅 모델">
          <el-input v-model="formData.chatModel" />
        </el-form-item>
        <el-form-item label="임베딩 모델">
          <el-input v-model="formData.embeddingModel" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">
          취소
        </el-button>
        <el-button type="primary" @click="submitForm">
          확인
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
