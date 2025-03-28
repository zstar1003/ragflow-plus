export interface LoginRequestData {
  /** admin 或 editor */
  username: "admin" | "editor"
  /** 密码 */
  password: string
}

export type CaptchaResponseData = ApiResponseData<string>

export type LoginResponseData = ApiResponseData<{ token: string }>
