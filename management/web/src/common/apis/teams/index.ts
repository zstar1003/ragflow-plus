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

// 获取用户列表
export function getUsersApi() {
  return request({
    url: "api/v1/users",
    method: "get"
  })
}
