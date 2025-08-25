<script lang="ts" setup>
import { useSettingsStore } from "@/pinia/stores/settings"
import { AppMain, Logo, NavigationBar, TagsView } from "../components"

const settingsStore = useSettingsStore()
const { showTagsView, showLogo } = storeToRefs(settingsStore)
</script>

<template>
  <div class="app-wrapper">
    <!-- 헤더 네비게이션 바와 태그 바 -->
    <div class="fixed-header layout-header">
      <div class="content">
        <Logo v-if="showLogo" :collapse="false" class="logo" />
        <NavigationBar class="navigation-bar" />
      </div>
      <TagsView v-show="showTagsView" />
    </div>
    <!-- 메인 컨테이너 -->
    <div :class="{ hasTagsView: showTagsView }" class="main-container">
      <!-- 페이지 메인 콘텐츠 -->
      <AppMain class="app-main" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
@import "@@/assets/styles/mixins.scss";
$transition-time: 0.35s;

.app-wrapper {
  @extend %clearfix;
  width: 100%;
}

.fixed-header {
  position: fixed;
  top: 0;
  z-index: 1002;
  width: 100%;
  .logo {
    width: var(--v3-sidebar-width);
  }
  .content {
    display: flex;
    .navigation-bar {
      flex: 1;
    }
  }
}

.layout-header {
  background-color: var(--v3-header-bg-color);
  box-shadow: var(--v3-header-box-shadow);
  border-bottom: var(--v3-header-border-bottom);
}

.main-container {
  min-height: 100%;
}

.app-main {
  transition: padding-left $transition-time;
  padding-top: var(--v3-navigationbar-height);
  height: 100vh;
  overflow: auto;
}

.hasTagsView {
  .app-main {
    padding-top: var(--v3-header-height);
  }
}
</style>
