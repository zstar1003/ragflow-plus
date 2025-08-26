import type * as Auth from "./type"
import { request } from "@/http/axios"

/** 로그인 인증코드 가져오기 */
// export function getCaptchaApi() {
//   return request<Auth.CaptchaResponseData>({
//     url: "v1/auth/captcha",
//     method: "get"
//   })
// }

/** 로그인하고 Token 반환 */
export function loginApi(data: Auth.LoginRequestData) {
  return request<Auth.LoginResponseData>({
    url: "/api/v1/auth/login",
    method: "post",
    data
  })
}
