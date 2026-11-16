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

## 5. 更换 title 和 logo

前台聊天页面与后台管理页面是两套独立前端。不要只修改后台图片来替换聊天页面的品牌，也不要直接删除运行中容器的静态文件目录。容器内手工修改还会在重建时丢失。

### 1. 确认要修改的资源

以下路径相对于仓库根目录，按当前源码核对；旧镜像或其他分支可能不同。

| 页面/元素 | 修改位置 | 代码依据 |
| --- | --- | --- |
| 前台聊天页左上角 logo | `web/public/logo.svg` | `web/src/layouts/components/header/index.tsx` 使用 `/logo.svg`；新版 header 也引用同一文件 |
| 前台聊天页左上角名称 | `web/src/conf.json` 的 `appName` | 同一 header 读取 `appConf.appName` |
| 前台浏览器标签标题、图标 | `appName`、`web/public/logo.svg` | `web/.umirc.ts` 的 `title`、`favicons` |
| 前台登录页文案 | `web/src/locales/zh.ts` 的 `login.title` | `web/src/pages/login/right-panel.tsx`；其他语言需修改对应 locale，勿批量替换所有 `title` |
| 后台折叠 logo、展开 logo | `management/web/src/common/assets/images/layouts/logo.png`、`logo-text-1.png`、`logo-text-2.png` | `management/web/src/layouts/components/Logo/index.vue` 根据布局选图 |
| 后台登录页 logo | 同目录 `logo-text-2.png` | `management/web/src/pages/login/index.vue` |
| 后台浏览器标题 | `management/web/.env` 的 `VITE_APP_TITLE` | `management/web/src/common/composables/useTitle.ts`；这是构建时变量，修改容器环境并重启不会重编译 |
| 后台页脚 | `management/web/src/layouts/components/Footer/index.vue` | 按需修改页脚内容 |

SVG 需保持有效格式；如果改用 PNG 等格式，必须同步修改引用路径。资源文件和名称是分开的，修改其中一个不会自动替换另一个。

### 2. 构建并保留独立版本

在与部署版本兼容的源码上修改，并安装项目依赖。从仓库根目录执行，只构建需要更新的前端：

```bash
(cd web && pnpm install --frozen-lockfile && pnpm run build)
(cd management/web && pnpm install --frozen-lockfile && pnpm run build)
```

构建失败时停止，不发布旧 `dist`。检查本次输出的 `dist/index.html`、JS/CSS 和品牌图片均存在，再复制到服务器上一个**全新、独立、绝对路径**的发布目录，例如 `/srv/ragflow-brand/20261116-01/web` 和 `/srv/ragflow-brand/20261116-01/management`。这些目录直接包含 `index.html`，不要多套一层 `dist`。保留旧版本，不在已挂载的发布目录上覆盖构建。

### 3. 用只读挂载发布，保留原文件用于回滚

以下仅适用于仓库 `docker/docker-compose.yml` 的默认目录和服务名。先在测试环境验证；若现有部署有额外 Compose 文件、不同 project name、GPU 配置、定制 Nginx 或同目标挂载，必须沿用原启动参数并调整示例，不可直接套用。

先记录当前服务镜像 ID、原 Compose 文件列表与 project name，并备份原配置（含 `.env`，安全存放，不提交仓库）。不要拉取新镜像、不要删除容器目录、不要执行 `down -v`。此方案只覆盖静态文件，不更新后端或数据库。

在服务器保存 `compose.brand.yml`，把 `source` 改成实际发布目录；只保留需要更新的服务：

```yaml
services:
  ragflow:
    volumes:
      - type: bind
        source: /srv/ragflow-brand/20261116-01/web
        target: /ragflow/web/dist
        read_only: true
        bind:
          create_host_path: false
  management-frontend:
    volumes:
      - type: bind
        source: /srv/ragflow-brand/20261116-01/management
        target: /usr/share/nginx/html
        read_only: true
        bind:
          create_host_path: false
```

`create_host_path: false` 防止路径拼错时自动创建空目录，但仍需手动检查 `index.html` 非空、文件权限允许容器读取。上述目标分别来自 `docker/nginx/ragflow.conf` 和 `docker/nginx/management_nginx.conf`。SELinux、不同容器用户或旧版 Compose 可能需要额外适配，不要为此关闭安全策略。

在仓库根目录，使用原部署相同的 Compose project name/环境和文件顺序，最后追加 override。默认部署示例：

```bash
test -s /srv/ragflow-brand/20261116-01/web/index.html
test -s /srv/ragflow-brand/20261116-01/management/index.html
docker compose -f docker/docker-compose.yml -f /absolute/path/compose.brand.yml config --quiet
# 以下会重建服务，有短暂中断；ragflow 同时承载后端，须安排维护窗口。
docker compose -f docker/docker-compose.yml -f /absolute/path/compose.brand.yml up -d --no-deps --pull never ragflow management-frontend
```

只更新一个前端时，从 override、检查命令和 `up` 服务列表中去掉另一个。不要修改原镜像标签，确保原镜像仍在本机；`--pull never` 不保证可变标签没有在本机被其他操作更新，因此部署前须核对镜像 ID。

验收：检查服务日志，访问前台和后台首页、登录页、聊天页，检查 logo/名称、JS/CSS 请求无 404，验证登录及 API 正常。用无痕窗口或清除缓存复查，不以首页 HTTP 200 作为唯一成功依据。发布后所有重建命令须继续带上此 override，否则会恢复镜像内资源。

### 4. 回滚

失败时使用**记录下来的原 Compose 文件列表和 project name，不带本次 branding override**，确认原镜像 ID 未改变，再重建本次变更的服务。例如默认部署：

```bash
docker compose -f docker/docker-compose.yml up -d --no-deps --pull never --force-recreate ragflow management-frontend
```

只变更一个服务时只回滚该服务。撤销只读挂载后会恢复原镜像中的静态文件；若之前已经有品牌 override，回滚应恢复上一版 override，而不是全部去掉。重做上述页面/API 验收并清除缓存。不要删除发布目录或旧镜像，直到确认无需回退。

**验证边界：**本文已按源码核对资源引用、Nginx 目录及 Compose 服务名；发布/回滚示例未在实际 Docker、GPU、SELinux 或生产环境执行，不能保证无停机。执行前须在与生产一致的测试环境验证。本次文档修订不会修改任何运行中的部署。
