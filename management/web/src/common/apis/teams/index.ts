import type * as Tables from "./type"
import { request } from "@/http/axios"

// 查询团队整体数据
export function getTableDataApi(params: Tables.TableRequestData) {
  return request<Tables.TableResponseData>({
    url: "api/v1/teams",
    method: "get",
    params
  })
}

// 获取团队成员列表
export function getTeamMembersApi(teamId: number) {
  return request({
    url: `api/v1/teams/${teamId}/members`,
    method: "get"
  })
}

// 添加团队成员
export function addTeamMemberApi(data: { teamId: number, userId: number, role: string }) {
  return request({
    url: `api/v1/teams/${data.teamId}/members`,
    method: "post",
    data
  })
}

// 移除团队成员
export function removeTeamMemberApi(data: { teamId: number, memberId: number }) {
  return request({
    url: `api/v1/teams/${data.teamId}/members/${data.memberId}`,
    method: "delete"
  })
}

/**
 * @description 获取用户列表
 * @param params 查询参数，例如 { size: number, currentPage: number, username: string }
 */
export function getUsersApi(params?: object) {
  return request({
    url: "api/v1/users",
    method: "get",
    params
  })
}
