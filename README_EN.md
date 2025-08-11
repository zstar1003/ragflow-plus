<div align="center">
  <img src="docs/images/ragflow-plus.png" width="400" alt="Ragflow-Plus">
</div>

<div align="center">
  <a href="https://github.com/zstar1003/ragflow-plus/stargazers"><img src="https://img.shields.io/github/stars/zstar1003/ragflow-plus?style=social" alt="stars"></a>
  <img src="https://img.shields.io/badge/version-0.5.0-blue" alt="version">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL3.0-green" alt="license"></a>
  <a href="https://hub.docker.com/r/zstar1003/ragflowplus/tags"><img src="https://img.shields.io/docker/pulls/zstar1003/ragflowplus" alt="docker pulls"></a>

  <h4>
    <a href="README.md">🇨🇳 Chinese</a>
    <span> | </span>
    <a href="README_EN.md">🇬🇧 English</a>
  </h4>
</div>

---

## 🌟 Introduction

**Ragflow-Plus** is a secondary development project based on **Ragflow**, aiming to solve some issues in real-world applications.  
Key features include:

- **Management Mode**  
  An additional admin panel to support user management, team management, configuration management, file management, and knowledge base management.
- **Permission Reclaiming**  
  The frontend system limits user permissions for a simplified interface.
- **Enhanced Parsing**  
  Replaces the DeepDoc algorithm with MinerU for better document parsing results, including image parsing.
- **Text-Image Output**  
  Supports displaying related images linked to referenced text blocks in model responses.
- **Document Writing Mode**  
  Offers a brand new document-mode interactive experience.

**In short:** Ragflow-Plus is the “industry-specific solution” of Ragflow for Chinese application scenarios.

## 📥 Usage

Video demo & tutorial:  

[![Ragflow-Plus Introduction and User Guide](https://i0.hdslb.com/bfs/archive/f7d8da4a112431af523bfb64043fe81da7dad8ee.jpg@672w_378h_1c.avif)](https://www.bilibili.com/video/BV1UJLezaEEE)

Project documentation: [xdxsb.top/ragflow-plus](https://xdxsb.top/ragflow-plus)

Quick start with Docker:
```bash
docker compose -f docker/docker-compose.yml up -d
````

## ❓ FAQ

* For common issues, check [FAQ](docs/question/README.md) or search the GitHub issues section.
* If not resolved, try using [DeepWiki](https://deepwiki.com/zstar1003/ragflow-plus) or [zread](https://zread.ai/zstar1003/ragflow-plus) to interact with the AI assistant, which can solve most common problems.
* If the problem persists, submit a GitHub issue — the AI assistant will respond automatically.

## 🛠️ How to Contribute

1. **Fork** this GitHub repository
2. Clone your fork locally:

   ```bash
   git clone git@github.com:<your-username>/ragflow-plus.git
   ```
3. Create a new branch:

   ```bash
   git checkout -b my-branch
   ```
4. Commit with a descriptive message:

   ```bash
   git commit -m 'Provide a clear and descriptive commit message'
   ```
5. Push changes to GitHub:

   ```bash
   git push origin my-branch
   ```
6. Submit a PR and wait for review.

## 🚀 Acknowledgements

This project is based on the following open-source projects:

* [ragflow](https://github.com/infiniflow/ragflow)
* [v3-admin-vite](https://github.com/un-pany/v3-admin-vite)
* [minerU](https://github.com/opendatalab/MinerU)

Thanks to all contributors:

<a href="https://github.com/zstar1003/ragflow-plus/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=zstar1003/ragflow-plus" />
</a>

## 📜 License & Usage Restrictions

1. **AGPLv3 License**
   Since the project contains third-party AGPLv3 code, it must comply with all AGPLv3 terms:

   * Any **derivative works** (including modifications or combined code) must remain AGPLv3 licensed and open-sourced.
   * If provided via **network services**, users have the right to obtain the corresponding source code.

2. **Commercial Use**

   * **Allowed**: AGPLv3 permits commercial use, including SaaS and enterprise deployments.
   * **Unmodified Code**: Even without modifications, you must still comply with AGPLv3:

     * Provide the complete source code (even if unchanged).
     * If offered as a network service, allow users to download the source code (AGPLv3 Section 13).
   * **No Closed-Source Commercial Use**: Closed-source commercial use (not releasing modified code) requires written permission from all copyright holders, including upstream AGPLv3 authors.

3. **Disclaimer**
   This project is provided without warranties. Users are responsible for compliance. For legal advice, consult a professional lawyer.

## ✨ Star History

![Stargazers over time](https://starchart.cc/zstar1003/ragflow-plus.svg)