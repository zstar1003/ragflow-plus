# Ragflow-Plus

## 项目介绍

Ragflow-Plus 是一个基于 Ragflow 的开源项目，主旨是在不影响 Ragflow 原有功能的基础上，提供一些新的功能，以解决实际应用中的一些痛点。

## 新增功能介绍

### 一. 用户后台管理系统

移除原登陆页用户注册的通道，搭建用户后台管理系统，可对用户进行管理，包括用户管理、团队管理、用户模型配置管理等功能。

### 二. 文档撰写功能
新增文档撰写全新的交互方式，支持直接导出为 Word 文档

## 使用方式

#### 1. 使用Docker Compose运行

和运行 ragflow 原始项目一样，项目根目录下执行

```bash
docker compose -f docker/docker-compose.yml up -d
```
访问地址：`服务器ip:80`，进入到ragflow原始界面

访问地址：`服务器ip:8888`，进入到管理界面


#### 2. 源码运行

也可以通过下面的方式单独运行管理系统

启动后端：

1.打开后端程序`management/server`，安装依赖

```bash
pip install -r requirements.txt
```

2.启动后端

```bash
python app.py
```

启动前端：

1.打开前端程序`management\web`，安装依赖
```bash
pnpm i
```

2.启动前端程序
```bash
pnpm dev
```

浏览器访问启动后的地址，即可进入系统。

<div align="center">
  <img src="assets/management.png"  alt="用户后台管理系统">
</div>


#### 3. 前端文件替换(可选)

ragflow-plus 还对原有的前端文件进行了若干优化，包含新增加的文档撰写功能，如需体验，可通过以下步骤替换原文件：

1. 克隆项目
```bash
git clone https://github.com/zstar1003/ragflow-plus.git
```

2. 打包web文件
```bash
cd web
pnpm run build
```

3. 进入到容器，删除容器中已有的/ragflow/web/dist文件
```bash
docker exec -it ragflow-server /bin/sh
rm -rf /ragflow/web/dist
```

4. 将打包好的web文件拷贝到容器中
```bash
docker cp dist ragflow-server:/ragflow/web/
```



## Agent功能恢复

由于在我的应用场景中，不需要Agent功能，故隐藏了Agent按钮的入口，如需恢复Agent功能，可修改`web\src\layouts\components\header\index.tsx`，对以下内容取消注释：

```tsx
{ path: '/flow', name: t('flow'), icon: GraphIcon },
```

同时可将排列样式进行重置，以还原原本的样式布局，修改`web\src\layouts\components\header\index.less`文件，替换为ragflow原始样式：`https://github.com/infiniflow/ragflow/blob/main/web/src/layouts/components/header/index.less`


## 交流群
如果有其它需求或问题建议，可加入交流群进行讨论

由于群聊超过200人，无法通过扫码加入，如需加群，加我微信zstar1003，备注"加群"即可。

## 鸣谢

本项目基于以下开源项目开发：

- [ragflow](https://github.com/infiniflow/ragflow)

- [v3-admin-vite](https://github.com/un-pany/v3-admin-vite)

## 更新信息获取

目前该项目仍在持续更新中，更新日志会在我的微信公众号[我有一计]上发布，欢迎关注。

## Star History

![Stargazers over time](https://starchart.cc/zstar1003/ragflow-plus.svg)