<script lang="ts" setup>
import { useLocale } from "@@/composables/useLocale"

const { locale, setLocale } = useLocale()
</script>

<template>
  <select :value="locale" aria-label="Language / 语言" class="language-switch" @change="setLocale(($event.target as HTMLSelectElement).value as 'en' | 'zh-CN')">
    <option value="zh-CN">
      简体中文
    </option>
    <option value="en">
      English
    </option>
  </select>
</template>

<style scoped>
.language-switch {
  padding: 6px;
  color: var(--el-text-color-primary);
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}
</style>
