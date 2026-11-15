# 进阶技巧

此模块用来介绍一些进阶使用技巧，适合有一定经验的开发者。

## 1. gpu加速

本项目提供了gpu部署的方案，可通过独立显卡，大大加速文档解析速度，预留空余显存需 > 6GB。

docker启动：

```bash
docker compose -f docker/docker-compose_gpu.yml up -d
```

若启动后，发现容器找不到显卡信息，则需要再单独安装nvidia-container-runtime：

```bash
sudo apt install nvidia-container-runtime
```

若上述未能解决，可考虑使用以下备用方案：

```bash
# 575为具体版本号，可根据具体gpu型号选择合适的版本
sudo apt install nvidia-cuda-toolkit
sudo apt install nvidia-container-toolkit
sudo apt install nvidia-fabricmanager-575
sudo apt install libnvidia-nscq-575
sudo systemctl start nvidia-fabricmanager
sudo systemctl enable nvidia-fabricmanager
sudo systemctl status nvidia-fabricmanager
```

## 2. 源码启动

除docker外，本项目支持采用源码的方式启动前后端。

### 1. 启动中间件

使用docker启动中间件：

```bash
docker start ragflow-es-01
docker start ragflow-mysql
docker start ragflow-minio
docker start ragflow-redis
```

同时，修改`docker\.env`的`MINIO_HOST`为 `localhost`。

### 2. 前台环境启动

后端安装依赖

```bash
pip install -r requirements.txt
```

启动后端
```bash
python -m api.ragflow_server
```

前端安装依赖

```bash
cd web
pnpm i
```

启动前端

```bash
pnpm dev
```

### 3. 后台环境启动

后端安装依赖

```bash
cd management/server
pip install -r requirements.txt
```

启动后端
```bash
python app.py
```

前端安装依赖

```bash
cd management/web
pnpm i
```

启动前端

```bash
pnpm dev
```

> [!NOTE]
> 源码部署需要注意：如果用MinerU后台解析，需要参考MinerU的文档下载模型文件，并安装LibreOffice，配置环境变量，以适配支持除pdf之外的类型文件。

## 3. 修改后台系统管理员账号密码

可通过修改`docker\.env`文件中，以下两个参数：
```bash
# 管理系统用户名和密码
MANAGEMENT_ADMIN_USERNAME=admin
# 必须设置为独有的至少 12 个字符的密码；此处故意留空，空值无法启动
MANAGEMENT_ADMIN_PASSWORD=
```

密码必须为非默认、非占位值；支持长口令，不要求特定字符组合。参见 [管理后台认证配置与升级说明](../security/jwt-secret.md)。修改后重新创建后台容器以应用新环境变量。仅修改密码不会使已签发的登录令牌失效；如需注销已有会话，同时更换 JWT 密钥。

## 4. 修改图像访问ip地址

服务器部署，minio访问地址可修改为服务器ip，以实现图片在用户端的正常访问。

可修改`docker\.env`文件中，以下参数：
```bash
# 显示minio文件时的ip地址，如需局域网/公网访问，可修改为局域网/公网ip地址
MINIO_VISIT_HOST=localhost
```

### MinIO HTTPS 域名或反向代理

`MINIO_VISIT_HOST` 控制浏览器访问的公开地址，不改变容器内 MinIO 连接、TLS 或端口发布：

- `localhost` / IP / 裸域名：兼容原配置，使用 `http://` 和 `MINIO_PORT`（默认 9000）。
- `https://images.example.com`：完整 URL 原样使用协议和标准端口，不追加 `:9000`。
- `https://images.example.com:9443/storage`：保留显式端口和代理路径前缀。

例如，TLS 在反向代理终止时，配置 `MINIO_VISIT_HOST=https://images.example.com`；容器仍可通过原有内部 HTTP 地址访问 MinIO。代理须由部署者配置，本改动不会部署证书或修改端口。配置中不要包含用户名、密码、查询参数或片段。

此设置统一用于公开 endpoint、聊天/撰写回复及新上传/解析图片。已有数据库或聊天记录里的绝对 URL 不会自动迁移。旧配置若写了 `http://host` 并依赖自动补端口，请明确改成 `http://host:9000`。需要重新构建并更新 RAGFlow 和管理后端镜像；仅更新宿主机源码或重启旧预构建镜像不会应用修复。

## 5. 更换title和logo

### 1. 后台系统修改logo和title

1.修改logo

logo文件在`management\web\src\common\assets\images\layouts`路径下，对应三个.png文件，分别是主页logo和登陆页logo(不同主题显示)

2.修改title

title在`management\web\.env`中，修改`VITE_APP_TITLE`参数

3.去除水印

管理系统主页，如需去除项目水印，可修改`management\web\src\layouts\components\Footer\index.vue`文件。

4.打包dist文件

进入到`management/web`路径，打包dist文件：

```c
cd management/web
pnpm run build
```

5.进入到容器，删除容器中已有的`/usr/share/nginx/html`文件
```c
docker exec -it ragflowplus-management-frontend /bin/sh
rm -rf /usr/share/nginx/html
```

6.将打包好的`dist`文件拷贝到容器中
```c
docker cp dist ragflowplus-management-frontend:/usr/share/nginx/html
```

### 前台系统修改logo和title

1.修改logo

logo文件在`web\public`路径下，logo文件格式为svg，如果是其它文件格式，需要对应转换。

2.修改title

title在`web\src\conf.json`中，修改`appName`参数

3.修改登录页title

如需修改登陆页title，可修改`web\src\locales\zh.ts`文件的`title`参数。

4.打包dist文件

进入到`web`路径，打包dist文件：

```c
cd web
pnpm run build
```

5.进入到容器，删除容器中已有的`/ragflow/web/dist`文件
```c
docker exec -it ragflowplus-server /bin/sh
rm -rf /ragflow/web/dist
```

6.将打包好的`dist`文件拷贝到容器中
```c
docker cp dist ragflowplus-server:/ragflow/web/
```

修改完，在浏览器中需要清除缓存，再刷新以查看效果。