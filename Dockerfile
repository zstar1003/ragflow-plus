# 使用 RAGFlow v0.17.2 镜像作为基础
FROM infiniflow/ragflow:v0.17.2

# 设置工作目录（与基础镜像保持一致）
WORKDIR /ragflow

# 复制 Python 相关代码目录
COPY api ./api
COPY conf ./conf
COPY deepdoc ./deepdoc
COPY rag ./rag
COPY agent ./agent
COPY graphrag ./graphrag
COPY agentic_reasoning ./agentic_reasoning

# 复制 Python 依赖定义文件
COPY pyproject.toml ./pyproject.toml
COPY uv.lock ./uv.lock

# 复制前端源代码目录
COPY web ./web

# 复制 Docker 相关文件
COPY docker/service_conf.yaml.template ./conf/service_conf.yaml.template
COPY docker/entrypoint.sh ./entrypoint.sh

RUN chmod +x ./entrypoint.sh

# 重新构建前端应用
# 因为我们覆盖了 /ragflow/web 目录，需要重新生成 /ragflow/web/dist
# 基础镜像 infiniflow/ragflow:v0.17.2 应该已经包含了 Node.js 和 npm
RUN cd web && npm install && npm run build


