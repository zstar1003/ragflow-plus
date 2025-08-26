import type { LayoutsConfig } from "@/layouts/config"
import type { Ref } from "vue"
import { layoutsConfig } from "@/layouts/config"
import { pinia } from "@/pinia"
import { setLayoutsConfig } from "@@/utils/cache/local-storage"

type SettingsStore = {
  // 매핑 타입을 사용하여 LayoutsConfig 객체의 키를 순회
  [Key in keyof LayoutsConfig]: Ref<LayoutsConfig[Key]>
}

type SettingsStoreKey = keyof SettingsStore

export const useSettingsStore = defineStore("settings", () => {
  // 상태 객체
  const state = {} as SettingsStore
  // LayoutsConfig 객체의 키-값 쌍을 순회
  for (const [key, value] of Object.entries(layoutsConfig)) {
    // 타입 어설션을 사용하여 key의 타입을 지정하고, value를 ref 함수로 감싸서 반응형 변수 생성
    const refValue = ref(value)
    // @ts-expect-error ignore
    state[key as SettingsStoreKey] = refValue
    // 각 반응형 변수 감시
    watch(refValue, () => {
      // 캐시
      const settings = getCacheData()
      setLayoutsConfig(settings)
    })
  }
  // 캐시할 데이터 가져오기: state 객체를 settings 객체로 변환
  const getCacheData = () => {
    const settings = {} as LayoutsConfig
    for (const [key, value] of Object.entries(state)) {
      // @ts-expect-error ignore
      settings[key as SettingsStoreKey] = value.value
    }
    return settings
  }

  return state
})

/**
 * @description SPA 애플리케이션에서 pinia 인스턴스가 활성화되기 전에 store를 사용할 수 있습니다
 * @description SSR 애플리케이션에서 setup 외부에서 store를 사용할 수 있습니다
 */
export function useSettingsStoreOutside() {
  return useSettingsStore(pinia)
}
