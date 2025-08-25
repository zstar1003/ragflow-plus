<script lang="ts" setup>
import { useDevice } from "@@/composables/useDevice"

interface Props {
  total: number
}

const props = defineProps<Props>()

const { isMobile } = useDevice()
</script>

<template>
  <div class="search-footer">
    <template v-if="!isMobile">
      <span class="search-footer-item">
        <SvgIcon name="keyboard-enter" class="svg-icon" />
        <span>확인</span>
      </span>
      <span class="search-footer-item">
        <SvgIcon name="keyboard-up" class="svg-icon" />
        <SvgIcon name="keyboard-down" class="svg-icon" />
        <span>전환</span>
      </span>
      <span class="search-footer-item">
        <SvgIcon name="keyboard-esc" class="svg-icon" />
        <span>닫기</span>
      </span>
    </template>
    <span class="search-footer-total">총 {{ props.total }}개</span>
  </div>
</template>

<style lang="scss" scoped>
.search-footer {
  display: flex;
  color: var(--el-text-color-secondary);
  font-size: 14px;
  &-item {
    display: flex;
    align-items: center;
    margin-right: 12px;
    .svg-icon {
      margin-right: 5px;
      padding: 2px;
      font-size: 20px;
      background-color: var(--el-fill-color);
    }
  }
  &-total {
    margin: 0 0 0 auto;
  }
}
</style>
