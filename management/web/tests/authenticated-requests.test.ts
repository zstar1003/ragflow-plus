import { request } from "@/http/axios"
import { downloadFileApi } from "@@/apis/files"
import { uploadFileApiV2 } from "@@/apis/files/upload"
import { addDocumentToKnowledgeBaseApi } from "@@/apis/kbs/knowledgebase"
import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  token: "management-jwt",
  status: 200,
  data: null as unknown,
  adapter: vi.fn(),
  logout: vi.fn(),
  reload: vi.fn(),
  showError: vi.fn()
}))

vi.mock("@@/utils/cache/cookies", () => ({ getToken: () => mocks.token }))
vi.mock("@/pinia/stores/user", () => ({ useUserStore: () => ({ logout: mocks.logout }) }))
vi.mock("element-plus", () => ({ ElMessage: { error: mocks.showError } }))
vi.mock("axios", async (importOriginal) => {
  const actual = await importOriginal<typeof import("axios")>()
  mocks.adapter.mockImplementation(async (config) => {
    const response = {
      config,
      data: mocks.data,
      status: mocks.status,
      statusText: "",
      headers: {},
      request: { responseType: config.responseType }
    }
    // Match the HTTP adapter's settlement, including callers' validateStatus.
    if (config.validateStatus && !config.validateStatus(response.status)) {
      throw new actual.AxiosError("Request failed", "ERR_BAD_REQUEST", config, response.request, response)
    }
    return response
  })
  actual.default.defaults.adapter = mocks.adapter
  return actual
})

beforeEach(() => {
  mocks.token = "management-jwt"
  mocks.status = 200
  mocks.data = { code: 0, data: { list: [], total: 0 }, message: "success" }
  mocks.adapter.mockClear()
  mocks.logout.mockClear()
  mocks.showError.mockClear()
  mocks.reload.mockClear()
  vi.stubGlobal("location", { reload: mocks.reload })
})

describe("authenticated management API requests", () => {
  it.each([
    "/api/v1/conversation",
    "/api/v1/conversation/conversation-id/messages"
  ])("sends the current bearer token for %s and preserves the API payload", async (url) => {
    const response = await request({ url, method: "get", params: { page: 1 } })
    expect(response).toBe(mocks.data)
    const config = mocks.adapter.mock.calls[0][0]
    expect(config.headers.Authorization).toBe("Bearer management-jwt")
    expect(config.url).toBe(url)
    expect(config.params).toEqual({ page: 1 })

    mocks.token = "replacement-jwt"
    await request({ url, method: "get" })
    expect(mocks.adapter.mock.calls[1][0].headers.Authorization).toBe("Bearer replacement-jwt")
  })

  it("accepts the existing created-documents response through the authenticated client", async () => {
    mocks.data = { code: 201, data: { added_count: 1 }, message: "created" }
    const fileIds = ["file-id", "000123", "9007199254740993"]
    const response = await addDocumentToKnowledgeBaseApi({ kb_id: "kb-id", file_ids: fileIds })
    expect(response).toBe(mocks.data)
    const config = mocks.adapter.mock.calls[0][0]
    expect(config.headers.Authorization).toBe("Bearer management-jwt")
    expect(config.url).toBe("/api/v1/knowledgebases/kb-id/documents")
    expect(JSON.parse(config.data)).toEqual({ file_ids: fileIds })
  })

  it("downloads the actual Blob through the authenticated client", async () => {
    mocks.data = new Blob(["file contents"], { type: "application/octet-stream" })
    expect(await downloadFileApi("file-id")).toBe(mocks.data)
    const config = mocks.adapter.mock.calls[0][0]
    expect(config.headers.Authorization).toBe("Bearer management-jwt")
    expect(config.url).toBe("/api/v1/files/file-id/download")
    expect(config.responseType).toBe("blob")
    expect(config.params).toBeUndefined()
  })

  it.each([401, 403])("rejects a %s download instead of saving the error response", async (status) => {
    mocks.status = status
    mocks.data = new Blob([JSON.stringify({ code: status, message: "denied" })], { type: "application/json" })
    await expect(downloadFileApi("file-id")).rejects.toMatchObject({ response: { status } })
    expect(mocks.logout).toHaveBeenCalledTimes(status === 401 ? 1 : 0)
    expect(mocks.reload).toHaveBeenCalledTimes(status === 401 ? 1 : 0)
  })

  it("keeps multipart uploads authenticated without placing credentials in the URL", async () => {
    const data = new FormData()
    data.append("files", new File(["contents"], "file.txt"))
    await uploadFileApiV2(data)
    const config = mocks.adapter.mock.calls[0][0]
    expect(config.headers.Authorization).toBe("Bearer management-jwt")
    expect(config.url).toBe("/api/v1/files/upload")
    expect(config.params).toBeUndefined()
  })

  it("does not invent a bearer token when signed out", async () => {
    mocks.token = ""
    await request({ url: "/api/v1/auth/login", method: "post" })
    expect(mocks.adapter.mock.calls[0][0].headers.Authorization).toBeUndefined()
  })
})
