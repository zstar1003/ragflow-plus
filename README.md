<div align="center">
  <img src="docs/images/ragflow-plus.png" width="400" alt="Ragflow-Plus">
</div>

<div align="center">
  <a href="https://github.com/zstar1003/ragflow-plus/stargazers"><img src="https://img.shields.io/github/stars/zstar1003/ragflow-plus?style=social" alt="stars"></a>
  <img src="https://img.shields.io/badge/版本-0.5.0-blue" alt="版本">
  <a href="LICENSE"><img src="https://img.shields.io/badge/许可证-AGPL3.0-green" alt="许可证"></a>
  <a href="https://hub.docker.com/r/zstar1003/ragflowplus/tags"><img src="https://img.shields.io/docker/pulls/zstar1003/ragflowplus" alt="docker pulls"></a>

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

一句话总结：RagflowPlus 是 Ragflow 在中文应用场景下的“行业特解”。

## 📥使用方式

视频演示及操作教程：

[![Ragflow-Plus项目简介与操作指南](https://i0.hdslb.com/bfs/archive/f7d8da4a112431af523bfb64043fe81da7dad8ee.jpg@672w_378h_1c.avif)](https://www.bilibili.com/video/BV1UJLezaEEE)

项目文档：[xdxsb.top/ragflow-plus](https://xdxsb.top/ragflow-plus)

使用 Docker 快速启动：
```bash
docker compose -f docker/docker-compose.yml up -d
```

## ❓ 问题解答

- 如果在使用过程中遇到问题，可以先查看[常见问题](docs/question/README.md)或仓库issue是否有解答。
- 如果未能解决您的问题，也可以使用[DeepWiki](https://deepwiki.com/zstar1003/ragflow-plus)或[zread](https://zread.ai/zstar1003/ragflow-plus)与AI助手交流，这可以解决大部分常见问题。
- 如果仍然无法解决问题，可以提交仓库issue，会有AI助手自动进行问题解答。

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


## 🚀 鸣谢

本项目基于以下开源项目开发：

- [ragflow](https://github.com/infiniflow/ragflow)

- [v3-admin-vite](https://github.com/un-pany/v3-admin-vite)

- [minerU](https://github.com/opendatalab/MinerU)

感谢此项目贡献者们：

<a href="https://github.com/zstar1003/ragflow-plus/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=zstar1003/ragflow-plus" />
</a>


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
   - **不允许闭源商用**：如需闭源（不公开修改后的代码）商用，需获得所有代码版权持有人的书面授权（包括上游AGPLv3代码作者）  

3. **免责声明**  
   本项目不提供任何担保，使用者需自行承担合规风险。若需法律建议，请咨询专业律师。
   
## ✨ Star History

![Stargazers over time](https://starchart.cc/zstar1003/ragflow-plus.svg)