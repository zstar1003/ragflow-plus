export interface LoginRequestData {
  /** admin 또는 editor */
  username: "admin" | "editor"
  /** 비밀번호 */
  password: string
}

export type CaptchaResponseData = ApiResponseData<string>

export type LoginResponseData = ApiResponseData<{ token: string }>
