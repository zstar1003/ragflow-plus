# 贡献指南

本文档提供了向 RAGFlow-Plus 提交贡献的指导原则和主要注意事项。

- 如需报告错误，请通过[GitHub issue](https://github.com/zstar1003/ragflow-plus/issues/new/choose)提交问题。
- 其他疑问可先在[Discussions](https://github.com/zstar1003/ragflow-plus/discussions)中查阅现有讨论或发起新话题。

## 可贡献的内容

以下列举部分可贡献的方向（非完整列表）：

- 提议或实现新功能
- 修复错误
- 添加测试用例或演示案例
- 发布博客或教程
- 更新现有文档、代码或注释
- 建议更友好的错误提示

## 提交拉取请求（PR）

### 通用流程

1. Fork本GitHub仓库
2. 将fork克隆到本地：  
`git clone git@github.com:<你的用户名>/ragflow-plus.git`
3. 创建本地分支：  
`git checkout -b my-branch`
4. 提交信息需包含充分说明：  
`git commit -m '提交信息需包含充分说明'`
5. 推送更改到GitHub（含必要提交信息）：  
`git push origin my-branch`
6. 提交PR等待审核

### PR提交前注意事项

- 大型PR建议拆分为多个独立小PR，便于追踪开发历史
- 单个PR应专注解决一个问题，无关改动需保持最小化
- 新增功能需包含测试用例，既验证代码正确性也防止未来变更引发问题

### PR描述规范

- 标题需简洁清晰且信息完整
- 如关联GitHub issue，请在描述中引用对应编号
- 对**重大变更**或**API修改**需在描述中包含详细设计说明