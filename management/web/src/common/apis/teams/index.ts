import type * as Tables from "./type"
import { request } from "@/http/axios"

// 팀 전체 데이터 조회
export function getTableDataApi(params: Tables.TableRequestData) {
  return request<Tables.TableResponseData>({
    url: "api/v1/teams",
    method: "get",
    params
  })
}

// 팀 멤버 목록 가져오기
export function getTeamMembersApi(teamId: number) {
  return request({
    url: `api/v1/teams/${teamId}/members`,
    method: "get"
  })
}

// 팀 멤버 추가
export function addTeamMemberApi(data: { teamId: number, userId: number, role: string }) {
  return request({
    url: `api/v1/teams/${data.teamId}/members`,
    method: "post",
    data
  })
}

// 팀 멤버 제거
export function removeTeamMemberApi(data: { teamId: number, memberId: number }) {
  return request({
    url: `api/v1/teams/${data.teamId}/members/${data.memberId}`,
    method: "delete"
  })
}

/**
 * @description 사용자 목록 가져오기
 * @param params 조회 파라미터, 예: { size: number, currentPage: number, username: string }
 */
export function getUsersApi(params?: object) {
  return request({
    url: "api/v1/users",
    method: "get",
    params
  })
}
