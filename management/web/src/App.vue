<script lang="ts" setup>
import { useGreyAndColorWeakness } from "@@/composables/useGreyAndColorWeakness"
import { useLocale } from "@@/composables/useLocale"
import { usePany } from "@@/composables/usePany"
import { useTheme } from "@@/composables/useTheme"

const { elementLocale } = useLocale()

const { initTheme } = useTheme()
const { initGreyAndColorWeakness } = useGreyAndColorWeakness()
const { initStarNotification, initStoreNotification } = usePany()

// 初始化主题
initTheme()
// 初始化灰色模式和色弱模式
initGreyAndColorWeakness()
// 初始化通知
initStarNotification()
initStoreNotification()
</script>

<template>
  <el-config-provider :locale="elementLocale">
    <router-view />
  </el-config-provider>
</template>
