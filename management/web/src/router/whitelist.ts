import type { RouteLocationNormalizedGeneric, RouteRecordNameGeneric } from "vue-router"

/** 로그인 면제 화이트리스트 (라우트 path 매칭) */
const whiteListByPath: string[] = ["/login"]

/** 로그인 면제 화이트리스트 (라우트 name 매칭) */
const whiteListByName: RouteRecordNameGeneric[] = []

/** 화이트리스트에 있는지 판단 */
export function isWhiteList(to: RouteLocationNormalizedGeneric) {
  // path와 name 중 하나라도 매칭되면 됨
  return whiteListByPath.includes(to.path) || whiteListByName.includes(to.name)
}
