<script lang="ts" setup>
import { useSettingsStore } from "@/pinia/stores/settings"
import { useLayoutMode } from "@@/composables/useLayoutMode"
import { removeLayoutsConfig } from "@@/utils/cache/local-storage"
import { Refresh } from "@element-plus/icons-vue"
import SelectLayoutMode from "./SelectLayoutMode.vue"

const { isLeft } = useLayoutMode()

const settingsStore = useSettingsStore()

// storeToRefs를 사용하여 추출된 속성의 반응성 유지
const {
  showTagsView,
  showLogo,
  fixedHeader,
  showFooter,
  showNotify,
  showThemeSwitch,
  showScreenfull,
  showSearchMenu,
  cacheTagsView,
  showWatermark,
  showGreyMode,
  showColorWeakness
} = storeToRefs(settingsStore)

/** switch 설정 항목 정의 */
const switchSettings = {
  "태그 바 표시": showTagsView,
  "로고 표시": showLogo,
  "Header 고정": fixedHeader,
  "푸터 표시": showFooter,
  "메시지 알림 표시": showNotify,
  "테마 전환 버튼 표시": showThemeSwitch,
  "전체화면 버튼 표시": showScreenfull,
  "검색 버튼 표시": showSearchMenu,
  "태그 바 캐시 여부": cacheTagsView,
  "시스템 워터마크 활성화": showWatermark,
  "회색 모드 표시": showGreyMode,
  "색약 모드 표시": showColorWeakness
}

// 좌측 모드가 아닐 때 Header는 모두 fixed 레이아웃
watchEffect(() => {
  !isLeft.value && (fixedHeader.value = true)
})

/** 프로젝트 설정 초기화 */
function resetLayoutsConfig() {
  removeLayoutsConfig()
  location.reload()
}
</script>

<template>
  <div class="setting-container">
    <h4>레이아웃 설정</h4>
    <SelectLayoutMode />
    <el-divider />
    <h4>기능 설정</h4>
    <div v-for="(settingValue, settingName, index) in switchSettings" :key="index" class="setting-item">
      <span class="setting-name">{{ settingName }}</span>
      <el-switch v-model="settingValue.value" :disabled="!isLeft && settingName === 'Header 고정'" />
    </div>
    <el-button type="danger" :icon="Refresh" @click="resetLayoutsConfig">
      초기화
    </el-button>
  </div>
</template>

<style lang="scss" scoped>
@import "@@/assets/styles/mixins.scss";

.setting-container {
  padding: 20px;
  .setting-item {
    font-size: 14px;
    color: var(--el-text-color-regular);
    padding: 5px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    .setting-name {
      @extend %ellipsis;
    }
  }
  .el-button {
    margin-top: 40px;
    width: 100%;
  }
}
</style>
