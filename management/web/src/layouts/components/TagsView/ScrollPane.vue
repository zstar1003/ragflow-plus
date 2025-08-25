<script lang="ts" setup>
import type { ElScrollbar } from "element-plus"
import type { RouterLink } from "vue-router"
import { useSettingsStore } from "@/pinia/stores/settings"
import Screenfull from "@@/components/Screenfull/index.vue"
import { useRouteListener } from "@@/composables/useRouteListener"
import { ArrowLeft, ArrowRight } from "@element-plus/icons-vue"

interface Props {
  tagRefs: InstanceType<typeof RouterLink>[]
}

const props = defineProps<Props>()

const route = useRoute()

const settingsStore = useSettingsStore()

const { listenerRouteChange } = useRouteListener()

/** 스크롤바 컴포넌트 요소의 참조 */
const scrollbarRef = ref<InstanceType<typeof ElScrollbar>>()

/** 스크롤바 내용 요소의 참조 */
const scrollbarContentRef = ref<HTMLDivElement>()

/** 현재 스크롤바가 왼쪽에서 떨어진 거리 */
let currentScrollLeft = 0

/** 매번 스크롤 거리 */
const translateDistance = 200

/** 스크롤 시 트리거 */
function scroll({ scrollLeft }: { scrollLeft: number }) {
  currentScrollLeft = scrollLeft
}

/** 마우스 휠 스크롤 시 트리거 */
function wheelScroll({ deltaY }: WheelEvent) {
  if (deltaY.toString().startsWith("-")) {
    scrollTo("left")
  } else {
    scrollTo("right")
  }
}

/** 필요할 수 있는 너비 가져오기 */
function getWidth() {
  // 스크롤 가능한 내용의 길이
  const scrollbarContentRefWidth = scrollbarContentRef.value!.clientWidth
  // 스크롤 가시 영역 너비
  const scrollbarRefWidth = scrollbarRef.value!.wrapRef!.clientWidth
  // 마지막 남은 스크롤 가능한 너비
  const lastDistance = scrollbarContentRefWidth - scrollbarRefWidth - currentScrollLeft

  return { scrollbarContentRefWidth, scrollbarRefWidth, lastDistance }
}

/** 좌우 스크롤 */
function scrollTo(direction: "left" | "right", distance: number = translateDistance) {
  let scrollLeft = 0
  const { scrollbarContentRefWidth, scrollbarRefWidth, lastDistance } = getWidth()
  // 가로 스크롤바가 없으면 바로 종료
  if (scrollbarRefWidth > scrollbarContentRefWidth) return
  if (direction === "left") {
    scrollLeft = Math.max(0, currentScrollLeft - distance)
  } else {
    scrollLeft = Math.min(currentScrollLeft + distance, currentScrollLeft + lastDistance)
  }
  scrollbarRef.value!.setScrollLeft(scrollLeft)
}

/** 대상 위치로 이동 */
function moveTo() {
  const tagRefs = props.tagRefs
  for (let i = 0; i < tagRefs.length; i++) {
    // @ts-expect-error ignore
    if (route.path === tagRefs[i].$props.to.path) {
      // @ts-expect-error ignore
      const el: HTMLElement = tagRefs[i].$el
      const offsetWidth = el.offsetWidth
      const offsetLeft = el.offsetLeft
      const { scrollbarRefWidth } = getWidth()
      // 현재 tag가 가시 영역 왼쪽에 있을 때
      if (offsetLeft < currentScrollLeft) {
        const distance = currentScrollLeft - offsetLeft
        scrollTo("left", distance)
        return
      }
      // 현재 tag가 가시 영역 오른쪽에 있을 때
      const width = scrollbarRefWidth + currentScrollLeft - offsetWidth
      if (offsetLeft > width) {
        const distance = offsetLeft - width
        scrollTo("right", distance)
        return
      }
    }
  }
}

// 라우트 변경 감지, 대상 위치로 이동
listenerRouteChange(() => {
  nextTick(moveTo)
})
</script>

<template>
  <div class="scroll-container">
    <el-tooltip content="태그를 왼쪽으로 스크롤 (최대 너비 초과 시 클릭 가능)">
      <el-icon class="arrow left" @click="scrollTo('left')">
        <ArrowLeft />
      </el-icon>
    </el-tooltip>
    <el-scrollbar ref="scrollbarRef" @wheel.passive="wheelScroll" @scroll="scroll">
      <div ref="scrollbarContentRef" class="scrollbar-content">
        <slot />
      </div>
    </el-scrollbar>
    <el-tooltip content="태그를 오른쪽으로 스크롤 (최대 너비 초과 시 클릭 가능)">
      <el-icon class="arrow right" @click="scrollTo('right')">
        <ArrowRight />
      </el-icon>
    </el-tooltip>
    <Screenfull v-if="settingsStore.showScreenfull" :content="true" class="screenfull" />
  </div>
</template>

<style lang="scss" scoped>
.scroll-container {
  height: 100%;
  user-select: none;
  display: flex;
  justify-content: space-between;
  .arrow {
    width: 40px;
    height: 100%;
    font-size: 18px;
    cursor: pointer;
    &.left {
      box-shadow: 5px 0 5px -6px var(--el-border-color-darker);
    }
    &.right {
      box-shadow: -5px 0 5px -6px var(--el-border-color-darker);
    }
  }
  .el-scrollbar {
    flex: 1;
    // 줄바꿈 방지 (너비 초과 시 스크롤바 표시)
    white-space: nowrap;
    .scrollbar-content {
      display: inline-block;
    }
  }
  .screenfull {
    width: 40px;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
  }
}
</style>
