<!-- eslint-disable vue/custom-event-name-casing -->
<script>
import { getDocumentParseProgress } from "@@/apis/kbs/document"

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
      progressMessage: "正在准备解析...",
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
      this.progressMessage = "正在准备解析..."
      this.logs = []
      this.isCompleted = false
      this.hasError = false
      this.progressStatus = ""
    },

    startPolling() {
      this.resetProgress()
      this.fetchProgress()

      // 每5秒轮询一次进度
      this.pollingInterval = setInterval(() => {
        this.fetchProgress()
      }, 5000)
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
          this.progressMessage = "解析进行中，请稍候..."
          return
        }

        if (response.code === 0) {
          const data = response.data

          // 更新进度
          this.progress = data.progress || 0

          // 更新消息
          if (data.message && data.message !== this.progressMessage) {
            this.progressMessage = data.message

            // 添加到日志
            const now = new Date()
            const timeStr = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}:${now.getSeconds().toString().padStart(2, "0")}`

            this.logs.unshift({
              time: timeStr,
              message: data.message
            })

            // 限制日志数量
            if (this.logs.length > 20) {
              this.logs.pop()
            }
          }

          // 检查是否完成
          if (data.running === "3") {
            this.isCompleted = true
            this.progressStatus = "success"
            this.stopPolling()
            this.$emit("parse-complete")
          }

          // 检查是否出错
          if (data.status === "3") {
            this.hasError = true
            this.progressStatus = "exception"
            this.stopPolling()
            this.$emit("parse-failed", data.message || "解析失败")
          }
        }
      } catch (error) {
        console.error("获取解析进度失败:", error)
      }
    },

    handleClose() {
      this.stopPolling()
      this.dialogVisible = false
    }
  }
}
</script>

<template>
  <div class="document-parse-progress-wrapper">
    <el-dialog v-model="dialogVisible" title="文档解析进度" width="500px">
      <div class="progress-container">
        <el-progress
          :percentage="progressPercentage"
          :status="progressStatus"
        />
        <div class="progress-message">
          {{ progressMessage }}
        </div>

        <div class="progress-logs">
          <div v-for="(log, index) in logs" :key="index" class="log-item">
            <span class="log-time">{{ log.time }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleClose" :disabled="!isCompleted && !hasError">取消</el-button>
          <el-button type="primary" @click="handleClose" v-if="isCompleted || hasError">确定</el-button>
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
}

.log-time {
  color: #909399;
  margin-right: 10px;
}

.log-message {
  color: #606266;
}
</style>
