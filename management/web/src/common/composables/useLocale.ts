import en from "element-plus/es/locale/lang/en"
import zhCn from "element-plus/es/locale/lang/zh-cn"
import { computed, ref } from "vue"

export type Locale = "zh-CN" | "en"
const storageKey = "ragflow-management-locale"

function readLocale(): Locale {
  try {
    return localStorage.getItem(storageKey) === "en" ? "en" : "zh-CN"
  } catch {
    return "zh-CN"
  }
}

const locale = ref<Locale>(readLocale())
const english: Record<string, string> = {
  "用户名": "Username",
  "邮箱": "Email",
  "用户邮箱": "User email",
  "密码": "Password",
  "请输入": "Please enter",
  "请输入用户名": "Please enter a username",
  "请输入邮箱": "Please enter an email address",
  "请输入正确的邮箱格式": "Please enter a valid email address",
  "请输入密码": "Please enter a password",
  "请输入新密码": "Please enter a new password",
  "登录校验不通过": "Please check the form",
  "表单校验不通过": "Please check the form",
  "操作成功": "Operation successful",
  "用户ID丢失，无法重置密码": "Missing user ID; cannot reset password",
  "密码重置成功": "Password reset successfully",
  "密码重置失败": "Password reset failed",
  "提示": "Confirmation",
  "确定": "Confirm",
  "取消": "Cancel",
  "删除成功": "User deleted",
  "请至少选择一条记录": "Please select at least one record",
  "批量删除成功": "Selected users deleted",
  "批量删除失败": "Could not delete all selected users",
  "查询": "Search",
  "重置": "Reset",
  "新增用户": "Add user",
  "批量删除": "Delete selected",
  "刷新当前页": "Refresh this page",
  "创建时间": "Created at",
  "更新时间": "Updated at",
  "操作": "Actions",
  "修改用户名": "Edit username",
  "重置密码": "Reset password",
  "删除": "Delete",
  "修改用户": "Edit user",
  "确认": "Confirm",
  "新密码": "New password",
  "确认重置": "Confirm reset",
  "登 录": "Sign in",
  "退出登录": "Sign out",
  "用户管理": "User management",
  "团队管理": "Team management",
  "用户配置": "User settings",
  "文件管理": "Files",
  "知识库管理": "Knowledge bases",
  "用户会话管理": "User conversations",
  "刷新": "Refresh",
  "关闭": "Close",
  "关闭其它": "Close others",
  "关闭所有": "Close all",
  "正在删除用户：{name}，确认删除？": "Delete user {name}?",
  "确认删除选中的 {count} 条记录吗？": "Delete the {count} selected records?"
}

function setLocale(value: Locale) {
  if (value !== "en" && value !== "zh-CN") return
  locale.value = value
  try {
    localStorage.setItem(storageKey, value)
  } catch {
    // Language switching still works when browser storage is unavailable.
  }
}

function t(message: string | undefined, params: Record<string, string | number> = {}) {
  const source = message ?? ""
  const translated = locale.value === "en" ? (english[source] ?? source) : source
  return translated.replace(/\{(\w+)\}/g, (match, key) => String(params[key] ?? match))
}

const elementLocale = computed(() => locale.value === "en" ? en : zhCn)

export function useLocale() {
  return { locale: computed(() => locale.value), elementLocale, setLocale, t }
}
