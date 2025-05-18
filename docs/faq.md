# 常见问题 (FAQ)

## 问题 1：如何部署 RagflowPlus？

**回答：** 您可以通过 Docker Compose 或源码进行部署。

- **Docker Compose (推荐):**
  - GPU 版本: `docker compose -f docker/docker-compose_gpu.yml up -d`
  - CPU 版本: `docker compose -f docker/docker-compose.yml up -d`
- **源码运行:** 请参考“快速开始”部分。

注：对于后台MinerU解析，默认仍采用CPU，如需更换为GPU版本，需保证预留显存在8GB以上，并在 `docker/magic-pdf.json` 文件中修改 `device-mode` 为 `cuda`。

## 问题 2：RagflowPlus 能和 Ragflow 同时使用吗？

**回答：** RagflowPlus 采用了独立的前后台系统，数据和 Ragflow 互通，但不建议和 Ragflow 同时使用。如需同时使用，可通过修改端口/切换启动方式来实现，但需承担部分接口不一致导致的风险。

## 问题 3：后台解析时报错：存储桶不存在:f62a03f61fdd11f0b1301a12a4193bf3。

**回答：** 此问题是由于解析的文件是由 Ragflow 原本的文件系统上传的，RagflowPlus 重构了文件上传的相关接口，因此解析新文件时，建议通过 RagflowPlus 的后台管理系统进行上传。

## 问题 4：支持解析的文档类型？

**回答：** 常见的文档类型均可支持，包括：pdf、word、ppt、excel、txt、md、html、jpg、png、bmp。

## 问题 5：embedding模型的向量维度非1024，导致后台解析出错。

**回答：** 建议使用`bge-m3`模型进行解析，该模型的向量维度为1024。解析模型不建议频繁更换，否则容易影响检索匹配。

## 问题 6：docker镜像支持arm平台吗？

**回答：** 鉴于 Ragflow 也不维护arm平台的镜像，RagflowPlus 也无计划推出和维护arm平台的镜像。

## 问题 7：可以用ollama部署模型吗？

**回答：** 可以，兼容ollama及在线api(硅基流动平台)。

--- 

# 以下是v0.3.0版本已知存在的问题：

## 问题 1：文件管理菜单中，添加文件，文件的上传时间晚8个小时。

**回答：** 时区问题，之后会修复。

## 问题 2：设置为gpu解析时，提示缺少模型文件：paddleocr_torch/ch_PP-OCRv4_rec_server_doc_infer.pth is not existed。

**回答：** 本地跑一下mineru的gpu解析，把相应的模型文件拷贝进容器即可。

*如有更多问题，欢迎在 GitHub 上提交 Issue。*