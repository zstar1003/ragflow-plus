<!-- eslint-disable vue/custom-event-name-casing -->
<script>
import { getDocumentParseProgress } from "@@/apis/kbs/document"
import { ElMessage } from "element-plus"

export default {
  name: "DocumentParseProgress",
  props: {
    documentId: {
      type: String,
      required: true
    },
    visible: {
      type: Boolean,
      default: false
    }
  },
  emits: ["close", "parse-complete", "parse-failed"],
  data() {
    return {
      dialogVisible: false,
      progress: 0,
      progressMessage: "파싱 준비 중...",
      logs: [],
      pollingInterval: null,
      isCompleted: false,
      hasError: false,
      progressStatus: ""
    }
  },
  computed: {
    progressPercentage() {
      return Math.round(this.progress * 100)
    }
  },
  watch: {
    visible(newVal) {
      this.dialogVisible = newVal
      if (newVal) {
        this.startPolling()
      } else {
        this.stopPolling()
      }
    },
    dialogVisible(newVal) {
      if (!newVal) {
        this.$emit("close")
      }
    },
    documentId() {
      this.resetProgress()
      if (this.dialogVisible) {
        this.startPolling()
      }
    }
  },
  beforeUnmount() {
    this.stopPolling()
    this.dialogVisible = false
  },
  methods: {
    resetProgress() {
      this.progress = 0
      this.progressMessage = "파싱 준비 중..."
      this.logs = []
      this.isCompleted = false
      this.hasError = false
      this.progressStatus = ""
    },

    startPolling() {
      this.resetProgress()
      this.fetchProgress()

      // 2초마다 진행률을 폴링하여 더 즉시적인 업데이트 제공
      this.pollingInterval = setInterval(() => {
        this.fetchProgress()
      }, 2000)
    },

    stopPolling() {
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval)
        this.pollingInterval = null
      }
    },

    async fetchProgress() {
      try {
        const response = await getDocumentParseProgress(this.documentId)

        if (response?.code === 202) {
          this.progressMessage = "파싱 진행 중, 잠시 기다려 주세요..."
          return
        }

        if (response.code === 0) {
          const data = response.data

          // 진행률 업데이트
          this.progress = data.progress || 0

          // 메시지 업데이트
          if (data.message && data.message !== this.progressMessage) {
            this.progressMessage = data.message

            // 동일한 로그 메시지가 이미 존재하는지 확인하여 중복 방지
            const isDuplicate = this.logs.some(log => log.message === data.message)
            
            if (!isDuplicate) {
              // 로그에 추가 (unshift 대신 push 사용하여 시간 순서 유지)
              const now = new Date()
              const timeStr = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}:${now.getSeconds().toString().padStart(2, "0")}`

              this.logs.push({
                time: timeStr,
                message: data.message
              })

              // 로그 수량 제한, 가장 오래된 로그 제거
              if (this.logs.length > 20) {
                this.logs.shift()
              }
            }
          }

          // 완료 여부 확인
          if (data.running === "3") {
            this.isCompleted = true
            this.progressStatus = "success"
            this.stopPolling()
            this.$emit("parse-complete")
          }

          // 오류 여부 확인
          if (data.status === "3") {
            this.hasError = true
            this.progressStatus = "exception"
            this.stopPolling()
            this.$emit("parse-failed", data.message || "파싱 실패")
          }
        }
      } catch (error) {
        console.error("파싱 진행률 가져오기 실패:", error)
      }
    },

    handleClose() {
      this.stopPolling()
      this.dialogVisible = false
    },

    // 간소화된 진행률 메시지 가져오기
    getSimplifiedMessage() {
      if (this.isCompleted) {
        return "파싱 완료"
      }
      if (this.hasError) {
        return "파싱 실패"
      }
      if (this.progress > 0 && this.progress < 1) {
        return "파싱 중"
      }
      return this.progressMessage || "파싱 준비 중..."
    }
  }
}
</script>

<template>
  <div class="document-parse-progress-wrapper">
    <el-dialog v-model="dialogVisible" title="문서 파싱 진행률" width="500px">
      <div class="progress-container">
        <el-progress
          :percentage="progressPercentage"
          :status="progressStatus"
        />
        <div class="progress-message">
          {{ getSimplifiedMessage() }}
        </div>

        <div class="progress-logs" ref="logsContainer">
          <div v-for="(log, index) in logs" :key="index" class="log-item">
            <span class="log-time">{{ log.time }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleClose" :disabled="!isCompleted && !hasError">취소</el-button>
          <el-button type="primary" @click="handleClose" v-if="isCompleted || hasError">확인</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.progress-container {
  padding: 10px;
}

.progress-message {
  margin-top: 10px;
  font-size: 14px;
  text-align: center;
}


.progress-logs {
  margin-top: 20px;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 10px;
}

.log-item {
  margin-bottom: 5px;
  font-size: 12px;
  line-height: 1.4;
  padding: 2px 0;
  border-bottom: 1px solid #f0f0f0;
}

.log-item:last-child {
  border-bottom: none;
}

.log-time {
  color: #909399;
  margin-right: 10px;
  font-weight: 500;
}

.log-message {
  color: #606266;
  word-break: break-all;
}
</style>
