import UserManagement from "@/pages/user-management/index.vue"
import { useLocale } from "@@/composables/useLocale"
import { flushPromises, mount } from "@vue/test-utils"
import ElementPlus from "element-plus"
import { afterEach, describe, expect, it, vi } from "vitest"
import { nextTick } from "vue"

vi.mock("@@/apis/tables", () => ({
  getTableDataApi: vi.fn().mockResolvedValue({ data: { list: [], total: 0 } }),
  createTableDataApi: vi.fn(),
  updateTableDataApi: vi.fn(),
  deleteTableDataApi: vi.fn(),
  resetPasswordApi: vi.fn()
}))

afterEach(() => useLocale().setLocale("zh-CN"))

describe("user management localization", () => {
  it("updates table, search and open create dialog on language changes", async () => {
    const wrapper = mount(UserManagement, { global: { plugins: [ElementPlus], stubs: { ElTable: { template: "<div><slot /></div>" }, ElTableColumn: { props: ["label"], template: "<span>{{ label }}</span>" } } }, attachTo: document.body })
    await flushPromises()
    expect(wrapper.text()).toContain("新增用户")
    const add = wrapper.findAll("button").find(button => button.text().includes("新增用户"))!
    await add.trigger("click")
    await nextTick()
    useLocale().setLocale("en")
    await nextTick()
    expect(wrapper.text()).toContain("Add user")
    expect(wrapper.text()).toContain("Username")
    expect(wrapper.text()).not.toContain("批量删除")
    expect(document.body.textContent).toContain("User email")
    expect(document.body.textContent).toContain("Password")
    useLocale().setLocale("zh-CN")
    await nextTick()
    expect(wrapper.text()).toContain("批量删除")
    wrapper.unmount()
  })
})
