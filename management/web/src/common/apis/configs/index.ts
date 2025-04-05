import type * as Tables from "./type"
import { request } from "@/http/axios"

/** 改 */
export function updateTableDataApi(data: Tables.CreateOrUpdateTableRequestData) {
  return request({
    url: `api/v1/tenants/${data.id}`,
    method: "put",
    data
  })
}

/** 查 */
export function getTableDataApi(params: Tables.TableRequestData) {
  return request<Tables.TableResponseData>({
    url: "api/v1/tenants",
    method: "get",
    params
  })
}
