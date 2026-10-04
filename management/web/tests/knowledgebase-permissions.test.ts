import Knowledgebase from "@/pages/knowledgebase/index.vue"
import { installPermissionDirective } from "@/plugins/permission-directive"
import { flushPromises, shallowMount } from "@vue/test-utils"
import { ElMessage } from "element-plus"
import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  roles: ["team_owner"],
  listUsers: vi.fn(),
  create: vi.fn(),
  systemConfig: vi.fn()
}))

vi.mock("@/pinia/stores/user", () => ({ useUserStore: () => ({ roles: mocks.roles }) }))
vi.mock("@@/apis/tables", () => ({ getTableDataApi: mocks.listUsers }))
vi.mock("@@/apis/kbs/knowledgebase", async importOriginal => ({
  ...await importOriginal<typeof import("@@/apis/kbs/knowledgebase")>(),
  getKnowledgeBaseListApi: vi.fn(async () => ({ code: 0, data: { list: [], total: 0 } })),
  createKnowledgeBaseApi: mocks.create,
  getSystemEmbeddingConfigApi: mocks.systemConfig
}))

beforeEach(() => {
  mocks.roles = ["team_owner"]
  mocks.listUsers.mockReset().mockResolvedValue({ data: { list: [] } })
  mocks.create.mockReset().mockResolvedValue({ code: 0 })
  mocks.systemConfig.mockReset().mockResolvedValue({ code: 0, data: { llm_name: "embedding-model" } })
  vi.spyOn(ElMessage, "success").mockImplementation(() => ({ close: vi.fn() }))
})

function mountPage() {
  return shallowMount(Knowledgebase, {
    global: {
      plugins: [{ install: installPermissionDirective }],
      directives: { loading: () => {} },
      renderStubDefaultSlot: true,
      stubs: {
        ElTable: { template: "<div />" },
        ElForm: false,
        ElFormItem: false
      }
    }
  })
}

describe("knowledgebase creation permissions", () => {
  it("lets owners create without global users, credentials, or caller-selected identity", async () => {
    const wrapper = mountPage()
    const page = wrapper.vm as unknown as {
      handleCreate: () => void
      submitCreate: () => Promise<void>
      knowledgeBaseForm: { name: string, creator_id: string }
    }
    page.handleCreate()
    page.knowledgeBaseForm.name = "Owner knowledgebase"
    page.knowledgeBaseForm.creator_id = "stale-foreign-user"
    await flushPromises()
    expect(wrapper.findAllComponents({ name: "ElFormItem" }).some(field => field.props("prop") === "creator_id")).toBe(false)
    expect(wrapper.text()).not.toContain("嵌入模型配置")
    await page.submitCreate()
    expect(mocks.listUsers).not.toHaveBeenCalled()
    expect(mocks.systemConfig).not.toHaveBeenCalled()
    expect(mocks.create).toHaveBeenCalledWith({
      name: "Owner knowledgebase",
      description: "",
      language: "Chinese",
      permission: "me"
    })
    wrapper.unmount()
  })

  it("preserves the administrator creator and embedding selection", async () => {
    mocks.roles = ["admin"]
    const wrapper = mountPage()
    const page = wrapper.vm as unknown as {
      handleCreate: () => void
      submitCreate: () => Promise<void>
      knowledgeBaseForm: { name: string, creator_id: string }
    }
    page.handleCreate()
    page.knowledgeBaseForm.name = "Administrator knowledgebase"
    page.knowledgeBaseForm.creator_id = "selected-user"
    await flushPromises()
    expect(wrapper.findAllComponents({ name: "ElFormItem" }).some(field => field.props("prop") === "creator_id")).toBe(true)
    expect(wrapper.text()).toContain("嵌入模型配置")
    await page.submitCreate()
    expect(mocks.listUsers).toHaveBeenCalledOnce()
    expect(mocks.systemConfig).toHaveBeenCalledOnce()
    expect(mocks.create).toHaveBeenCalledWith(expect.objectContaining({
      creator_id: "selected-user",
      embd_id: "embedding-model"
    }))
    wrapper.unmount()
  })
})
