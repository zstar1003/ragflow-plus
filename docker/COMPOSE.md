# Compose 引擎与依赖

使用 Docker Compose **2.20.3 或更新版本**。项目通过官方支持的
[`include`](https://docs.docker.com/compose/how-tos/multiple-compose-files/include/)
加载基础服务，CPU 和 GPU 配置都依赖它。

当前完整的 RagflowPlus 部署只支持 `DOC_ENGINE=elasticsearch`。
核心 API 保留了 Infinity 连接分支，但本仓库的 Compose 没有 Infinity 服务，
管理端也直接使用 Elasticsearch 客户端读写解析结果。仅修改环境变量不能使
管理端切换引擎，不应将配置渲染成功视为替代引擎可运行。

`es01` 是管理端必需依赖，因此不应放在可选 profile 中。
旧配置中，宿主机覆盖 `COMPOSE_PROFILES`（例如空值或无关 profile），或设置
`DOC_ENGINE=infinity`，会排除 `es01`，并产生
`depends on undefined service "es01"`。这是配置依赖检查错误，不是证明
Elasticsearch 容器已启动失败；这也不是 `include` 不被现代 Compose 支持。
不能仅根据历史 issue 报错确定报告者实际使用了哪些环境变量或 Compose 版本。

升级后的配置保留 Elasticsearch 的名称、数据卷、端口、健康检查和认证设置，
只移除其 profile 门槛。不要删除数据卷，也不要为解决此错误修改数据库密码。
如使用定制部署或外部 Elasticsearch，应另行审查服务依赖与连接设置。

配置好管理端必需的认证变量后，可以仅检查配置，不启动容器：

```bash
docker compose -f docker/docker-compose.yml config --quiet
docker compose -f docker/docker-compose_gpu.yml config --quiet
```

测试覆盖默认、空/无关 profile 和替代引擎环境值的配置渲染与依赖完整性，
不验证镜像启动、GPU 驱动、真实服务健康或替代引擎运行。
