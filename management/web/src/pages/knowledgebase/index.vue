<script lang="ts" setup>
import type { SequentialBatchTaskProgress } from "@@/apis/kbs/document"
import type { FormInstance, UploadFile, UploadProps } from "element-plus"
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
  getKbDetailApi,
  getKnowledgeBaseListApi,
  getKnowledgeBaseEmbeddingConfigApi,
  getSystemEmbeddingConfigApi,
  setSystemEmbeddingConfigApi,
  updateKnowledgeBaseApi,
  loadingEmbeddingModelsApi
} from "@@/apis/kbs/knowledgebase"
import { getTableDataApi } from "@@/apis/tables"
import { usePagination } from "@@/composables/usePagination"
import { CaretRight, Delete, Edit, Loading, Plus, Refresh, Search, Setting, View } from "@element-plus/icons-vue"

import axios from "axios"
import { ElMessage, ElMessageBox } from "element-plus"
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from "vue"
import "element-plus/dist/index.css"
import "element-plus/theme-chalk/el-message-box.css"

import "element-plus/theme-chalk/el-message.css"

defineOptions({
  // 현재 컴포넌트 이름 지정
  name: "KnowledgeBase"
})

const loading = ref<boolean>(false)
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination()
const createDialogVisible = ref(false)
const uploadLoading = ref(false)
const showParseProgress = ref(false)
const currentDocId = ref("")

// 리소스 정리 함수 추가
function cleanupResources() {
  // 모든 상태 초기화
  if (multipleSelection.value) {
    multipleSelection.value = []
  }

  loading.value = false
  documentLoading.value = false
  fileLoading.value = false
  uploadLoading.value = false

  // 모든 다이얼로그 닫기
  viewDialogVisible.value = false
  createDialogVisible.value = false
  addDocumentDialogVisible.value = false
  showParseProgress.value = false
}

// 컴포넌트 비활성화 시 리소스 정리
onDeactivated(() => {
  cleanupResources()
})

// 컴포넌트 언마운트 전 리소스 정리
onBeforeUnmount(() => {
  cleanupResources()
})

// 지식베이스 데이터 타입 정의
interface KnowledgeBaseData {
  id: string
  name: string
  embd_id?: string
  created_by?:string
  nickname?: string
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

// 새 지식베이스 폼
const knowledgeBaseForm = reactive({
  name: "",
  description: "",
  language: "Chinese",
  permission: "me",
  creator_id: ""
})

// API 반환 데이터 인터페이스 정의
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

// 폼 검증 규칙
const knowledgeBaseFormRules = {
  name: [
    { required: true, message: "지식베이스 이름을 입력하세요", trigger: "blur" },
    { min: 2, max: 50, message: "길이는 2~50자여야 합니다", trigger: "blur" }
  ],
  description: [
    { max: 200, message: "설명은 200자를 초과할 수 없습니다", trigger: "blur" }
  ],
  creator_id: [
    { required: true, message: "생성자를 선택하세요", trigger: "change" }
  ]
}

const knowledgeBaseFormRef = ref<FormInstance | null>(null)

// 지식베이스 목록 조회
const tableData = ref<KnowledgeBaseData[]>([])
const searchFormRef = ref<FormInstance | null>(null)
const searchData = reactive({
  name: ""
})

// 정렬 상태
const sortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc" // 기본 정렬 순서
})

// 문서 목록 정렬 상태
const docSortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc" // 기본 정렬 순서
})

// 파일 목록 정렬 상태
const fileSortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc" // 기본 정렬 순서
})

const editDialogVisible = ref(false)
const editForm = reactive({
  id: "",
  name: "",
  permission: "me",
  avatar: "",
  embd_id: ""
})
const editLoading = ref(false)

// // 지식베이스 수정 처리
// function handleEdit(row: KnowledgeBaseData) {
//   editDialogVisible.value = true
//   editForm.id = row.id
//   editForm.name = row.name
//   editForm.permission = row.permission
// }

// 완전한 데이터 가져오기용
async function handleEdit(row: KnowledgeBaseData) {
  editDialogVisible.value = true
  editLoading.value = true
  try {
    const { data } = await getKbDetailApi(row.id)
    editForm.id = data.id
    editForm.name = data.name
    editForm.permission = row.permission
    editForm.embd_id = row.embd_id || ""
    // 백엔드에서 반환된 base64에 접두사가 없으면 수동으로 추가
    if (data.avatar && !data.avatar.startsWith("data:image")) {
      editForm.avatar = `data:image/jpeg;base64,${data.avatar}`
    } else {
      editForm.avatar = data.avatar || ""
    }
  } catch (error: any) {
    ElMessage.error(`지식베이스 상세 정보 가져오기 실패: ${error?.message || "알 수 없는 오류"}`)
    editDialogVisible.value = false // 실패 시 다이얼로그 닫기
  } finally {
    editLoading.value = false
  }
}

// 수정 제출
function submitEdit() {
  editLoading.value = true
  console.log("수정할 지식베이스 데이터 제출:", editForm)
  // 제출할 데이터 준비
  const payload: { permission: string, avatar?: string ,embd_id?:string} = {
    permission: editForm.permission,
    embd_id: editForm.embd_id 
  }

  // 새 아바타 데이터가 있으면 순수 Base64 부분 추출
  if (editForm.avatar && editForm.avatar.startsWith("data:image")) {
    payload.avatar = editForm.avatar.split(",")[1]
  }

  // 가져온 API 함수 사용
  updateKnowledgeBaseApi(editForm.id, payload)
    .then(() => {
      ElMessage.success("지식베이스 정보가 성공적으로 수정되었습니다")
      editDialogVisible.value = false
      getTableData() // 지식베이스 목록 새로고침
    })
    .catch((error: any) => {
      ElMessage.error(`지식베이스 수정 실패: ${error?.message || "알 수 없는 오류"}`)
    })
    .finally(() => {
      editLoading.value = false
    })
}

const handleAvatarChange: UploadProps["onChange"] = (uploadFile: UploadFile) => {
  if (!uploadFile.raw) return
  if (!uploadFile.raw.type.includes("image")) {
    ElMessage.error("이미지 형식의 파일을 업로드하세요!")
    return false
  }
  // 업로드 파일 크기 제한
  const isLt2M = uploadFile.raw.size / 1024 / 1024 < 2
  if (!isLt2M) {
    ElMessage.error("업로드하는 아바타 이미지 크기는 2MB를 초과할 수 없습니다!")
    return false
  }

  const reader = new FileReader()
  reader.readAsDataURL(uploadFile.raw)
  reader.onload = () => {
    editForm.avatar = reader.result as string
  }
}

// 다중 선택된 테이블 데이터 저장
const multipleSelection = ref<KnowledgeBaseData[]>([])

// 지식베이스 목록 데이터 가져오기
function getTableData() {
  loading.value = true
  // 지식베이스 목록 가져오기 API 호출
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
    // 선택된 데이터 초기화
    multipleSelection.value = []
  }).catch(() => {
    tableData.value = []
  }).finally(() => {
    loading.value = false
  })
}

// 검색 처리
function handleSearch() {
  paginationData.currentPage === 1 ? getTableData() : (paginationData.currentPage = 1)
}

// 검색 초기화
function resetSearch() {
  searchFormRef.value?.resetFields()
  handleSearch()
}

// 새 지식베이스 다이얼로그 열기
function handleCreate() {
  createDialogVisible.value = true
  getUserList() // 사용자 목록 가져오기
}

// 사용자 목록 가져오기
function getUserList() {
  userLoading.value = true
  // 사용자 관리 페이지의 API 재사용
  getTableDataApi({
    currentPage: 1,
    size: 1000, // 충분한 수의 사용자 가져오기
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
    ElMessage.error("사용자 목록 가져오기 실패")
  }).finally(() => {
    userLoading.value = false
  })
}

// 새 지식베이스 제출
async function submitCreate() {
  if (!knowledgeBaseFormRef.value) return

  await knowledgeBaseFormRef.value.validate(async (valid) => {
    if (valid) {
      uploadLoading.value = true
      try {
        // 시스템 레벨 임베딩 설정을 읽어 llm_name을 embd_id로 가져오기
        const res = await getSystemEmbeddingConfigApi() as ApiResponse<{ llm_name?: string }>
        const embdId = res?.data?.llm_name ? String(res.data.llm_name).trim() : ""

        if (!embdId) {
          ElMessage.error("시스템 임베딩 모델 설정이 감지되지 않았습니다. 먼저 '임베딩 모델 설정'에서 설정을 완료해주세요")
          return
        }

        const payload = {
          name: knowledgeBaseForm.name,
          description: knowledgeBaseForm.description,
          language: knowledgeBaseForm.language,
          permission: knowledgeBaseForm.permission,
          creator_id: knowledgeBaseForm.creator_id,
          embd_id: embdId
        }

        await createKnowledgeBaseApi(payload)
        ElMessage.success("지식베이스 생성 성공")
        getTableData()
        createDialogVisible.value = false
        // 폼 초기화
        knowledgeBaseFormRef.value?.resetFields()
      } catch (error: unknown) {
        let errorMessage = "생성 실패"
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

// 지식베이스 상세 정보 보기
const viewDialogVisible = ref(false)
const batchParsingLoading = ref(false) // 일괄 파싱 로딩 상태
const currentKnowledgeBase = ref<KnowledgeBaseData | null>(null)
const documentLoading = ref(false)
const documentList = ref<any[]>([])

// 순차 일괄 작업 폴링 관련 상태
const batchPollingInterval = ref<NodeJS.Timeout | null>(null) // 타이머 ID
const isBatchPolling = ref(false) // 일괄 작업 폴링 중인지 여부
const batchProgress = ref<SequentialBatchTaskProgress | null>(null) // 일괄 작업 진행 정보 저장
// 일괄 파싱 버튼 비활성화 여부 계산
const isBatchParseDisabled = computed(() => {
  // 일괄 작업 폴링 중이면 비활성화
  if (isBatchPolling.value) return true
  // 문서 목록이 비어있거나 모든 문서가 완료되면 비활성화
  if (!documentList.value || documentList.value.length === 0) return true
  return documentList.value.every(doc => doc.status === "3")
})

// 문서 목록 페이지네이션
const docPaginationData = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0,
  pageSizes: [10, 20, 50, 100],
  layout: "total, sizes, prev, pager, next, jumper"
})

// 문서 페이지네이션 변경 처리
function handleDocCurrentChange(page: number) {
  docPaginationData.currentPage = page
  getDocumentList()
}

function handleDocSizeChange(size: number) {
  docPaginationData.pageSize = size
  docPaginationData.currentPage = 1
  getDocumentList()
}

// 지식베이스 하위 문서 목록 가져오기
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
    ElMessage.error(`문서 목록 가져오기 실패: ${error?.message || "알 수 없는 오류"}`)
    documentList.value = []
  }).finally(() => {
    documentLoading.value = false
  })
}

/**
 * @description 문서 테이블 정렬 변경 이벤트 처리
 * @param {object} sortInfo 정렬 정보 객체, prop과 order 포함
 * @param {string} sortInfo.prop 정렬할 필드명
 * @param {string | null} sortInfo.order 정렬 순서('ascending', 'descending', null)
 */
function handleDocSortChange({ prop }: { prop: string, order: string | null }) {
  // 같은 필드를 클릭하면 정렬 순서 전환
  if (docSortData.sortBy === prop) {
    // 현재 오름차순이면 내림차순으로, 아니면 오름차순으로 전환
    docSortData.sortOrder = docSortData.sortOrder === "asc" ? "desc" : "asc"
  } else {
    // 필드 전환 시 기본 오름차순
    docSortData.sortBy = prop
    docSortData.sortOrder = "asc"
  }
  getDocumentList()
}

// handleView 메서드 수정
function handleView(row: KnowledgeBaseData) {
  currentKnowledgeBase.value = row
  viewDialogVisible.value = true
  // 문서 페이지네이션 초기화
  docPaginationData.currentPage = 1
  batchProgress.value = null
  // 문서 목록 가져오기
  getDocumentList()
}

// 파싱 상태 포맷팅
function formatParseStatus(progress: number) {
  if (progress === 0) return "미파싱"
  if (progress === 1) return "완료"
  return `파싱 중 ${Math.floor(progress * 100)}%`
}

// 파싱 상태에 대응하는 태그 타입 가져오기
function getParseStatusType(progress: number) {
  if (progress === 0) return "info"
  if (progress === 1) return "success"
  return "warning"
}

// handleParseDocument 메서드
function handleParseDocument(row: any) {
  // 먼저 파싱이 완료되었는지 확인
  if (row.progress === 1) {
    ElMessage.warning("문서가 이미 파싱 완료되었습니다. 중복 파싱할 필요가 없습니다")
    return
  }

  ElMessageBox.confirm(
    `문서 "${row.name}"을(를) 파싱하시겠습니까?`,
    "파싱 확인",
    {
      confirmButtonText: "확인",
      cancelButtonText: "취소",
      type: "info"
    }
  ).then(() => {
    // 즉시 진행상황 다이얼로그 표시
    currentDocId.value = row.id
    showParseProgress.value = true
    
    // DOM 업데이트 후 요청 발생을 위해 nextTick 사용
    nextTick(() => {
      // 파싱 요청 발생(fire-and-forget 모드)
      runDocumentParseApi(row.id).catch((error) => {
        ElMessage.error(`파싱 작업 제출 실패: ${error?.message || "알 수 없는 오류"}`)
        // 제출 실패 시 진행상황 다이얼로그 닫기
        showParseProgress.value = false
      })
    })
    
    // "파싱 중" 상태 표시를 위해 문서 목록 지연 새로고침
    setTimeout(getDocumentList, 1500)
  }).catch(() => {
    // 사용자 취소 작업
  })
}

// 일괄 문서 파싱 처리 (동기 API 호출)
function handleBatchParse() {
  if (!currentKnowledgeBase.value) return

  const kbId = currentKnowledgeBase.value.id
  const kbName = currentKnowledgeBase.value.name

  ElMessageBox.confirm(
    `지식베이스 "${kbName}"에 대해 백그라운드 일괄 파싱을 시작하시겠습니까?<br><strong style="color: #E6A23C;">이 과정은 백그라운드에서 실행되며, 나중에 결과를 확인하거나 이 창을 닫을 수 있습니다.</strong>`,
    "일괄 파싱 시작 확인",
    {
      confirmButtonText: "시작 확인",
      cancelButtonText: "취소",
      type: "warning",
      dangerouslyUseHTMLString: true // HTML 태그 사용 허용
    }
  ).then(async () => {
    batchParsingLoading.value = true // '시작 중' 상태 표시
    batchProgress.value = null
    try {
      const res = await startSequentialBatchParseAsyncApi(kbId)

      if (res.code === 0 && res.data) {
        // 백엔드에서 시작 요청을 성공적으로 받음
        ElMessage.success(res.data.message || `일괄 파싱 작업이 성공적으로 시작되었습니다`)
        // --- 핵심: 진행상황 모니터링을 위한 폴링 시작 ---
        startBatchPolling()
        // 시작 후 약간의 지연 후에 목록을 새로고침하여 '파싱 중' 상태를 표시 시도
        setTimeout(getDocumentList, 1500)
      } else {
        // 시작 API 자체 호출 실패 또는 백엔드가 오류 반환
        const errorMsg = res.data?.message || res.message || "일괄 파싱 작업 시작 실패"
        ElMessage.error(errorMsg)
        batchParsingLoading.value = false // 시작 실패, '시작 중' 상태 취소
      }
    } catch (error: any) {
      // 시작 API 요청 시 네트워크 오류 또는 기타 예외 발생
      ElMessage.error(`일괄 파싱 작업 시작 중 오류 발생: ${error?.message || "네트워크 오류"}`)
      console.error("일괄 파싱 작업 시작 실패:", error)
      batchParsingLoading.value = false // 시작 예외, '시작 중' 상태 취소
    } finally {
      // '성공적으로' 폴링을 시작하지 못한 경우에만 batchParsingLoading을 false로 설정
      // 폴링이 시작된 경우 isBatchPolling 상태가 버튼과 인터페이스 표시를 제어함
      if (!isBatchPolling.value) {
        batchParsingLoading.value = false
      }
    }
  }).catch(() => {
    // 사용자가 '취소' 버튼을 클릭함
    ElMessage.info("일괄 파싱 작업이 취소되었습니다")
  })
}
// 일괄 작업 진행률 폴링 시작
function startBatchPolling() {
  // 이미 폴링 중이거나 현재 지식베이스가 없으면 실행하지 않음
  if (isBatchPolling.value || !currentKnowledgeBase.value) return

  console.log("지식베이스 일괄 파싱 진행률 폴링 시작:", currentKnowledgeBase.value.id)
  isBatchPolling.value = true
  // 사용자에게 즉시 피드백을 제공하기 위한 초기 상태 설정
  batchProgress.value = { status: "running", message: "일괄 파싱 작업을 시작하는 중...", total: 0, current: 0 }

  // 혹시 모를 기존 타이머가 있다면 먼저 정리
  if (batchPollingInterval.value) {
    clearInterval(batchPollingInterval.value)
  }

  // 즉시 한 번 진행률을 가져온 후 타이머 설정
  fetchBatchProgress()
  batchPollingInterval.value = setInterval(fetchBatchProgress, 5000) // 5초마다 진행률 조회
}

// 일괄 작업 진행률 폴링 중지
function stopBatchPolling() {
  if (batchPollingInterval.value) {
    console.log("일괄 파싱 진행률 폴링을 중지합니다.")
    clearInterval(batchPollingInterval.value)
    batchPollingInterval.value = null
  }
  // 표시를 위한 마지막 상태 정보 유지
  isBatchPolling.value = false
  batchParsingLoading.value = false
}

// 일괄 작업 진행률 가져오기 및 업데이트
async function fetchBatchProgress() {
  // 상세 대화상자가 닫혔거나 현재 지식베이스가 없으면 폴링 중지
  if (!currentKnowledgeBase.value || !viewDialogVisible.value) {
    stopBatchPolling()
    return
  }

  try {
    // 진행률 가져오기 API 호출
    const res = await getSequentialBatchParseProgressApi(currentKnowledgeBase.value.id)

    if (res.code === 0 && res.data) {
      // 진행률 상태 업데이트
      batchProgress.value = res.data
      console.log("일괄 진행률 가져옴:", batchProgress.value)

      if (batchProgress.value.status === "running") {
        getDocumentList()
      }

      // 작업이 완료되었거나 실패했는지 확인
      if (batchProgress.value.status === "completed" || batchProgress.value.status === "failed") {
        stopBatchPolling() // 폴링 중지
        // 최종 결과 메시지 표시
        ElMessage({
          message: batchProgress.value.message || (batchProgress.value.status === "completed" ? "일괄 파싱이 완료되었습니다" : "일괄 파싱이 실패했습니다"),
          type: batchProgress.value.status === "completed" ? "success" : "error"
        })
        // 최신 상태를 표시하기 위해 문서 목록 새로고침
        getDocumentList()
        // 지식베이스 목록 새로고침 (문서 수, 청크 수가 변경될 수 있음)
        getTableData()
      }
    } else {
      // API 호출은 성공했지만 오류 코드가 반환되었거나 데이터가 없음
      console.error("일괄 진행률 가져오기 실패:", res.message || res.data?.message)
      // 인터페이스에서 진행률 가져오기 중 문제가 발생했음을 알릴 수 있음
      if (batchProgress.value) { // batchProgress가 null이 아닌지 확인
        batchProgress.value.message = `진행률 가져오기 중 오류: ${res.message || "잠시 후 다시 시도해주세요..."}`
      }
    }
  } catch (error: any) {
    // 네트워크 오류 또는 기타 요청 예외
    console.error("일괄 진행률 API 요청 실패:", error)
    // 인터페이스에서 네트워크 문제를 알릴 수 있음
    if (batchProgress.value) { // batchProgress가 null이 아닌지 확인
      batchProgress.value.message = `진행률 가져오기 중 네트워크 오류: ${error.message || "네트워크 연결을 확인해주세요..."}`
    }
    // 정책에 따라 폴링을 중지할지 결정, 예: 연속으로 여러 번 실패 후 중지
    // stopBatchPolling();
  }
}

// 파싱 완료 및 실패 처리 함수 추가
function handleParseComplete() {
  ElMessage.success("문서 파싱이 완료되었습니다")
  getDocumentList() // 문서 목록 새로고침
  getTableData() // 지식베이스 목록 새로고침
}

function handleParseFailed(error: string) {
  ElMessage.error(`문서 파싱 실패: ${error || "알 수 없는 오류"}`)
  getDocumentList() // 상태 업데이트를 위해 문서 목록 새로고침
}

// 문서 제거 처리
function handleRemoveDocument(row: any) {
  ElMessageBox.confirm(
    `지식베이스에서 문서 "${row.name}"을(를) 제거하시겠습니까?<br><span style="color: #909399; font-size: 12px;">이 작업은 지식베이스 파일만 제거하며, 원본 파일은 삭제되지 않습니다</span>`,
    "제거 확인",
    {
      confirmButtonText: "확인",
      cancelButtonText: "취소",
      type: "warning",
      dangerouslyUseHTMLString: true
    }
  ).then(() => {
    deleteDocumentApi(row.id)
      .then(() => {
        ElMessage.success("문서가 지식베이스에서 제거되었습니다")
        // 문서 목록 새로고침
        getDocumentList()
        // 지식베이스 목록 새로고침
        getTableData()
      })
      .catch((error) => {
        ElMessage.error(`문서 제거 실패: ${error?.message || "알 수 없는 오류"}`)
      })
  }).catch(() => {
    // 사용자가 작업을 취소함
  })
}

// 문서 추가 대화상자
const addDocumentDialogVisible = ref(false)
const selectedFiles = ref<string[]>([])
const fileTableRef = ref<any>()
const isSyncingSelection = ref(false)
const fileLoading = ref(false)
const fileList = ref<any[]>([])
const filePaginationData = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0,
  pageSizes: [10, 20, 50, 100],
  layout: "total, sizes, prev, pager, next, jumper"
})

// 문서 추가 처리
function handleAddDocument() {
  addDocumentDialogVisible.value = true
  // 선택 초기화
  selectedFiles.value = []
  // 파일 목록 가져오기
  getFileList()
}

// 파일 목록 가져오기
function getFileList() {
  fileLoading.value = true
  // 파일 목록 가져오기 API 호출
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
    nextTick(() => {
      if (fileTableRef.value) {
        isSyncingSelection.value = true
        fileTableRef.value.clearSelection()
        fileList.value.forEach((row: any) => {
          if (selectedFiles.value.includes(String(row.id))) {
            fileTableRef.value.toggleRowSelection(row, true)
          }
        })
        setTimeout(() => { isSyncingSelection.value = false }, 0)
      }
    })
  }).catch((error) => {
    ElMessage.error(`파일 목록 가져오기 실패: ${error?.message || "알 수 없는 오류"}`)
    fileList.value = []
  }).finally(() => {
    fileLoading.value = false
  })
}

/**
 * @description 파일 테이블 정렬 변경 이벤트 처리
 * @param {object} sortInfo 정렬 정보 객체, prop과 order 포함
 * @param {string} sortInfo.prop 정렬할 필드명
 * @param {string | null} sortInfo.order 정렬 순서 ('ascending', 'descending', null)
 */
function handleFileSortChange({ prop }: { prop: string, order: string | null }) {
  // 같은 필드를 클릭한 경우 정렬 순서 전환
  if (fileSortData.sortBy === prop) {
    // 현재 오름차순이면 내림차순으로, 그렇지 않으면 오름차순으로 전환
    fileSortData.sortOrder = fileSortData.sortOrder === "asc" ? "desc" : "asc"
  } else {
    // 필드 전환 시 기본값은 오름차순
    fileSortData.sortBy = prop
    fileSortData.sortOrder = "asc"
  }
  getFileList()
}

// 파일 선택 변경 처리
function handleFileSelectionChange(selection: any[]) {
  if (isSyncingSelection.value) return
  const currentPageIds = new Set(fileList.value.map((item: any) => String(item.id)))
  const set = new Set(selectedFiles.value.map(id => String(id)))
  // 현재 페이지에서 선택되지 않은 항목 제거
  currentPageIds.forEach(id => set.delete(id))
  // 현재 페이지에서 선택된 항목 병합
  selection.forEach((item: any) => set.add(String(item.id)))
  selectedFiles.value = Array.from(set)
}

// 요청 잠금 변수 추가
const isAddingDocument = ref(false)
const messageShown = ref(false) // 이 줄을 추가하여 messageShown을 컴포넌트 수준 변수로 승격

// confirmAddDocument 함수 수정
async function confirmAddDocument() {
  // 이미 요청을 처리 중인지 확인
  if (isAddingDocument.value) {
    console.log("문서 추가 요청을 처리 중입니다. 중복 클릭하지 마세요")
    return
  }

  if (selectedFiles.value.length === 0) {
    ElMessage.warning("최소 하나의 파일을 선택해주세요")
    return
  }

  if (!currentKnowledgeBase.value) return

  try {
    // 요청 잠금 설정
    isAddingDocument.value = true
    messageShown.value = false // 컴포넌트 수준 변수를 사용하여 메시지 표시 플래그 초기화
    console.log("문서 추가 요청 시작...", selectedFiles.value)

    // 파일 ID를 직접 처리, 더 이상 확인 대화상자를 표시하지 않음
    const fileIds = selectedFiles.value.map(id => /^\d+$/.test(String(id)) ? Number(id) : id)

    // API 요청 전송 - 불필요한 내부 try/catch 제거
    const response = await axios.post(
      `/api/v1/knowledgebases/${currentKnowledgeBase.value.id}/documents`,
      { file_ids: fileIds }
    )

    console.log("API 원본 응답:", response)

    // 응답 상태 확인
    if (response.data && (response.data.code === 0 || response.data.code === 201)) {
      // 성공 처리
      if (!messageShown.value) {
        messageShown.value = true
        console.log("성공 메시지 표시")
        ElMessage.success("문서가 성공적으로 추가되었습니다")
      }

      addDocumentDialogVisible.value = false
      getDocumentList()
      getTableData()
    } else {
      // 오류 응답 처리
      throw new Error(response.data?.message || "문서 추가 실패")
    }
  } catch (error: any) {
    // API 호출 실패
    console.error("API 요청 실패 상세정보:", {
      error: error?.toString(),
      stack: error?.stack,
      response: error?.response?.data,
      request: error?.request,
      config: error?.config
    })

    // 더 자세한 오류 로그 추가
    console.log("오류 상세정보:", error)
    if (error.response) {
      console.log("응답 데이터:", error.response.data)
      console.log("응답 상태:", error.response.status)
    }

    ElMessage.error(`문서 추가 실패: ${error?.message || "알 수 없는 오류"}`)
  } finally {
    // 성공/실패와 관계없이 요청 잠금 해제
    console.log("문서 추가 요청 완료, 잠금 해제", new Date().toISOString())
    setTimeout(() => {
      isAddingDocument.value = false
    }, 500) // 빠른 클릭 방지를 위한 지연 시간 추가
  }
}

// 파일 크기 포맷팅
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

// 파일 타입 포맷팅
function formatFileType(type: string) {
  const typeMap: Record<string, string> = {
    pdf: "PDF",
    doc: "Word",
    docx: "Word",
    xls: "Excel",
    xlsx: "Excel",
    ppt: "PPT",
    pptx: "PPT",
    txt: "텍스트",
    md: "Markdown",
    jpg: "이미지",
    jpeg: "이미지",
    png: "이미지"
  }

  return typeMap[type.toLowerCase()] || type
}

// 지식베이스 삭제
function handleDelete(row: KnowledgeBaseData) {
  ElMessageBox.confirm(
    `지식베이스 "${row.name}"을(를) 삭제하시겠습니까? 삭제 후에는 복구할 수 없으며, 그 안의 모든 문서도 함께 삭제됩니다.`,
    "삭제 확인",
    {
      confirmButtonText: "확인",
      cancelButtonText: "취소",
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
          instance.confirmButtonText = "삭제 중..."

          loading.value = true
          deleteKnowledgeBaseApi(row.id)
            .then(() => {
              ElMessage.success("삭제가 완료되었습니다")
              getTableData() // 테이블 데이터 새로고침
              done()
            })
            .catch((error) => {
              ElMessage.error(`삭제 실패: ${error?.message || "알 수 없는 오류"}`)
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
    // 사용자가 삭제 작업을 취소함
  })
}

// 지식베이스 일괄 삭제
function handleBatchDelete() {
  if (multipleSelection.value.length === 0) {
    ElMessage.warning("최소 하나의 지식베이스를 선택해주세요")
    return
  }

  ElMessageBox.confirm(
    `선택한 <strong>${multipleSelection.value.length}</strong>개의 지식베이스를 삭제하시겠습니까?<br><span style="color: #F56C6C; font-size: 12px;">이 작업은 되돌릴 수 없으며, 그 안의 모든 문서도 함께 삭제됩니다</span>`,
    "일괄 삭제 확인",
    {
      confirmButtonText: "확인",
      cancelButtonText: "취소",
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
          instance.confirmButtonText = "삭제 중..."

          loading.value = true
          const ids = multipleSelection.value.map(item => item.id)
          batchDeleteKnowledgeBaseApi(ids)
            .then(() => {
              ElMessage.success(`${multipleSelection.value.length}개의 지식베이스가 성공적으로 삭제되었습니다`)
              getTableData() // 테이블 데이터 새로고침
              done()
            })
            .catch((error) => {
              ElMessage.error(`일괄 삭제 실패: ${error?.message || "알 수 없는 오류"}`)
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
    // 사용자가 삭제 작업을 취소함
  })
}

// 테이블 다중 선택 이벤트 처리
function handleSelectionChange(selection: KnowledgeBaseData[]) {
  multipleSelection.value = selection
}

/**
 * @description 테이블 정렬 변경 이벤트 처리 (오름차순과 내림차순 전환만 허용)
 * @param {object} sortInfo 정렬 정보 객체, prop과 order 포함
 * @param {string} sortInfo.prop 정렬할 필드명
 * @param {string | null} sortInfo.order 정렬 순서 ('ascending', 'descending', null)
 */
function handleSortChange({ prop }: { prop: string, order: string | null }) {
  // 같은 필드를 클릭한 경우 정렬 순서 전환
  if (sortData.sortBy === prop) {
    // 현재 오름차순이면 내림차순으로, 그렇지 않으면 오름차순으로 전환
    sortData.sortOrder = sortData.sortOrder === "asc" ? "desc" : "asc"
  } else {
    // 필드 전환 시 기본값은 오름차순
    sortData.sortBy = prop
    sortData.sortOrder = "asc"
  }
  getTableData()
}

// 페이지네이션 매개변수 변화 감시
watch([() => paginationData.currentPage, () => paginationData.pageSize], getTableData, { immediate: true })

// 페이지 마운트 및 활성화 시 데이터 가져오기 보장
onMounted(() => {
  getTableData()
})

// 다른 페이지에서 돌아올 때 데이터 새로고침
onActivated(() => {
  getTableData()
})

// 시스템 Embedding 설정 로직
const configModalVisible = ref(false)
const configFormRef = ref<FormInstance>() // 폼 참조
const configFormLoading = ref(false) // 폼 로딩 상태
const configSubmitLoading = ref(false) // 제출 버튼 로딩 상태

const configForm = reactive({
  kb_id: "",
  llm_name: "",
  api_base: "",
  api_key: ""
})

// 간단한 URL 검증 규칙
function validateUrl(rule: any, value: any, callback: any) {
  if (!value) {
    return callback(new Error("모델 API 주소를 입력해주세요"))
  }
  // http, https로 시작하는 것, IP 주소와 도메인명, 포트 허용
  // 수정: 경로는 허용하지만 쿼리 매개변수나 프래그먼트는 허용하지 않음
  const urlPattern = /^(https?:\/\/)?([a-zA-Z0-9.-]+|\[[a-fA-F0-9:]+\])(:\d+)?(\/[^?#]*)?$/
  if (!urlPattern.test(value)) {
    callback(new Error("유효한 Base URL을 입력해주세요 (예: http://host:port 또는 https://domain/path)"))
  } else {
    callback()
  }
}

const configFormRules = reactive({
  llm_name: [{ required: true, message: "모델명을 입력해주세요", trigger: "blur" }],
  api_base: [{ required: true, validator: validateUrl, trigger: "blur" }]
  // api_key는 필수 항목이 아님
})

// 설정 모달 표시
async function showConfigModal() {
  configModalVisible.value = true
  configFormLoading.value = true
  // 폼 리셋은 DOM 업데이트가 완료된 후 nextTick에서 실행해야 할 수 있음
  await nextTick()
  configFormRef.value?.resetFields() // 이전 입력과 검증 상태 초기화

  try {
    // 캐시 방지를 위한 타임스탬프 추가
    const res = await getSystemEmbeddingConfigApi({ t: Date.now() }) as ApiResponse<{ llm_name?: string, api_base?: string, api_key?: string }>
    console.log("시스템 임베딩 설정 전체 응답 가져오기:", res)
    console.log("응답 데이터 상세정보:", res.data)
    
    if (res.code === 0 && res.data) {
      configForm.llm_name = res.data.llm_name || ""
      configForm.api_base = res.data.api_base || ""
      // 주의: API Key는 일반적으로 GET 요청에서 반환되지 않음, 백엔드에서 반환하지 않으면 빈 문자열이 됨
      configForm.api_key = res.data.api_key || ""
      console.log("폼이 채워짐:", { 
        llm_name: configForm.llm_name, 
        api_base: configForm.api_base, 
        api_key: configForm.api_key ? "***" : "" 
      })
    } else if (res.code !== 0) {
      ElMessage.error(res.message || "설정 가져오기 실패")
    } else {
      // code === 0이지만 data가 비어있음, 설정이 없음을 의미
      console.log("현재 임베딩 모델이 설정되지 않았습니다.")
    }
  } catch (error: any) {
    ElMessage.error(error.message || "설정 요청 가져오기 실패")
    console.error("설정 가져오기 실패:", error)
  } finally {
    configFormLoading.value = false
  }
}


// 모달 닫기 처리
function handleModalClose() {
  // 사용자가 저장하지 않고 직접 닫는 경우를 대비하여 여기서 폼을 다시 초기화할 수 있음
  configFormRef.value?.resetFields()
}

// 설정 제출 처리
async function handleConfigSubmit() {
  if (!configFormRef.value) return
  // .then() .catch()를 사용하여 validate의 Promise 처리
  configFormRef.value.validate().then(async () => {
    // 검증 통과
    configSubmitLoading.value = true
    try {
      const payload = {
        llm_name: configForm.llm_name.trim(),
        api_base: configForm.api_base.trim(),
        api_key: configForm.api_key
      }
      console.log("설정 데이터 제출:", payload)
      
      // API 함수명이 올바른지 확인하고 타입 단언 추가
      const res = await setSystemEmbeddingConfigApi(payload) as ApiResponse<any>
      console.log("설정 저장 응답:", res)
      
      if (res.code === 0) {
        ElMessage.success("설정이 성공적으로 저장되었습니다! 연결 테스트를 통과했습니다")
        
        // 저장 성공 후 잠시 대기한 다음 설정을 다시 가져와서 폼 표시 새로고침
        await new Promise(resolve => setTimeout(resolve, 500))
        
        try {
          const refreshRes = await getSystemEmbeddingConfigApi({ t: Date.now() }) as ApiResponse<{ llm_name?: string, api_base?: string, api_key?: string }>
          console.log("새로고침 설정 가져오기 응답:", refreshRes)
          
          if (refreshRes.code === 0 && refreshRes.data) {
            const oldValues = {
              llm_name: configForm.llm_name,
              api_base: configForm.api_base,
              api_key: configForm.api_key
            }
            
            configForm.llm_name = refreshRes.data.llm_name || ""
            configForm.api_base = refreshRes.data.api_base || ""
            configForm.api_key = refreshRes.data.api_key || ""
            
            console.log("설정값 비교:", {
              old: oldValues,
              new: {
                llm_name: configForm.llm_name,
                api_base: configForm.api_base,
                api_key: configForm.api_key ? "***" : ""
              }
            })
            
            // 실제로 업데이트되었는지 확인
            if (configForm.llm_name !== oldValues.llm_name || 
                configForm.api_base !== oldValues.api_base) {
              ElMessage.success("설정이 업데이트되어 최신 내용이 표시됩니다")
            } else {
              console.warn("설정값이 변경되지 않았습니다. 캐시나 동기화 문제가 있을 수 있습니다")
            }
          } else {
            console.warn("설정 새로고침 시 빈 데이터 반환:", refreshRes)
          }
        } catch (refreshError) {
          console.warn("설정 새로고침 실패했지만 저장은 성공:", refreshError)
        }
        
        // 저장 성공 후 팝업 닫기
        configModalVisible.value = false
      } else {
        // 백엔드는 res.message에서 연결 테스트 실패 이유를 포함한 오류 정보를 반환해야 함
        ElMessage.error(res.message || "설정 저장 실패")
      }
    } catch (error: any) {
      ElMessage.error(error.message || "설정 저장 요청 실패")
      console.error("설정 저장 실패:", error)
    } finally {
      configSubmitLoading.value = false
    }
  }).catch((errorFields) => {
    // 검증 실패
    console.log("폼 검증 실패!", errorFields)
    // 여기서 false를 반환할 필요 없음, validate의 Promise reject가 실패를 나타냄
  })
}

// 상태에 따라 Alert 타입 결정
function getAlertType(status: any) {
  switch (status) {
    case "failed":
    case "not_found": // 'not_found'도 하나의 오류로 간주될 수 있음
      return "error"
    case "completed":
      return "success"
    case "cancelled":
      return "warning" // 취소는 경고나 정보로 간주할 수 있음, 요구사항에 따라
    case "running":
    case "starting":
    case "cancelling":
    default:
      return "info"
  }
}

// 로딩 중 상태인지 판단
function isLoadingStatus(status: string) {
  return ["running", "starting", "cancelling"].includes(status)
}

// 진행률 카운트를 표시할지 판단 (예: 시작 중이거나 작업을 찾을 수 없을 때는 0/0 표시가 적합하지 않을 수 있음)
function shouldShowProgressCount(status: string) {
  return !["starting", "not_found"].includes(status)
}

// 사용자 목록 관련 상태
const userList = ref<{ id: number, username: string }[]>([])
const userLoading = ref(false)

// 지식베이스 모델 목록
const embeddingModels= ref<{ tenant_id: string, llm_name: string, llm_factory:string }[]>([])

// 지식베이스 모델 로딩
function loadingEmbeddingModels(){
  loadingEmbeddingModelsApi({
    kb_id:editForm.id
  }).then((response) =>{
    const result = response as ApiResponse<{ tenant_id: string, llm_name: string, llm_factory:string }[]>
    embeddingModels.value= result.data
  }).catch((error) => {
    ElMessage.error(`임베딩 모델 로딩 실패: ${error?.message || "알 수 없는 오류"}`)
    embeddingModels.value = []
  })
}
</script>

<template>
  <div>
    <div class="app-container">
      <el-card v-loading="loading" shadow="never" class="search-wrapper">
        <el-form ref="searchFormRef" :inline="true" :model="searchData">
          <el-form-item prop="name" label="지식베이스명">
            <el-input v-model="searchData.name" placeholder="입력해주세요" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :icon="Search" @click="handleSearch">
              검색
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
            <el-button
              type="primary"
              :icon="Plus"
              @click="handleCreate"
            >
              새 지식베이스 생성
            </el-button>
            <el-button
              type="danger"
              :icon="Delete"
              :disabled="multipleSelection.length === 0"
              @click="handleBatchDelete"
            >
              일괄 삭제
            </el-button>
          </div>

          <div>
            <el-button type="primary" :icon="Setting" @click="showConfigModal">
              임베딩 모델 설정
            </el-button>
          </div>
        </div>

        <div class="table-wrapper">
          <el-table :data="tableData" @selection-change="handleSelectionChange" @sort-change="handleSortChange">
            <el-table-column type="selection" width="50" align="center" />
            <el-table-column label="번호" align="center" width="60">
              <template #default="scope">
                {{ (paginationData.currentPage - 1) * paginationData.pageSize + scope.$index + 1 }}
              </template>
            </el-table-column>
            <el-table-column prop="name" label="지식베이스명" align="center" min-width="120" sortable="custom" />
            <el-table-column prop="nickname" label="생성자" align="center" min-width="120" sortable="custom" />
            <el-table-column prop="embd_id" label="임베딩 모델" align="center" min-width="120" sortable="custom" />
            <el-table-column prop="description" label="설명" align="center" min-width="180" show-overflow-tooltip />
            <el-table-column prop="doc_num" label="문서 수" align="center" width="80" />
            <el-table-column label="언어" align="center" width="80">
              <template #default="scope">
                <el-tag type="info" size="small">
                  {{ scope.row.language === 'Chinese' ? '중국어' : '영어' }}
                </el-tag>
              </template>
            </el-table-column>
            <!-- 권한 열 추가 -->
            <el-table-column label="권한" align="center" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.permission === 'me' ? 'success' : 'warning'" size="small">
                  {{ scope.row.permission === 'me' ? '개인' : '팀' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="생성시간" align="center" width="180" sortable="custom">
              <template #default="scope">
                {{ scope.row.create_date }}
              </template>
            </el-table-column>
            <el-table-column fixed="right" label="작업" width="300" align="center">
              <template #default="scope">
                <el-button
                  type="primary"
                  text
                  bg
                  size="small"
                  :icon="View"
                  @click="handleView(scope.row)"
                >
                  보기
                </el-button>
                <el-button
                  type="warning"
                  text
                  bg
                  size="small"
                  :icon="Edit"
                  @click="handleEdit(scope.row)"
                >
                  수정
                </el-button>
                <el-button
                  type="danger"
                  text
                  bg
                  size="small"
                  :icon="Delete"
                  @click="handleDelete(scope.row)"
                >
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

      <!-- 지식베이스 상세 대화상자 -->
      <el-dialog
        v-model="viewDialogVisible"
        :title="`지식베이스 상세정보 - ${currentKnowledgeBase?.name || ''}`"
        width="80%"
        append-to-body
        :close-on-click-modal="!batchParsingLoading"
        :close-on-press-escape="!batchParsingLoading"
        :show-close="!batchParsingLoading"
      >
        <div v-if="currentKnowledgeBase">
          <div class="kb-info-header">
            <div>
              <span class="kb-info-label">지식베이스 ID:</span> {{ currentKnowledgeBase.id }}
            </div>
            <div>
              <span class="kb-info-label">총 문서 수:</span> {{ currentKnowledgeBase.doc_num }}
            </div>
            <div>
              <span class="kb-info-label">언어:</span>
              <el-tag type="info" size="small">
                {{ currentKnowledgeBase.language === 'Chinese' ? '중국어' : '영어' }}
              </el-tag>
            </div>
            <div>
              <span class="kb-info-label">권한:</span>
              <el-tag :type="currentKnowledgeBase.permission === 'me' ? 'success' : 'warning'" size="small">
                {{ currentKnowledgeBase.permission === 'me' ? '개인' : '팀' }}
              </el-tag>
            </div>
          </div>

          <div class="document-table-header">
            <div class="left-buttons">
              <el-button type="primary" @click="handleAddDocument">
                문서 추가
              </el-button>
              <!-- 일괄 파싱 버튼 -->
              <el-button
                type="warning"
                :icon="CaretRight"
                :loading="batchParsingLoading && !isBatchPolling"
                @click="handleBatchParse"
                :disabled="isBatchParseDisabled || batchParsingLoading"
              >
                <!-- 폴링 중인지에 따라 다른 텍스트 표시 -->
                {{ isBatchPolling ? '일괄 파싱 중...' : (batchParsingLoading ? '시작 중...' : '일괄 파싱') }}
              </el-button>
            </div>
          </div>
          <!-- 진행률 표시 -->
          <div v-if="batchProgress" class="batch-progress">
            <el-alert
              :title="batchProgress.message || '처리 중...'"
              :type="getAlertType(batchProgress.status)"
              :closable="false"
              show-icon
              class="batch-progress-alert"
            >
              <!-- 로딩 아이콘: 진행 중 관련 상태('running', 'starting', 'cancelling')에서만 표시 -->
              <template #icon v-if="isLoadingStatus(batchProgress.status)">
                <el-icon class="is-loading">
                  <Loading />
                </el-icon>
              </template>

              <!-- 기본 슬롯: 추가 진행률 세부정보 표시용 -->
              <div class="batch-progress-details">
                <!-- 처리 진행률 표시 (현재 항목 / 총 항목 수) -->
                <!-- 총 수가 0보다 크고 상태가 'starting' 또는 'not_found'가 아닐 때만 표시하는 것이 의미있음 -->
                <template v-if="batchProgress.total > 0 && shouldShowProgressCount(batchProgress.status)">
                  <p>
                    처리 진행률: {{ batchProgress.current ?? 0 }} / {{ batchProgress.total }}
                  </p>
                </template>

                <!-- 플레이스홀더: 진행률 카운트를 표시하지 않으면 높이 축소를 방지하기 위한 플레이스홀더 표시 -->
                <template v-else>
                  <p>&nbsp;</p> <!-- 줄바꿈 없는 공백을 사용하여 최소 높이 보장 -->
                </template>
              </div>
            </el-alert>
          </div>
          <!-- === 진행률 표시 종료 === -->

          <div class="document-table-wrapper" v-loading="documentLoading || (isBatchPolling && !batchProgress)">
            <el-table :data="documentList" style="width: 100%" @sort-change="handleDocSortChange">
              <el-table-column prop="name" label="이름" min-width="180" show-overflow-tooltip sortable="custom" />
              <el-table-column prop="chunk_num" label="청크 수" width="100" align="center" />
              <el-table-column prop="create_date" label="업로드 날짜" width="180" align="center" sortable="custom">
                <template #default="scope">
                  {{ scope.row.create_date }}
                </template>
              </el-table-column>
              <el-table-column label="파싱 상태" width="120" align="center">
                <template #default="scope">
                  <el-tag :type="getParseStatusType(scope.row.progress)">
                    {{ formatParseStatus(scope.row.progress) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="작업" width="200" align="center">
                <template #default="scope">
                  <el-button
                    type="success"
                    size="small"
                    :icon="CaretRight"
                    @click="handleParseDocument(scope.row)"
                  >
                    파싱
                  </el-button>
                  <el-button
                    type="danger"
                    size="small"
                    :icon="Delete"
                    @click="handleRemoveDocument(scope.row)"
                  >
                    제거
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- 페이지네이션 컨트롤 -->
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

      <!-- 새 지식베이스 대화상자 -->
      <el-dialog
        v-model="createDialogVisible"
        title="새 지식베이스 생성"
        width="40%"
      >
        <el-form
          ref="knowledgeBaseFormRef"
          :model="knowledgeBaseForm"
          :rules="knowledgeBaseFormRules"
          label-width="100px"
        >
          <el-form-item label="지식베이스명" prop="name">
            <el-input v-model="knowledgeBaseForm.name" placeholder="지식베이스명을 입력해주세요" />
          </el-form-item>
          <el-form-item label="설명" prop="description">
            <el-input
              v-model="knowledgeBaseForm.description"
              type="textarea"
              :rows="3"
              placeholder="지식베이스 설명을 입력해주세요"
            />
          </el-form-item>
          <el-form-item label="언어" prop="language">
            <el-select v-model="knowledgeBaseForm.language" placeholder="언어를 선택해주세요">
              <el-option label="중국어" value="Chinese" />
              <el-option label="영어" value="English" />
            </el-select>
          </el-form-item>
          <el-form-item label="생성자" prop="creator_id">
            <el-select
              v-model="knowledgeBaseForm.creator_id"
              placeholder="생성자를 선택해주세요"
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
          <el-form-item label="권한" prop="permission">
            <el-select v-model="knowledgeBaseForm.permission" placeholder="권한을 선택해주세요">
              <el-option label="개인" value="me" />
              <el-option label="팀" value="team" />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="createDialogVisible = false">
            취소
          </el-button>
          <el-button
            type="primary"
            :loading="uploadLoading"
            @click="submitCreate"
          >
            생성 확인
          </el-button>
        </template>
      </el-dialog>

      <!-- 지식베이스 수정 대화상자 -->
      <el-dialog
        v-model="editDialogVisible"
        title="지식베이스 권한 수정"
        width="40%"
      >
        <el-form
          label-width="120px"
        >
          <el-form-item label="지식베이스명">
            <span>{{ editForm.name }}</span>
          </el-form-item>
          <el-form-item label="지식베이스 아바타">
            <el-upload
              class="avatar-uploader"
              action="#"
              :show-file-list="false"
              :on-change="handleAvatarChange"
              :auto-upload="false"
              accept="image/png, image/jpeg, image/gif, image/webp"
            >
              <img v-if="editForm.avatar" :src="editForm.avatar" class="avatar" alt="avatar">
              <el-icon v-else class="avatar-uploader-icon">
                <Plus />
              </el-icon>
            </el-upload>
          </el-form-item>
          <el-form-item label="권한 설정">
            <el-select v-model="editForm.permission" placeholder="권한을 선택해주세요">
              <el-option label="개인" value="me" />
              <el-option label="팀" value="team" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <div style="color: #909399; font-size: 12px; line-height: 1.5;">
              개인 권한: 본인만 조회 및 사용 가능<br>
              팀 권한: 팀 구성원이 조회 및 사용 가능
            </div>
          </el-form-item>
          <el-form-item label="지식베이스 임베딩 모델" @click="loadingEmbeddingModels()">
            <el-select v-model="editForm.embd_id" placeholder="임베딩 모델을 선택해주세요">
              <el-option
                v-for="model in embeddingModels"
                :label="model.llm_name+'@'+model.llm_factory"
                :value="model.llm_name"
              />
            </el-select>
            <el-form-item>
              <div style="color: #909399; font-size: 12px; line-height: 1.5;">
                <br>파일을 파싱한 후에는 Embedding 모델을 다시 수정하지 마세요
                <br>서로 다른 Embedding 모델의 차이로 인해 bge-m3 모델 사용을 권장합니다
              </div>
            </el-form-item>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="editDialogVisible = false">
            취소
          </el-button>
          <el-button
            type="primary"
            :loading="editLoading"
            @click="submitEdit"
          >
            수정 확인
          </el-button>
        </template>
      </el-dialog>

      <!-- 문서 대화상자 -->
      <el-dialog
        v-model="addDocumentDialogVisible"
        title="지식베이스에 문서 추가"
        width="70%"
      >
        <div v-loading="fileLoading">
          <el-table
            ref="fileTableRef"
            :data="fileList"
            :row-key="row => String(row.id)"
            style="width: 100%"
            @selection-change="handleFileSelectionChange"
            @sort-change="handleFileSortChange"
          >
            <el-table-column type="selection" width="55" reserve-selection />
            <el-table-column prop="name" label="파일명" min-width="180" show-overflow-tooltip sortable="custom" />
            <el-table-column prop="size" label="크기" width="100" align="center" sortable="custom">
              <template #default="scope">
                {{ formatFileSize(scope.row.size) }}
              </template>
            </el-table-column>
            <el-table-column prop="type" label="타입" width="100" align="center">
              <template #default="scope">
                {{ formatFileType(scope.row.type) }}
              </template>
            </el-table-column>
            <el-table-column prop="create_date" label="생성시간" align="center" width="180" sortable="custom">
              <template #default="scope">
                {{ scope.row.create_date }}
              </template>
            </el-table-column>
          </el-table>

          <!-- 페이지네이션 컨트롤 -->
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
            <el-button @click="addDocumentDialogVisible = false">취소</el-button>
            <el-button
              type="primary"
              :disabled="isAddingDocument"
              @click.stop.prevent="confirmAddDocument"
            >
              {{ isAddingDocument ? '처리 중...' : '확인' }}
            </el-button>
          </span>
        </template>
      </el-dialog>

      <!-- 시스템 Embedding 설정 모달 -->
      <el-dialog
        v-model="configModalVisible"
        title="임베딩 모델 설정"
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
          <el-form-item label="모델명" prop="llm_name">
            <el-input v-model="configForm.llm_name" placeholder="먼저 프론트엔드에서 설정해주세요" />
            <div class="form-tip">
              모델 서비스에 배포된 이름과 일치해야 합니다
            </div>
          </el-form-item>
          <el-form-item label="모델 API 주소" prop="api_base">
            <el-input v-model="configForm.api_base" placeholder="먼저 프론트엔드에서 설정해주세요" />
            <div class="form-tip">
              모델의 Base URL
            </div>
          </el-form-item>
          <el-form-item label="API Key (선택사항)" prop="api_key">
            <el-input v-model="configForm.api_key" type="password" show-password placeholder="먼저 프론트엔드에서 설정해주세요" />
            <div class="form-tip">
              모델 서비스에 인증이 필요한 경우 제공해주세요
            </div>
          </el-form-item>
          <el-form-item>
            <div style="color: #909399; font-size: 12px; line-height: 1.5;">
              이 설정은 지식베이스 파싱 시 기본 Embedding 모델로 사용됩니다.
              지식베이스 수정에서 새로운 Embedding 모델로 전환할 수 있음을 참고해주세요.
            </div>
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="configModalVisible = false">취소</el-button>
            <el-button type="primary" @click="handleConfigSubmit" :loading="configSubmitLoading">
              저장 및 연결 테스트
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
  justify-content: space-between; // 좌우 양쪽 정렬 보장
  align-items: center; // 수직 중앙 정렬
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
  margin-bottom: 20px; // 하단 테이블과의 간격
  margin-top: 5px; // 상단 버튼 행과의 간격
  padding: 0 10px; // 좌우 여백 설정
}

.batch-progress-alert {
  // Alert에 일부 효과 추가 가능, 예: 가벼운 테두리나 배경
  // background-color: #f8f8f9; // 매우 연한 배경색
  border: 1px solid #e9e9eb;
  border-radius: 4px;

  // 내부 icon과 title/description의 정렬 방식 조정
  :deep(.el-alert__content) {
    display: flex;
    align-items: center; // Title과 Icon의 수직 중앙 정렬 (기본 아이콘 표시 시)
  }
  :deep(.el-alert__title) {
    margin-right: 15px; // 제목과 우측 상세 정보 간 거리 추가
  }

  // 커스텀 로딩 아이콘 스타일
  .el-icon.is-loading {
    margin-right: 8px; // 아이콘과 제목 간의 거리
    font-size: 16px; // 아이콘 크기
  }
}

.batch-progress-details {
  font-size: 12px;
  line-height: 1.5;
  color: #606266; // 일반 상세 텍스트 색상

  p {
    margin: 0; // 단락 기본 여백 제거
    min-height: 18px; // 내용이나 플레이스홀더가 있을 때 최소 높이 보장
  }

  .error-detail {
    color: #f56c6c; // 오류 상세 정보는 눈에 띄는 빨간색
    font-weight: 500; // 약간 굵게 표시 가능
  }
}

// 회전 애니메이션 보장
@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// 로딩 아이콘 애니메이션 상속
.el-tag .el-icon.is-loading,
.batch-progress-alert .el-icon.is-loading {
  margin-right: 4px;
  vertical-align: middle;
  animation: rotating 2s linear infinite;
}

.avatar-uploader .el-upload {
  border: 1px dashed var(--el-border-color);
  border-radius: 50%; /* 원형 */
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}

.avatar-uploader .el-upload:hover {
  border-color: var(--el-color-primary);
}

.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 120px;
  height: 120px;
  text-align: center;
  line-height: 120px; /* 아이콘 수직 중앙 정렬 */
}

.avatar {
  width: 120px;
  height: 120px;
  display: block;
  object-fit: cover; /* 이미지 변형 방지 */
}
</style>
