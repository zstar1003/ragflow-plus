<script lang="ts" setup>
import screenfull from "screenfull"

interface Props {
  /** 전체화면할 요소, 기본값은 html */
  element?: string
  /** 전체화면 열기 안내 메시지 */
  openTips?: string
  /** 전체화면 닫기 안내 메시지 */
  exitTips?: string
  /** 콘텐츠 영역만 대상으로 할지 여부 */
  content?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  element: "html",
  openTips: "전체화면",
  exitTips: "전체화면 종료",
  content: false
})

const CONTENT_LARGE = "content-large"

const CONTENT_FULL = "content-full"

const classList = document.body.classList

// #region 전체화면
const isEnabled = screenfull.isEnabled
const isFullscreen = ref<boolean>(false)
const fullscreenTips = computed(() => (isFullscreen.value ? props.exitTips : props.openTips))
const fullscreenSvgName = computed(() => (isFullscreen.value ? "fullscreen-exit" : "fullscreen"))

function handleFullscreenClick() {
  const dom = document.querySelector(props.element) || undefined
  isEnabled ? screenfull.toggle(dom) : ElMessage.warning("브라우저가 작동하지 않습니다")
}

function handleFullscreenChange() {
  isFullscreen.value = screenfull.isFullscreen
  // 전체화면 종료 시 관련 class 제거
  isFullscreen.value || classList.remove(CONTENT_LARGE, CONTENT_FULL)
}

watchEffect((onCleanup) => {
  if (isEnabled) {
    // 컴포넌트 마운트 시 자동 실행
    screenfull.on("change", handleFullscreenChange)
    // 컴포넌트 언마운트 시 자동 실행
    onCleanup(() => {
      screenfull.off("change", handleFullscreenChange)
    })
  }
})
// #endregion

// #region 콘텐츠 영역
const isContentLarge = ref<boolean>(false)
const contentLargeTips = computed(() => (isContentLarge.value ? "콘텐츠 영역 복원" : "콘텐츠 영역 확대"))
const contentLargeSvgName = computed(() => (isContentLarge.value ? "fullscreen-exit" : "fullscreen"))

function handleContentLargeClick() {
  isContentLarge.value = !isContentLarge.value
  // 콘텐츠 영역 확대 시 불필요한 컴포넌트 숨김
  classList.toggle(CONTENT_LARGE, isContentLarge.value)
}

function handleContentFullClick() {
  // 콘텐츠 영역 확대 취소
  isContentLarge.value && handleContentLargeClick()
  // 콘텐츠 영역 전체화면 시 불필요한 컴포넌트 숨김
  classList.add(CONTENT_FULL)
  // 전체화면 시작
  handleFullscreenClick()
}
// #endregion
</script>

<template>
  <div>
    <!-- 전체화면 -->
    <el-tooltip v-if="!props.content" effect="dark" :content="fullscreenTips" placement="bottom">
      <SvgIcon :name="fullscreenSvgName" @click="handleFullscreenClick" class="svg-icon" />
    </el-tooltip>
    <!-- 콘텐츠 영역 -->
    <el-dropdown v-else :disabled="isFullscreen">
      <SvgIcon :name="contentLargeSvgName" class="svg-icon" />
      <template #dropdown>
        <el-dropdown-menu>
          <!-- 콘텐츠 영역 확대 -->
          <el-dropdown-item @click="handleContentLargeClick">
            {{ contentLargeTips }}
          </el-dropdown-item>
          <!-- 콘텐츠 영역 전체화면 -->
          <el-dropdown-item @click="handleContentFullClick">
            콘텐츠 영역 전체화면
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<style lang="scss" scoped>
.svg-icon {
  font-size: 20px;
  &:focus {
    outline: none;
  }
}
</style>
