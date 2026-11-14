import { mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

beforeEach(() => {
  localStorage.clear()
  vi.resetModules()
})
afterEach(() => vi.restoreAllMocks())

describe("management language preference", () => {
  it("defaults to Chinese and localizes Element Plus with English selection", async () => {
    const { useLocale } = await import("@@/composables/useLocale")
    const state = useLocale()
    expect(state.locale.value).toBe("zh-CN")
    expect(state.t("用户名")).toBe("用户名")
    state.setLocale("en")
    expect(state.t("用户名")).toBe("Username")
    expect(state.elementLocale.value.name).toBe("en")
    expect(state.t("正在删除用户：{name}，确认删除？", { name: "Alice <admin>" })).toBe("Delete user Alice <admin>?")
    expect(localStorage.getItem("ragflow-management-locale")).toBe("en")
    vi.resetModules()
    const reloaded = (await import("@@/composables/useLocale")).useLocale()
    expect(reloaded.locale.value).toBe("en")
    reloaded.setLocale("zh-CN")
    expect(reloaded.elementLocale.value.name).toBe("zh-cn")
  })

  it("ignores invalid stored values and tolerates unavailable storage", async () => {
    localStorage.setItem("ragflow-management-locale", "invalid")
    const { useLocale } = await import("@@/composables/useLocale")
    expect(useLocale().locale.value).toBe("zh-CN")
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked")
    })
    expect(() => useLocale().setLocale("en")).not.toThrow()
    expect(useLocale().t("确认")).toBe("Confirm")
  })

  it("switches from the accessible language selector without reloading", async () => {
    const { default: LanguageSwitch } = await import("@@/components/LanguageSwitch/index.vue")
    const { useLocale } = await import("@@/composables/useLocale")
    const wrapper = mount(LanguageSwitch)
    await wrapper.get("select").setValue("en")
    expect(useLocale().locale.value).toBe("en")
    await wrapper.get("select").setValue("zh-CN")
    expect(useLocale().locale.value).toBe("zh-CN")
    wrapper.unmount()
  })
})
