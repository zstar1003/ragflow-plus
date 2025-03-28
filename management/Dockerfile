# 前端构建阶段
FROM node:18 AS frontend-builder
WORKDIR /app/frontend
COPY web /app/frontend
# 安装 pnpm
RUN npm install -g pnpm
# 设置环境变量禁用交互式提示
ENV CI=true
# 安装依赖并构建
RUN pnpm i && pnpm build

# 前端服务阶段
FROM nginx:alpine AS frontend
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html
# 暴露前端端口
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# 后端构建阶段
FROM python:3.10.16 AS backend
WORKDIR /app
COPY server/requirements.txt /app/
# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 复制后端代码
COPY server /app
# 暴露后端端口
EXPOSE 5000
CMD ["python", "app.py"]