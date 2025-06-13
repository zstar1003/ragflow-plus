# Docker镜像构建

本节介绍如何构建镜像，并在离线情况下实现镜像的导出和加载。

## 1. 构建镜像

构建前台镜像：

```bash
docker build -t zstar1003/ragflowplus:v0.4.3 .
```

构建后台镜像：

构建后台镜像前，需先将模型文件放置到`management`文件夹中。

下载地址：https://pan.baidu.com/s/1aUV7ohieL9byrbbmjfu3pg?pwd=8888 提取码: 8888 

```bash
cd management
docker-compose build
```


## 2. 上传镜像

上传镜像到公共仓库，可供他人进行下载：

上传前台镜像：

```bash
docker tag zstar1003/ragflowplus:v0.4.3 zstar1003/ragflowplus:v0.4.3
docker push zstar1003/ragflowplus:v0.4.3
```

上传后台镜像：
```bash
docker tag zstar1003/ragflowplus-management-web:v0.4.3 zstar1003/ragflowplus-management-web:v0.4.3
docker tag zstar1003/ragflowplus-management-server:v0.4.3 zstar1003/ragflowplus-management-server:v0.4.3
docker push zstar1003/ragflowplus-management-web:v0.4.3
docker push zstar1003/ragflowplus-management-server:v0.4.3
```

## 3. 导出镜像

导出所有镜像文件，可实现离线情况下的镜像迁移安装。

```bash
docker save -o ragflowplus-images.tar zstar1003/ragflowplus-management-web:v0.4.3 zstar1003/ragflowplus-management-server:v0.4.3 zstar1003/ragflowplus:v0.4.3 valkey/valkey:8 quay.io/minio/minio:RELEASE.2023-12-20T01-00-02Z mysql:8.0.39 elasticsearch:8.11.3
```

## 4. 离线安装镜像

在离线服务器中，安装镜像

```bash
docker load -i ragflowplus-images.tar
```