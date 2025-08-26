<script lang="ts" setup>
import type { FormInstance, FormRules } from "element-plus"
import type { LoginRequestData } from "./apis/type"
import { useSettingsStore } from "@/pinia/stores/settings"
import { useUserStore } from "@/pinia/stores/user"
import ThemeSwitch from "@@/components/ThemeSwitch/index.vue"
import { Key, Loading, Lock, Picture, User } from "@element-plus/icons-vue"
import { loginApi } from "./apis"
import Owl from "./components/Owl.vue"
import { useFocus } from "./composables/useFocus"

const router = useRouter()

const userStore = useUserStore()

const settingsStore = useSettingsStore()

const { isFocus, handleBlur, handleFocus } = useFocus()

/** 로그인 폼 요소의 참조 */
const loginFormRef = ref<FormInstance | null>(null)

/** 로그인 버튼 Loading */
const loading = ref(false)

/** 인증코드 이미지 URL */
// const codeUrl = ref("")

/** 로그인 폼 데이터 */
const loginFormData: LoginRequestData = reactive({
  username: import.meta.env.VITE_DEFAULT_USERNAME || "admin",
  password: import.meta.env.VITE_DEFAULT_PASSWORD || "12345678",
  code: ""
})

/** 로그인 폼 검증 규칙 */
const loginFormRules: FormRules = {
  username: [
    { required: true, message: "사용자명을 입력하세요", trigger: "blur" }
  ],
  password: [
    { required: true, message: "비밀번호를 입력하세요", trigger: "blur" },
    { min: 8, max: 16, message: "길이는 8~16자여야 합니다", trigger: "blur" }
  ]
}

/** 로그인 */
function handleLogin() {
  loginFormRef.value?.validate((valid) => {
    if (!valid) {
      ElMessage.error("폼 검증에 실패했습니다")
      return
    }
    loading.value = true
    loginApi(loginFormData).then(({ data }) => {
      userStore.setToken(data.token)
      router.push("/")
    }).catch(() => {
      loginFormData.password = ""
    }).finally(() => {
      loading.value = false
    })
  })
}

// /** 인증코드 생성 */
// function createCode() {
//   // 입력된 인증코드 초기화
//   loginFormData.code = ""
//   // 인증 이미지 초기화
//   codeUrl.value = ""
//   // 인증코드 이미지 가져오기
//   getCaptchaApi().then((res) => {
//     codeUrl.value = res.data
//   })
// }

// // 인증코드 초기화
// createCode()
</script>

<template>
  <div class="login-container">
    <ThemeSwitch v-if="settingsStore.showThemeSwitch" class="theme-switch" />
    <Owl :close-eyes="isFocus" />
    <div class="login-card">
      <div class="title">
        <img src="@@/assets/images/layouts/logo-text-2.png">
      </div>
      <div class="content">
        <el-form ref="loginFormRef" :model="loginFormData" :rules="loginFormRules" @keyup.enter="handleLogin">
          <el-form-item prop="username">
            <el-input
              v-model.trim="loginFormData.username"
              placeholder="사용자명"
              type="text"
              tabindex="1"
              :prefix-icon="User"
              size="large"
            />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model.trim="loginFormData.password"
              placeholder="비밀번호"
              type="password"
              tabindex="2"
              :prefix-icon="Lock"
              size="large"
              show-password
              @blur="handleBlur"
              @focus="handleFocus"
            />
          </el-form-item>
          <!-- <el-form-item prop="code">
            <el-input
              v-model.trim="loginFormData.code"
              placeholder="인증코드"
              type="text"
              tabindex="3"
              :prefix-icon="Key"
              maxlength="7"
              size="large"
              @blur="handleBlur"
              @focus="handleFocus"
            >
              <template #append>
                <el-image :src="codeUrl" draggable="false" @click="createCode">
                  <template #placeholder>
                    <el-icon>
                      <Picture />
                    </el-icon>
                  </template>
                  <template #error>
                    <el-icon>
                      <Loading />
                    </el-icon>
                  </template>
                </el-image>
              </template>
            </el-input>
          </el-form-item> -->
          <el-button :loading="loading" type="primary" size="large" @click.prevent="handleLogin">
            로그인
          </el-button>
        </el-form>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.login-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  width: 100%;
  min-height: 100%;
  .theme-switch {
    position: fixed;
    top: 5%;
    right: 5%;
    cursor: pointer;
  }
  .login-card {
    width: 480px;
    max-width: 90%;
    border-radius: 20px;
    box-shadow: 0 0 10px #dcdfe6;
    background-color: var(--el-bg-color);
    overflow: hidden;
    .title {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 150px;
      img {
        height: 100%;
      }
    }
    .content {
      padding: 20px 50px 50px 50px;
      :deep(.el-input-group__append) {
        padding: 0;
        overflow: hidden;
        .el-image {
          width: 100px;
          height: 40px;
          border-left: 0px;
          user-select: none;
          cursor: pointer;
          text-align: center;
        }
      }
      .el-button {
        width: 100%;
        margin-top: 10px;
      }
    }
  }
}
</style>
