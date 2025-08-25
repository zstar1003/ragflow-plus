<script lang="ts" setup>
import type { NotifyItem } from "./type"
import { Bell } from "@element-plus/icons-vue"
import { messageData, notifyData, todoData } from "./data"
import List from "./List.vue"

type TabName = "알림" | "메시지" | "할일"

interface DataItem {
  name: TabName
  type: "primary" | "success" | "warning" | "danger" | "info"
  list: NotifyItem[]
}

/** 각 탭의 배지 현재값 */
const badgeValue = computed(() => data.value.reduce((sum, item) => sum + item.list.length, 0))

/** 각 탭의 배지 최대값 */
const badgeMax = 99

/** 팝오버 패널 너비 */
const popoverWidth = 350

/** 현재 활성화된 탭 */
const activeName = ref<TabName>("알림")

/** 모든 데이터 */
const data = ref<DataItem[]>([
  // 알림 데이터
  {
    name: "알림",
    type: "primary",
    list: notifyData
  },
  // 메시지 데이터
  {
    name: "메시지",
    type: "danger",
    list: messageData
  },
  // 할일 데이터
  {
    name: "할일",
    type: "warning",
    list: todoData
  }
])

function handleHistory() {
  ElMessage.success(`${activeName.value} 히스토리 페이지로 이동`)
}
</script>

<template>
  <div class="notify">
    <el-popover placement="bottom" :width="popoverWidth" trigger="click">
      <template #reference>
        <el-badge :value="badgeValue" :max="badgeMax" :hidden="badgeValue === 0">
          <el-tooltip effect="dark" content="메시지 알림" placement="bottom">
            <el-icon :size="20">
              <Bell />
            </el-icon>
          </el-tooltip>
        </el-badge>
      </template>
      <template #default>
        <el-tabs v-model="activeName" class="demo-tabs" stretch>
          <el-tab-pane v-for="(item, index) in data" :key="index" :name="item.name">
            <template #label>
              {{ item.name }}
              <el-badge :value="item.list.length" :max="badgeMax" :type="item.type" />
            </template>
            <el-scrollbar height="400px">
              <List :data="item.list" />
            </el-scrollbar>
          </el-tab-pane>
        </el-tabs>
        <div class="notify-history">
          <el-button link @click="handleHistory">
            {{ activeName }} 히스토리 보기
          </el-button>
        </div>
      </template>
    </el-popover>
  </div>
</template>

<style lang="scss" scoped>
.notify-history {
  text-align: center;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color);
}
</style>
