<div align="center">
  <img src="assets/ragflow-plus.png" width="400" alt="Ragflow-Plus">
</div>

<div align="center">
  <img src="https://img.shields.io/badge/version-0.3.0-blue" alt="Version">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL3.0-green" alt="License"></a>
  <h4>
    <a href="README.md">🇨🇳 Chinese</a>
    <span> | </span>
    <a href="README_EN.md">🇬🇧 English</a>
  </h4>
</div>

---

## 🌟 Introduction

**Ragflow-Plus** is a secondary development project based on **Ragflow**, aiming to address practical application issues with the following features:

- **Management Mode**  
  An additional backend management system is provided for user, team, config, file, and knowledge base management.

- **Permission Restriction**  
  The frontend interface is simplified by reducing user access permissions.

- **Enhanced Parsing**  
  Replaces the DeepDoc algorithm with **MinerU** for improved file parsing and support for image analysis.

- **Image & Text Output**  
  Supports linking reference images to answer text blocks during responses.

- **Document Writing Mode**  
  Offers a brand-new interactive document editing experience.

🎬 **Demo Video & Tutorial:**

[![Ragflow-Plus Project Overview & Guide](https://i0.hdslb.com/bfs/archive/f7d8da4a112431af523bfb64043fe81da7dad8ee.jpg@672w_378h_1c.avif)](https://www.bilibili.com/video/BV1UJLezaEEE)

## 📥 How to Use

### 1. Run with Docker Compose

Run from the root directory:

**Using GPU:**
```bash
docker compose -f docker/docker-compose_gpu.yml up -d
```

**Using CPU::**

```bash
docker compose -f docker/docker-compose.yml up -d
```
Access the frontend UI at: `your-server-ip:80`  
Access the admin dashboard at: `your-server-ip:8888`  

📘 Step-by-step tutorial: [https://blog.csdn.net/qq1198768105/article/details/147475488](https://blog.csdn.net/qq1198768105/article/details/147475488)

#### 2. Run from Source Code (Docker is still required for MySQL, MinIO, Elasticsearch, etc.)

1. Start the Admin System:

- **Start the backend**: Navigate to `management/server` and run:
```bash
python app.py
```

- **Start the frontend**: Navigate to `management/web` and run:
```bash
pnpm dev
```

2. Start the Frontend Interaction System:
- **Start the backend**: From the project root directory, run:
```bash
python -m api.ragflow_server
```

- **Start the frontend**: Navigate to `web` and run:
```bash
pnpm dev
```

## 🛠️ How to Contribute

1. Fork this repository  
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)  
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)  
4. Push to the branch (`git push origin feature/AmazingFeature`)  
5. Open a Pull Request  

## 📄 Community Group

If you have additional needs, suggestions, or questions, feel free to join our community group for discussion.

⚠️ Note: Since the group has over 200 members, QR code join is disabled. To join, please add me on WeChat (ID: **zstar1003**) and include the note "Join Group".

## 🚀 Acknowledgments

This project is developed based on the following open-source projects:

- [ragflow](https://github.com/infiniflow/ragflow)  
- [v3-admin-vite](https://github.com/un-pany/v3-admin-vite)  
- [minerU](https://github.com/opendatalab/MinerU)

## 💻 Stay Updated

This project is under continuous development. Update logs will be posted on my WeChat public account **[我有一计]** — feel free to follow!

## 📜 License and Usage Restrictions

1. **This Repository is Licensed Under AGPLv3**  
   As it incorporates third-party AGPLv3 code, this project must fully comply with AGPLv3 terms. This means:
   - Any **derivative works** (including modifications or combined code) must remain under AGPLv3 with source code publicly available.  
   - If provided as a **network service**, users are entitled to obtain the corresponding source code.

2. **Commercial Use**  
   - **Allowed**: This software is licensed under AGPLv3, permitting commercial use, including SaaS and on-premises deployment.  
   - **Unmodified Code**: If used *as-is* (no modifications/derivative works), AGPLv3 compliance remains mandatory:  
     - Provide complete source code (even if unaltered).  
     - For network services, users must be able to download corresponding source code (AGPLv3 §13).  
   - **No Closed-Source Commercialization**: To use modified versions *without* releasing source code commercially, written authorization from *all copyright holders* (including upstream AGPLv3 authors) is required.  

3. **Disclaimer**  
   This project comes with no warranties. Users shall bear all compliance risks. Consult legal professionals for legal advice.

## ✨ Star History

![Stargazers over time](https://starchart.cc/zstar1003/ragflow-plus.svg)