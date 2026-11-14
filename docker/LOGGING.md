# Docker 容器日志轮转

CPU、GPU 和公共依赖 Compose 文件为所有启用的服务显式配置
`json-file` 日志驱动，每个日志文件 `10m`，最多保留 `5` 个文件。
这些限制针对 Docker 收集的 stdout/stderr，不是整个容器或磁盘配额；
旧日志会随轮转淘汰，需要长期审计日志时请先接入日志归档。

应用写入 `ragflow-logs`、`ragflow-plus-logs` 等挂载目录的文件日志，
以及数据库数据，不受此配置限制，应分别检查其大小和保留策略。
此改动是防止未设置上限的 Docker 日志持续增长，不代表已确认历史
[问题 #251](https://github.com/zstar1003/ragflow-plus/issues/251) 的具体磁盘占用来源。

## 更新已有部署

1. 确认使用的 Compose 文件、现有日志驱动及日志归档要求。该配置会覆盖
   Docker daemon 的默认日志驱动。如果当前使用集中式日志驱动，请保留自己的
   服务级 logging 配置，不要直接切换；同时移除不适用于该驱动的 json-file 选项。
2. 配好现有 `.env` 后，先运行 `docker compose -f docker-compose.yml config --quiet`
   校验。GPU 部署使用 `docker-compose_gpu.yml`。
3. 在维护窗口按正常升级流程重新创建容器，使新日志配置生效。
   单纯 restart 不会更新现有容器的日志配置；重建可能中断服务并删除旧容器日志，
   如需留存请先导出。不要删除数据卷，不要直接编辑或截断 Docker 管理的日志文件。
4. 重建后检查实际设置，例如：

   ```sh
   docker inspect --format '{{json .HostConfig.LogConfig}}' ragflowplus-server
   ```

   应包含 `Type: json-file` 和 `max-size: 10m`、`max-file: 5`。
   也应检查其他服务，尤其是已存在的数据库容器。

如需修改保留量，调整所用 Compose 文件中 `x-logging.options` 的两个
字符串值；公共依赖服务位于 `docker-compose-base.yml`。
YAML 锚点仅在各自文件内有效。

参考：[Docker JSON File logging driver](https://docs.docker.com/engine/logging/drivers/json-file/)、
[Configure logging drivers](https://docs.docker.com/engine/logging/configure/)。

## 配置回归检查

从仓库根目录运行（需要 PyYAML）：

```sh
python -m unittest discover -s docker/tests -p 'test_*.py'
```
