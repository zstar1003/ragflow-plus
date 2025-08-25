<script lang="ts" setup>
import { useSettingsStore } from "@/pinia/stores/settings"
import { useTagsViewStore } from "@/pinia/stores/tags-view"
import { Footer } from "../index"

const tagsViewStore = useTagsViewStore()
const settingsStore = useSettingsStore()
</script>

<template>
  <section class="app-main">
    <div class="app-scrollbar">
      <!-- key에 route.path와 route.fullPath를 사용하면 다른 효과가 있으며, 대부분의 경우 path가 더 범용적입니다 -->
      <router-view v-slot="{ Component, route }">
        <transition name="el-fade-in" mode="out-in">
          <keep-alive :include="tagsViewStore.cachedViews">
            <component :is="Component" :key="route.path" class="app-container-grow" />
          </keep-alive>
        </transition>
      </router-view>
      <!-- 푸터 -->
      <Footer v-if="settingsStore.showFooter" />
    </div>
    <!-- 맨 위로 돌아가기 -->
    <el-backtop />
    <!-- 맨 위로 돌아가기 (고정 Header인 경우) -->
    <el-backtop target=".app-scrollbar" />
  </section>
</template>

<style lang="scss" scoped>
@import "@@/assets/styles/mixins.scss";

.app-main {
  width: 100%;
  display: flex;
}

.app-scrollbar {
  flex-grow: 1;
  overflow: auto;
  @extend %scrollbar;
  display: flex;
  flex-direction: column;
  .app-container-grow {
    flex-grow: 1;
  }
}
</style>
