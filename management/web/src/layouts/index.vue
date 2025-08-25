<script lang="ts" setup>
import { useSettingsStore } from "@/pinia/stores/settings"
import { useDevice } from "@@/composables/useDevice"
import { useLayoutMode } from "@@/composables/useLayoutMode"
import { useWatermark } from "@@/composables/useWatermark"
import { getCssVar, setCssVar } from "@@/utils/css"
import { RightPanel, Settings } from "./components"
import { useResize } from "./composables/useResize"
import LeftMode from "./modes/LeftMode.vue"
import LeftTopMode from "./modes/LeftTopMode.vue"
import TopMode from "./modes/TopMode.vue"

// Layout 레이아웃 반응형
useResize()

const { setWatermark, clearWatermark } = useWatermark()
const { isMobile } = useDevice()
const { isLeft, isTop, isLeftTop } = useLayoutMode()
const settingsStore = useSettingsStore()
const { showSettings, showTagsView, showWatermark } = storeToRefs(settingsStore)

// #region 태그 바 숨김 시 높이 제거, Logo 컴포넌트 높이와 Header 영역 높이가 항상 일치하도록 함
const cssVarName = "--v3-tagsview-height"
const v3TagsviewHeight = getCssVar(cssVarName)
watchEffect(() => {
  showTagsView.value ? setCssVar(cssVarName, v3TagsviewHeight) : setCssVar(cssVarName, "0px")
})
// #endregion

// 시스템 워터마크 활성화 또는 비활성화
watchEffect(() => {
  showWatermark.value ? setWatermark(import.meta.env.VITE_APP_TITLE) : clearWatermark()
})
</script>

<template>
  <div>
    <!-- 좌측 모드 -->
    <LeftMode v-if="isLeft || isMobile" />
    <!-- 상단 모드 -->
    <TopMode v-else-if="isTop" />
    <!-- 혼합 모드 -->
    <LeftTopMode v-else-if="isLeftTop" />
    <!-- 우측 설정 패널 -->
    <RightPanel v-if="showSettings">
      <Settings />
    </RightPanel>
  </div>
</template>
