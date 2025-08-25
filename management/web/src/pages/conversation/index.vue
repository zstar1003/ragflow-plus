<script lang="ts" setup>
import type { TableData } from "@@/apis/tables/type"
import { getTableDataApi } from "@@/apis/tables"
import { ChatDotRound, User } from "@element-plus/icons-vue"
import axios from "axios"

defineOptions({
  // 현재 컴포넌트 명명
  name: "ConversationManagement"
})

// #region 사용자 데이터
const userList = ref<TableData[]>([])
const searchData = reactive({
  username: "",
  email: ""
})

// 사용자 목록 스크롤 로딩 관련
const userLoading = ref(false)
const userHasMore = ref(true)
const userPage = ref(1)
const userPageSize = 20

// 정렬 상태
const sortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc" // 기본 정렬 순서 (최신 생성순)
})

/**
 * 사용자 목록 데이터 가져오기
 * @param isLoadMore 더 불러오기 작업 여부
 */
function getUserData(isLoadMore = false) {
  if (!isLoadMore) {
    userPage.value = 1
    userList.value = []
  }

  userLoading.value = true
  getTableDataApi({
    currentPage: userPage.value,
    size: userPageSize,
    username: searchData.username,
    email: searchData.email,
    sort_by: sortData.sortBy,
    sort_order: sortData.sortOrder
  }).then(({ data }) => {
    if (isLoadMore) {
      userList.value = [...userList.value, ...data.list]
    } else {
      userList.value = data.list
    }

    // 더 많은 데이터가 있는지 판단
    userHasMore.value = userList.value.length < data.total
  }).catch(() => {
    if (!isLoadMore) {
      userList.value = []
    }
  }).finally(() => {
    userLoading.value = false
  })
}

/**
 * 더 많은 사용자 불러오기
 */
function loadMoreUsers() {
  if (userLoading.value || !userHasMore.value) return

  userPage.value++
  getUserData(true)
}

/**
 * 사용자 목록 스크롤 이벤트 모니터링
 * @param event DOM 스크롤 이벤트 객체
 */
function handleUserListScroll(event: Event) {
  // event.target을 HTMLElement로 단언하고 존재 여부 확인
  const target = event.target as HTMLElement
  if (!target) return

  // 스크롤 관련 속성 가져오기
  const { scrollTop, scrollHeight, clientHeight } = target

  // 하단으로부터 100px 거리까지 스크롤했을 때 더 많은 데이터 로드
  if (scrollHeight - scrollTop - clientHeight < 100 && userHasMore.value && !userLoading.value) {
    loadMoreUsers()
  }
}
// #endregion

// #region 대화 데이터
// 대화 데이터 타입 정의
interface ConversationData {
  id: string // string 타입으로 수정
  name: string // title을 name으로 수정
  latestMessage: string // latestMessage 필드 추가
  createTime: string // create_time을 createTime으로 수정
  updateTime: string
}

// 메시지 데이터 타입 정의
interface MessageData {
  id: number
  conversation_id: number
  role: string
  content: string
  create_time: string
}

const conversationList = ref<ConversationData[]>([])
const messageList = ref<MessageData[]>([])
const conversationLoading = ref(false)
const messageLoading = ref(false)

// 대화 목록 스크롤 로딩 관련
const conversationHasMore = ref(true)
const conversationPage = ref(1)
const conversationPageSize = 20

// 메시지 목록 스크롤 로딩 관련
const messageHasMore = ref(true)
const messagePage = ref(1)
const messagePageSize = 30

// 현재 선택된 사용자와 대화
const selectedUser = ref<TableData | null>(null)
const selectedConversation = ref<ConversationData | null>(null)

/**
 * 사용자 선택
 * @param user 사용자 데이터
 */
function selectUser(user: TableData) {
  selectedUser.value = user
  selectedConversation.value = null
  messageList.value = []
  conversationPage.value = 1
  conversationHasMore.value = true
  getConversationsByUserId(user.id)
}

/**
 * 대화 선택
 * @param conversation 대화 데이터
 */
function selectConversation(conversation: ConversationData) {
  selectedConversation.value = conversation
  messagePage.value = 1
  messageHasMore.value = true
  messageList.value = []
  getMessagesByConversationId(conversation.id)
}

/**
 * 사용자의 대화 목록 가져오기
 * @param userId 사용자 ID
 * @param isLoadMore 더 불러오기 작업 여부
 */
function getConversationsByUserId(userId: string, isLoadMore = false) {
  conversationLoading.value = true
  // 대화 목록 API 호출
  axios.get(`/api/v1/conversation`, {
    params: {
      user_id: userId,
      page: conversationPage.value,
      size: conversationPageSize,
      sort_by: "update_time",
      sort_order: "desc"
    }
  }).then((response) => {
    const data = response.data.data

    if (isLoadMore) {
      conversationList.value = [...conversationList.value, ...(data.list || [])]
    } else {
      conversationList.value = data.list || []
    }

    // 더 많은 데이터가 있는지 판단
    conversationHasMore.value = conversationList.value.length < (data.total || 0)
  }).catch((error) => {
    console.error("대화 목록 가져오기 실패:", error)
    ElMessage.error("대화 목록 가져오기 실패")
    if (!isLoadMore) {
      conversationList.value = []
    }
  }).finally(() => {
    conversationLoading.value = false
  })
}

/**
 * 더 많은 대화 불러오기
 */
function loadMoreConversations() {
  if (conversationLoading.value || !conversationHasMore.value || !selectedUser.value) return

  conversationPage.value++
  getConversationsByUserId(selectedUser.value.id, true)
}

/**
 * 대화 목록 스크롤 이벤트 모니터링
 * @param event DOM 스크롤 이벤트 객체
 */
function handleConversationListScroll(event: Event) {
  // event.target을 HTMLElement로 단언하고 존재 여부 확인
  const target = event.target as HTMLElement
  if (!target) return

  // 스크롤 관련 속성 가져오기
  const { scrollTop, scrollHeight, clientHeight } = target

  // 하단으로부터 100px 거리까지 스크롤했을 때 더 많은 데이터 로드
  if (scrollHeight - scrollTop - clientHeight < 100 && conversationHasMore.value && !conversationLoading.value) {
    loadMoreConversations()
  }
}

/**
 * 대화의 메시지 목록 가져오기
 * @param conversationId 대화 ID
 * @param isLoadMore 더 불러오기 작업 여부
 */
function getMessagesByConversationId(conversationId: string, isLoadMore = false) {
  messageLoading.value = true

  // 메시지 목록 API 호출
  axios.get(`/api/v1/conversation/${conversationId}/messages`, {
    params: {
      page: messagePage.value,
      size: messagePageSize,
      sort_by: "create_time",
      sort_order: "asc" // 시간순 정렬, 오래된 메시지가 앞에
    }
  })
    .then((response) => {
      const data = response.data
      // 콘솔에 가져온 메시지 데이터 출력
      console.log("가져온 메시지 데이터:", data)

      // 메시지 데이터 처리
      let processedMessages = []

      if (data.data && data.data.list) {
        const conversation = data.data.list

        // messages 필드가 문자열인지 확인하고, 문자열이면 JSON 객체로 파싱
        if (conversation.messages && typeof conversation.messages === "string") {
          try {
            const parsedMessages = JSON.parse(conversation.messages)

            // 메시지 데이터 포맷팅
            processedMessages = parsedMessages.map((msg: { id: any, role: any, content: any, created_at: number }, index: any) => {
              return {
                id: msg.id || `msg-${index}`,
                conversation_id: conversationId,
                role: msg.role || "unknown",
                content: msg.content || "",
                create_time: msg.created_at ? new Date(msg.created_at * 1000).toISOString() : conversation.createTime
              }
            })
          } catch (error) {
            console.error("메시지 데이터 파싱 실패:", error)
            processedMessages = []
          }
        }
      }

      console.log("처리된 메시지 데이터:", processedMessages)

      if (isLoadMore) {
        // 중복 로딩 방지: 새 메시지가 이미 존재하는지 확인
        const existingIds = new Set(messageList.value.map(msg => msg.id))
        const uniqueNewMessages = processedMessages.filter((msg: { id: number }) => !existingIds.has(msg.id))

        // 새로운 고유 메시지 추가
        messageList.value = [...messageList.value, ...uniqueNewMessages]
        console.log(`${uniqueNewMessages.length}개의 새 메시지를 로드했습니다. ${processedMessages.length - uniqueNewMessages.length}개의 중복 메시지를 필터링했습니다.`)
      } else {
        messageList.value = processedMessages
      }

      // 더 많은 데이터가 있는지 판단
      messageHasMore.value = messageList.value.length < (data.data.total || 0)

      // 더 불러오기가 아닌 경우 하단으로 스크롤
      if (!isLoadMore && messageList.value.length > 0) {
        setTimeout(() => {
          const messageListEl = document.querySelector(".message-list")
          if (messageListEl) {
            messageListEl.scrollTop = messageListEl.scrollHeight
          }
        }, 100)
      }
    })
    .catch((error) => {
      console.error("메시지 목록 가져오기 실패:", error)
      ElMessage.error("메시지 목록 가져오기 실패")
      if (!isLoadMore) {
        messageList.value = []
      }
    })
    .finally(() => {
      messageLoading.value = false
    })
}

/**
 * 메시지 내용 렌더링, 이미지와 링크 처리
 * @param content 메시지 내용
 * @returns 처리된 HTML 내용
 */
function renderMessageContent(content: string) {
  if (!content) return ""

  // Markdown 형식의 이미지 처리
  let processedContent = content.replace(/!\[.*?\]\((.*?)\)/g, "<img src=\"$1\" class=\"message-image\" />")

  // 줄바꿈 문자 처리
  processedContent = processedContent.replace(/\n/g, "<br>")

  return processedContent
}

/**
 * 더 많은 메시지 불러오기
 */
function loadMoreMessages() {
  if (messageLoading.value || !messageHasMore.value || !selectedConversation.value) return

  messagePage.value++
  getMessagesByConversationId(selectedConversation.value.id, true)
}

/**
 * 메시지 목록 스크롤 이벤트 모니터링
 * @param event DOM 스크롤 이벤트 객체
 */
function handleMessageListScroll(event: Event) {
  // event.target을 HTMLElement로 단언하고 존재 여부 확인
  const target = event.target as HTMLElement
  if (!target) return

  // 스크롤 관련 속성 가져오기
  const { scrollTop, scrollHeight, clientHeight } = target

  // 하단으로부터 100px 거리까지 스크롤했을 때 더 많은 데이터 로드 (아래로 스크롤하여 더 불러오기)
  if (scrollHeight - scrollTop - clientHeight < 100 && messageHasMore.value && !messageLoading.value) {
    loadMoreMessages()
  }
}

// 초기 사용자 데이터 로드
onMounted(() => {
  getUserData()
})
</script>

<template>
  <div class="app-container">
    <!-- 다단계 카드 영역 -->
    <div class="conversation-cards-container">
      <!-- 첫 번째 카드: 사용자 목록 -->
      <el-card shadow="hover" class="user-card">
        <template #header>
          <div class="card-header">
            <span>사용자 목록</span>
          </div>
        </template>
        <div class="user-list" @scroll="handleUserListScroll">
          <div
            v-for="user in userList"
            :key="user.id"
            class="user-item"
            :class="{ active: selectedUser?.id === user.id }"
            @click="selectUser(user)"
          >
            <el-avatar :size="32" :icon="User" />
            <div class="user-info">
              <div class="username">
                {{ user.username }}
              </div>
              <div class="email">
                {{ user.email }}
              </div>
            </div>
          </div>
          <div v-if="userLoading" class="loading-more">
            <el-icon class="loading-icon">
              <Loading />
            </el-icon>
            <span>로딩 중...</span>
          </div>
          <el-empty v-if="userList.length === 0 && !userLoading" description="사용자 데이터 없음" />
        </div>
      </el-card>

      <!-- 두 번째 카드: 대화 제목 목록 -->
      <el-card shadow="hover" class="conversation-card">
        <template #header>
          <div class="card-header">
            <span>대화 목록</span>
          </div>
        </template>
        <div class="conversation-list" @scroll="handleConversationListScroll">
          <template v-if="selectedUser">
            <div
              v-for="conversation in conversationList"
              :key="conversation.id"
              class="conversation-item"
              :class="{ active: selectedConversation?.id === conversation.id }"
              @click="selectConversation(conversation)"
            >
              <div class="conversation-icon">
                <el-icon><ChatDotRound /></el-icon>
              </div>
              <div class="conversation-info">
                <div class="conversation-title">
                  {{ conversation.name }}
                </div>
                <div class="conversation-meta">
                  <span>{{ new Date(conversation.updateTime).toLocaleString() }}</span>
                </div>
              </div>
            </div>
            <div v-if="conversationLoading" class="loading-more">
              <el-icon class="loading-icon">
                <Loading />
              </el-icon>
              <span>로딩 중...</span>
            </div>
            <el-empty v-if="conversationList.length === 0 && !conversationLoading" description="대화 데이터 없음" />
          </template>
          <el-empty v-else description="먼저 사용자를 선택해주세요" />
        </div>
      </el-card>

      <!-- 세 번째 카드: 대화 내용 -->
      <el-card shadow="hover" class="message-card">
        <template #header>
          <div class="card-header">
            <span>대화 제목: {{ selectedConversation?.name || '대화 미선택' }}</span>
          </div>
        </template>
        <div class="message-list" @scroll="handleMessageListScroll">
          <template v-if="selectedConversation">
            <div
              v-for="message in messageList"
              :key="message.id"
              class="message-item"
              :class="{ 'user-message': message.role === 'user', 'assistant-message': message.role === 'assistant' }"
            >
              <div class="message-header">
                <span class="message-role">{{ message.role === 'user' ? '사용자' : '어시스턴트' }}</span>
                <span class="message-time">{{ new Date(message.create_time).toLocaleString() }}</span>
              </div>
              <div class="message-content" v-html="renderMessageContent(message.content)" />
            </div>
            <el-empty v-if="messageList.length === 0 && !messageLoading" description="메시지 데이터 없음" />
            <!-- 로딩 힌트 -->
            <!-- <div v-if="messageHasMore" class="loading-more bottom-loading">
              <el-icon class="loading-icon" :class="{ 'is-loading': messageLoading }">
                <Loading />
              </el-icon>
              <span>{{ messageLoading ? '로딩 중...' : '아래로 스크롤하여 더 불러오기' }}</span>
            </div> -->
          </template>
          <el-empty v-else description="먼저 대화를 선택해주세요" />
        </div>
      </el-card>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.search-wrapper {
  margin-bottom: 20px;
  :deep(.el-card__body) {
    padding-bottom: 2px;
  }
}

.conversation-cards-container {
  display: flex;
  gap: 20px;
  height: calc(100vh - 240px);
  min-height: 750px;
  overflow-x: auto; /* 수평 스크롤 추가 */
  padding-bottom: 10px; /* 하단 내부 여백 추가, 스크롤바가 내용을 가리지 않도록 */
}

.user-card {
  width: 25%;
  min-width: 250px; /* 최소 너비 설정, 카드가 너무 작아지지 않도록 */
  display: flex;
  flex-direction: column;
  flex-shrink: 0; /* 카드가 압축되지 않도록 방지 */
}

.conversation-card {
  width: 25%;
  min-width: 250px; /* 최소 너비 설정, 카드가 너무 작아지지 않도록 */
  display: flex;
  flex-direction: column;
  flex-shrink: 0; /* 카드가 압축되지 않도록 방지 */
}

.message-card {
  flex: 1;
  min-width: 300px; /* 최소 너비 설정, 카드가 너무 작아지지 않도록 */
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.user-list,
.conversation-list,
.message-list {
  overflow-y: auto;
  flex: 1;
  position: relative;
  padding: 0 4px;
  max-height: calc(100vh - 300px); /* 최대 높이 설정, 내용이 스크롤되도록 보장 */

  &::-webkit-scrollbar {
    width: 6px;
    height: 6px; /* 수평 스크롤바 높이 추가 */
  }

  &::-webkit-scrollbar-thumb {
    background-color: var(--el-border-color-darker);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-track {
    background-color: var(--el-fill-color-lighter);
    border-radius: 3px;
  }
}

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;

  .loading-icon {
    margin-right: 6px;
    animation: rotating 2s linear infinite;
  }

  &.top-loading {
    position: sticky;
    top: 0;
    background-color: rgba(255, 255, 255, 0.8);
    z-index: 1;
  }

  &.bottom-loading {
    position: sticky;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.8);
    z-index: 1;
  }
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.user-item {
  display: flex;
  align-items: center;
  padding: 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
  margin-bottom: 8px;

  &:hover {
    background-color: var(--el-fill-color-light);
  }

  &.active {
    background-color: var(--el-color-primary-light-9);
  }

  .user-info {
    margin-left: 10px;

    .username {
      font-weight: bold;
    }

    .email {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }
}

.conversation-item {
  display: flex;
  align-items: center;
  padding: 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
  margin-bottom: 8px;

  &:hover {
    background-color: var(--el-fill-color-light);
  }

  &.active {
    background-color: var(--el-color-primary-light-9);
  }

  .conversation-icon {
    font-size: 20px;
    color: var(--el-color-primary);
  }

  .conversation-info {
    margin-left: 10px;
    flex: 1;

    .conversation-title {
      font-weight: bold;
      margin-bottom: 4px;
    }

    .conversation-meta {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }
}

.message-item {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;

  &.user-message {
    background-color: var(--el-color-primary-light-9);
    margin-left: 20px;
  }

  &.assistant-message {
    background-color: var(--el-fill-color-light);
    margin-right: 20px;
  }

  .message-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;

    .message-role {
      font-weight: bold;
    }

    .message-time {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }

  .message-content {
    white-space: pre-wrap;
    word-break: break-word;
    .message-image {
      max-width: 100%;
      border-radius: 4px;
      margin: 8px 0;
    }
  }
}
</style>

<!-- 전역 스크롤바 스타일 추가 -->
<style lang="scss">
/* 전역 스크롤바 스타일 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-thumb {
  background-color: var(--el-border-color);
  border-radius: 4px;

  &:hover {
    background-color: var(--el-border-color-darker);
  }
}

::-webkit-scrollbar-track {
  background-color: var(--el-fill-color-lighter);
  border-radius: 4px;
}
</style>
