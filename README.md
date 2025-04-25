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

## 🛠️ 如何贡献

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request


## 📄 交流群
如果有其它需求或问题建议，可加入交流群进行讨论。

由于群聊超过200人，无法通过扫码加入，如需加群，加我微信zstar1003，备注"加群"即可。

## 🚀 鸣谢

本项目基于以下开源项目开发：

- [ragflow](https://github.com/infiniflow/ragflow)

- [v3-admin-vite](https://github.com/un-pany/v3-admin-vite)

- [minerU](https://github.com/opendatalab/MinerU)

## 💻 更新信息获取

目前该项目仍在持续更新中，更新日志会在我的微信公众号[我有一计]上发布，欢迎关注。

## ✨ Star History

![Stargazers over time](https://starchart.cc/zstar1003/ragflow-plus.svg)