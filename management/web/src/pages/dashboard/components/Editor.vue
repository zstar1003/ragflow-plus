<script lang="ts" setup>
import SvgDashboard from "../images/dashboard.svg?component" // vite-svg-loader 플러그인 기능
</script>

<template>
  <div class="app-container center">
    <SvgDashboard class="svg" />
    <p>「Editor」 역할 전용 홈페이지에 오신 것을 환영합니다</p>
  </div>
</template>

<style lang="scss" scoped>
.center {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  .svg {
    width: 600px;
    max-width: 100%;
  }
}
</style>
