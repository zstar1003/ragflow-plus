import type * as Tables from "./type"
import { request } from "@/http/axios"

/** 增 */
export function createTableDataApi(data: Tables.CreateOrUpdateTableRequestData) {
  return request({
    url: "api/v1/users",
    method: "post",
    data
  })
}

/** 删 */
export function deleteTableDataApi(id: number) {
  return request({
    url: `api/v1/users/${id}`,
    method: "delete"
  })
}

/** 改 */
export function updateTableDataApi(data: Tables.CreateOrUpdateTableRequestData) {
  return request({
    url: `api/v1/users/${data.id}`,
    method: "put",
    data
  })
}

/** 查 */
export function getTableDataApi(params: Tables.TableRequestData) {
  return request<Tables.TableResponseData>({
    url: "api/v1/users",
    method: "get",
    params
  })
}

/**
 * 重置用户密码
 * @param userId 用户ID
 * @param password 新密码
 * @returns BaseResponse
 */
export function resetPasswordApi(userId: number, password: string) {
  return request({
    url: `api/v1/users/${userId}/reset-password`,
    method: "put",
    data: { password } // 发送新密码
  })
}
