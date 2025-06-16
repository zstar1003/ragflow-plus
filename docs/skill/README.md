# 进阶技巧

此模块用来介绍一些进阶使用技巧，适合有一定经验的开发者。

## 1. gpu加速

本项目提供了gpu部署的方案，可通过独立显卡，大大加速文档解析速度，预留空余显存需 > 6GB。

docker启动：

```bash
docker compose -f docker/docker-compose_gpu.yml up -d
```

若启动失败，可通过以下方式增加docker对gpu加速的支持。

```bash
# 575为具体版本号，可根据具体gpu型号选择合适的版本
sudo apt install nvidia-cuda-toolkit
sudo apt install nvidia-container-toolkit
sudo apt install nvidia-fabricmanager-575
sudo apt install libnvidia-nscq-575
sudo apt install nvidia-container-runtime
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

### 2. 前台环境启动

后端安装依赖

```bash
pip install -r requirements.txt
```

启动后端
```bash
python -m python -m api.ragflow_server
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
python -m api.ragflow_server
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
MANAGEMENT_ADMIN_PASSWORD=12345678
```

修改后重启容器。

## 4. 修改图像访问ip地址

服务器部署，minio访问地址可修改为服务器ip，以实现图片在用户端的正常访问。

可修改`docker\.env`文件中，以下参数：
```bash
# 显示minio文件时的ip地址，如需局域网/公网访问，可修改为局域网/公网ip地址
MINIO_VISIT_HOST=localhost
```

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