# 前端构建阶段
FROM node:18 AS frontend-builder
WORKDIR /app/frontend

# 先复制依赖配置，利用 Docker 缓存机制
COPY web/package.json web/pnpm-lock.yaml ./

# 安装 pnpm（固定版本以避免兼容性问题）
RUN npm install -g pnpm@8
# 设置环境变量禁用交互式提示
ENV CI=true
# 安装依赖（这时 node_modules 会在容器里生成，而不是从宿主机复制）
RUN pnpm install

# 再复制其余源码（避免把宿主机的 node_modules 带进来）
COPY web .

# 构建产物
RUN pnpm build && chmod -R 755 dist

# 前端服务阶段
FROM nginx:alpine AS frontend
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html
# 暴露前端端口
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# 后端构建阶段
FROM python:3.10.16 AS backend
# 安装 LibreOffice 及字体支持
RUN apt-get update && \
    apt-get install -y libreoffice fonts-noto-cjk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY server/requirements.txt /app/
# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 复制后端代码
COPY server /app

# 创建 huggingface 缓存目录并复制模型
RUN mkdir -p /root/.cache/huggingface/hub/
COPY models--opendatalab--PDF-Extract-Kit-1.0 /root/.cache/huggingface/hub/models--opendatalab--PDF-Extract-Kit-1.0
COPY models--hantian--layoutreader /root/.cache/huggingface/hub/models--hantian--layoutreader
# COPY magic-pdf.json /root/magic-pdf.json

# 暴露后端端口
EXPOSE 5000
CMD ["python", "app.py"]