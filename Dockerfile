# 使用 RAGFlow v0.17.2-slim 镜像作为基础
FROM infiniflow/ragflow:v0.17.2-slim

# 设置工作目录（与基础镜像保持一致）
WORKDIR /ragflow

# 复制 Python 相关代码目录
COPY api ./api
COPY conf ./conf
COPY rag ./rag
COPY graphrag ./graphrag
COPY agentic_reasoning ./agentic_reasoning

# 安装额外依赖
RUN uv pip install --no-cache-dir mysql-connector-python==9.2.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN uv pip install --no-cache-dir redis==6.2.0 -i https://pypi.tuna.tsinghua.edu.cn/simple


# 复制前端源代码目录
COPY web ./web

# 复制 Docker 相关文件
COPY docker/service_conf.yaml.template ./conf/service_conf.yaml.template
COPY docker/entrypoint.sh ./entrypoint.sh

RUN chmod +x ./entrypoint.sh

# 重新构建前端应用
RUN cd web && npm install && npm run build