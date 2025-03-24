export const aiAssistantConfig = {
    // 模型配置
    model: {
      modelName: "deepseek-r1:1.5b", // 默认模型
      temperature: 0.7,           // 温度参数
      topP: 0.9,                  // Top-P 参数
      maxTokens: 1024,            // 最大生成 token 数
    },
    
    // API 配置
    api: {
      // 修改为正确的 API 端点格式
      chatEndpoint: "/api/v1/chats",           // 创建聊天会话的端点
      completionEndpoint: "/api/v1/chats/{chat_id}/completions", // 聊天完成的端点
      timeout: 30000,                       // 请求超时时间(ms)
    },
    
    // 默认系统提示词
    systemPrompt: "你是一个专业的写作助手，可以帮助用户改进文档、提供写作建议和回答相关问题。",
  };