<div align="center">
  <img src="assets/ragflow-plus.png" width="400" alt="Ragflow-Plus">

</div>

<div align="center">
  <img src="https://img.shields.io/badge/版本-0.2.1-blue" alt="版本">
  <a href="LICENSE"><img src="https://img.shields.io/badge/许可证-AGPL3.0-green" alt="许可证"></a>
  <h4>
    <a href="README.md">🇨🇳 中文</a>
    <span> | </span>
    <a href="README_EN.md">🇬🇧 English</a>
  </h4>
</div>

<h4 align="center">
  <a href="https://xdxsb.top/ragflow-plus">官网</a> |
  <a href="docs/faq.md">常见问题</a> |
  <a href="docs/plan.md">开发计划</a> |
  <a href="docs/images/group.jpg">社群</a>
</h4>

---

## 🌟 简介

Ragflow-Plus 是一个基于 Ragflow 的二次开发项目，目的是解决实际应用中的一些问题，主要有以下特点：

- 管理模式  
额外搭建后台管理系统，支持管理员执行用户管理、团队管理、配置管理、文件管理、知识库管理等功能
- 权限回收  
前台系统对用户权限进行收缩，进一步简化界面
- 解析增强  
使用MinerU替代DeepDoc算法，使文件解析效果更好，并支持图片解析
- 图文输出  
支持模型在回答时，输出引用文本块关联的相关图片
- 文档撰写模式  
支持全新的文档模式交互体验

视频演示及操作教程：

[![Ragflow-Plus项目简介与操作指南](https://i0.hdslb.com/bfs/archive/f7d8da4a112431af523bfb64043fe81da7dad8ee.jpg@672w_378h_1c.avif)](https://www.bilibili.com/video/BV1UJLezaEEE)

> [!NOTE]
> 视频中采用了vllm作为演示示例，vllm默认拉取使用的模型是float16精度，导致众多用户因显存不足无法正常使用，因此将vllm容器进行注释，除非对vllm比较了解，否则建议使用ollama进行配置。

## 📥使用方式

#### 1. 使用Docker Compose运行

在项目根目录下执行

使用GPU运行：
```bash
docker compose -f docker/docker-compose_gpu.yml up -d
```

使用CPU运行：
```bash
docker compose -f docker/docker-compose.yml up -d
```

访问地址：`服务器ip:80`，进入到前台界面

访问地址：`服务器ip:8888`，进入到后台管理界面

图文教程：[https://blog.csdn.net/qq1198768105/article/details/147475488](https://blog.csdn.net/qq1198768105/article/details/147475488)

#### 2. 源码运行(mysql、minio、es等组件仍需docker启动)

1. 启动后台管理系统：

- 启动后端：进入到`management/server`，执行：

```bash
python app.py
```

- 启动前端：进入到`management\web`，执行：

```bash
pnpm dev
```

2. 启动前台交互系统：

- 启动后端：项目根目录下执行：

```bash
python -m api.ragflow_server
```

- 启动前端：进入到`web`，执行：

```bash
pnpm dev
```

> [!NOTE]
> 源码部署需要注意：如果用到MinerU后台解析，需要参考MinerU的文档下载模型文件，并安装LibreOffice，配置环境变量，以适配支持除pdf之外的类型文件。


## 📝 常见问题

参见[常见问题](docs/faq.md)

## 📜 开发计划

参见[开发计划](docs/plan.md)

## 🛠️ 如何贡献

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

## 📄 交流群
如果有使用问题或建议，可加入交流群进行讨论。

由于群聊超过200人，无法通过扫码加入，如需加群，加我微信zstar1003，备注"加群"即可。

## 🚀 鸣谢

本项目基于以下开源项目开发：

- [ragflow](https://github.com/infiniflow/ragflow)

- [v3-admin-vite](https://github.com/un-pany/v3-admin-vite)

- [minerU](https://github.com/opendatalab/MinerU)

感谢此项目贡献者们：

<a href="https://github.com/zstar1003/ragflow-plus/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=zstar1003/ragflow-plus" />
</a>

## 💻 更新信息获取

目前该项目仍在持续更新中，更新日志会在我的微信公众号[我有一计]上发布，欢迎关注。

## 📜  许可证与使用限制
1. **本仓库基于AGPLv3许可证**  
   由于包含第三方AGPLv3代码，本项目必须遵循AGPLv3的全部条款。这意味着：
   - 任何**衍生作品**（包括修改或组合代码）必须继续使用AGPLv3并公开源代码。  
   - 若通过**网络服务**提供本软件，用户有权获取对应源码。

2. **商用说明**  
   - **允许商用**：本软件遵循AGPLv3，允许商业使用，包括SaaS和企业内部部署。
   - **不修改代码**：若仅原样运行（不修改、不衍生），仍需遵守AGPLv3，包括：  
     - 提供完整的源代码（即使未修改）。  
     - 若作为网络服务提供，需允许用户下载对应源码（AGPLv3第13条）。
   - **不允许闭源商用**：如需闭源（不公开修改后的代码）商用，需获得获得所有代码版权持有人的书面授权（包括上游AGPLv3代码作者）  

3. **免责声明**  
   本项目不提供任何担保，使用者需自行承担合规风险。若需法律建议，请咨询专业律师。
   
## ✨ Star History

![Stargazers over time](https://starchart.cc/zstar1003/ragflow-plus.svg)