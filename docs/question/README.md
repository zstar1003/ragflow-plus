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

## 问题 8：端口冲突报错如何解决？

```bash
(HTTP code 500) server error - Ports are not available: exposing port TCP 0.0.0.0:5455 -> 0.0.0.0:0: listen tcp 0.0.0.0:5455: bind: An attempt was made to access a socket in a way forbidden by its access permissions.s
```

**回答：** 该问题原因是 Windows 网络地址转换服务（WinNAT），该服务为 Hyper-V、WSL2 或 Docker 等虚拟化技术提供网络地址转换(NAT)功能 。WinNAT 在运行时会随机保留一部分 TCP/UDP 端口供虚拟网络使用。这些保留端口可能与应用所需端口冲突。

通过以下命令，可以停止服务，释放这些保留端口，允许用户临时使用它们。
```bash
net stop winnat
netsh int ipv4 add excludedportrange protocol=tcp startport=5455 numberofports=1
net start winnat
```

## 问题 9：MinerU GPU 加速似乎只调用了第一张显卡，如何指定其它显卡？

**回答：** MinerU 1.x 本身无法指定具体所用显卡，且不支持多显卡部署，可通过以下方式去限定后端容器所能利用的显卡id。

修改`docker\docker-compose_gpu.yml`：

```bash
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          capabilities: [gpu]
          device_ids: ["2"]  # 使用索引号指定id为2的显卡
```

## 问题 10：日志出现警告：RedisDB.queue_info rag_flow_svr_queue got exception:no such key

**回答：** Ragflow原生解析器心跳触发的问题，不影响正常使用，可忽略，官方回答可参考：https://github.com/infiniflow/ragflow/issues/6700

--- 



*如有更多问题，欢迎在 GitHub 上提交 Issue。*