<script lang="ts" setup>
import type { ElScrollbar } from "element-plus"
import type { RouteRecordNameGeneric, RouteRecordRaw } from "vue-router"
import { usePermissionStore } from "@/pinia/stores/permission"
import { useDevice } from "@@/composables/useDevice"
import { isExternal } from "@@/utils/validate"
import { cloneDeep, debounce } from "lodash-es"
import Footer from "./Footer.vue"
import Result from "./Result.vue"

/** modal 표시/숨김 제어 */
const modelValue = defineModel<boolean>({ required: true })

const router = useRouter()
const { isMobile } = useDevice()

const inputRef = ref<HTMLInputElement | null>(null)
const scrollbarRef = ref<InstanceType<typeof ElScrollbar> | null>(null)
const resultRef = ref<InstanceType<typeof Result> | null>(null)

const keyword = ref<string>("")
const result = shallowRef<RouteRecordRaw[]>([])
const activeRouteName = ref<RouteRecordNameGeneric | undefined>(undefined)
/** 위/아래 키를 눌렀는지 여부 (mouseenter 이벤트와의 충돌 해결용) */
const isPressUpOrDown = ref<boolean>(false)

/** 검색 대화상자 너비 제어 */
const modalWidth = computed(() => (isMobile.value ? "80vw" : "40vw"))
/** 트리형 메뉴 */
const menus = computed(() => cloneDeep(usePermissionStore().routes))

/** 검색 (디바운스) */
const handleSearch = debounce(() => {
  const flatMenus = flatTree(menus.value)
  const _keywords = keyword.value.toLocaleLowerCase().trim()
  result.value = flatMenus.filter(menu => keyword.value ? menu.meta?.title?.toLocaleLowerCase().includes(_keywords) : false)
  // 기본적으로 검색 결과의 첫 번째 항목 선택
  const length = result.value?.length
  activeRouteName.value = length > 0 ? result.value[0].name : undefined
}, 500)

/** 트리형 메뉴를 1차원 배열로 평면화, 메뉴 검색에 사용 */
function flatTree(arr: RouteRecordRaw[], result: RouteRecordRaw[] = []) {
  arr.forEach((item) => {
    result.push(item)
    item.children && flatTree(item.children, result)
  })
  return result
}

/** 검색 대화상자 닫기 */
function handleClose() {
  modelValue.value = false
  // 사용자가 데이터 재설정 작업을 보지 않도록 지연 처리
  setTimeout(() => {
    keyword.value = ""
    result.value = []
  }, 200)
}

/** 인덱스 위치에 따른 스크롤 */
function scrollTo(index: number) {
  if (!resultRef.value) return
  const scrollTop = resultRef.value.getScrollTop(index)
  // el-scrollbar 스크롤바를 수동으로 제어하여 상단에서의 거리 설정
  scrollbarRef.value?.setScrollTop(scrollTop)
}

/** 키보드 위쪽 키 */
function handleUp() {
  isPressUpOrDown.value = true
  const { length } = result.value
  if (length === 0) return
  // 해당 name이 메뉴에서 처음 나타나는 위치 가져오기
  const index = result.value.findIndex(item => item.name === activeRouteName.value)
  // 이미 상단에 있는 경우
  if (index === 0) {
    const bottomName = result.value[length - 1].name
    // 상단과 하단의 bottomName이 같고 길이가 1보다 큰 경우, 한 위치 더 점프 (처음과 끝의 같은 name으로 인한 위쪽 키 비활성화 문제 해결)
    if (activeRouteName.value === bottomName && length > 1) {
      activeRouteName.value = result.value[length - 2].name
      scrollTo(length - 2)
    } else {
      // 하단으로 점프
      activeRouteName.value = bottomName
      scrollTo(length - 1)
    }
  } else {
    activeRouteName.value = result.value[index - 1].name
    scrollTo(index - 1)
  }
}

/** 키보드 아래쪽 키 */
function handleDown() {
  isPressUpOrDown.value = true
  const { length } = result.value
  if (length === 0) return
  // 해당 name이 메뉴에서 마지막으로 나타나는 위치 가져오기 (연속된 두 개의 같은 name으로 인한 아래쪽 키 비활성화 문제 해결)
  const index = result.value.map(item => item.name).lastIndexOf(activeRouteName.value)
  // 이미 하단에 있는 경우
  if (index === length - 1) {
    const topName = result.value[0].name
    // 하단과 상단의 topName이 같고 길이가 1보다 큰 경우, 한 위치 더 점프 (처음과 끝의 같은 name으로 인한 아래쪽 키 비활성화 문제 해결)
    if (activeRouteName.value === topName && length > 1) {
      activeRouteName.value = result.value[1].name
      scrollTo(1)
    } else {
      // 상단으로 점프
      activeRouteName.value = topName
      scrollTo(0)
    }
  } else {
    activeRouteName.value = result.value[index + 1].name
    scrollTo(index + 1)
  }
}

/** 키보드 엔터키 */
function handleEnter() {
  const { length } = result.value
  if (length === 0) return
  const name = activeRouteName.value
  const path = result.value.find(item => item.name === name)?.path
  if (path && isExternal(path)) return window.open(path, "_blank", "noopener, noreferrer")
  if (!name) return ElMessage.warning("검색을 통해 해당 메뉴에 진입할 수 없습니다. 해당 라우트에 고유한 Name을 설정해주세요")
  try {
    router.push({ name })
  } catch {
    return ElMessage.warning("해당 메뉴에는 필수 동적 매개변수가 있어 검색을 통해 진입할 수 없습니다")
  }
  handleClose()
}

/** 위/아래 키 해제 */
function handleReleaseUpOrDown() {
  isPressUpOrDown.value = false
}
</script>

<template>
  <el-dialog
    v-model="modelValue"
    :before-close="handleClose"
    :width="modalWidth"
    top="5vh"
    class="search-modal__private"
    append-to-body
    @opened="inputRef?.focus()"
    @closed="inputRef?.blur()"
    @keydown.up="handleUp"
    @keydown.down="handleDown"
    @keydown.enter="handleEnter"
    @keyup.up.down="handleReleaseUpOrDown"
  >
    <el-input ref="inputRef" v-model="keyword" placeholder="메뉴 검색" size="large" clearable @input="handleSearch">
      <template #prefix>
        <SvgIcon name="search" class="svg-icon" />
      </template>
    </el-input>
    <el-empty v-if="result.length === 0" description="검색 결과 없음" :image-size="100" />
    <template v-else>
      <p>검색 결과</p>
      <el-scrollbar ref="scrollbarRef" max-height="40vh" always>
        <Result
          ref="resultRef"
          v-model="activeRouteName"
          :data="result"
          :is-press-up-or-down="isPressUpOrDown"
          @click="handleEnter"
        />
      </el-scrollbar>
    </template>
    <template #footer>
      <Footer :total="result.length" />
    </template>
  </el-dialog>
</template>

<style lang="scss">
.search-modal__private {
  .svg-icon {
    font-size: 18px;
  }
  .el-dialog__header {
    display: none;
  }
  .el-dialog__footer {
    border-top: 1px solid var(--el-border-color);
    padding-top: var(--el-dialog-padding-primary);
  }
}
</style>
