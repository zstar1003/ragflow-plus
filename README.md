# Ragflow-Plus

## 项目介绍

Ragflow-Plus 是一个基于 Ragflow 的开源项目，主旨是在不影响 Ragflow 原有功能的基础上，提供一些新的功能，以解决实际应用中的一些痛点。

## 新增功能介绍

### 一. 用户后台管理系统

移除原登陆页用户注册的通道，搭建用户后台管理系统，可对用户进行管理，包括用户注册、查询、删除、修改等功能。

### 二. 优化对话显示
微调了对话界面的样式，使其观感更为友好

### 三. 文档撰写功能
新增文档撰写全新的交互方式，支持直接导出为 Word 文档

## 使用方式

### 1. 前端文件替换

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

### 2. 管理系统运行方式

#### 2.1 使用Docker Compose运行

```bash
docker compose -f management/docker-compose.yml up -d
```

访问地址：`服务器ip:8080`，进入到管理界面

#### 2.2 源码运行

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


## Agent功能恢复

由于在我的应用场景中，不需要Agent功能，故隐藏了Agent按钮的入口，如需恢复Agent功能，可修改`web\src\layouts\components\header\index.tsx`，对以下内容取消注释：

```tsx
{ path: '/flow', name: t('flow'), icon: GraphIcon },
```

同时可将排列样式进行重置，以还原原本的样式布局，修改`web\src\layouts\components\header\index.less`文件，替换为ragflow原始样式：`https://github.com/infiniflow/ragflow/blob/main/web/src/layouts/components/header/index.less`


## Todo List

- [x] 搭建用户后台管理系统

- [ ] 知识库批量上传解析

- [ ] 文档撰写图表支持

## 交流群
如果有其它需求或问题建议，可加入交流群进行讨论

<div align="center">
  <img src="assets/group.jpg" width="300" alt="交流群">
</div>

## License

版权说明：本项目在 Ragflow 项目基础上进行二开，需要遵守 Ragflow 的开源协议，如下

This repository is available under the [Ragflow
 Open Source License](LICENSE), which is essentially Apache 2.0 with a few additional restrictions.

## 鸣谢

本项目基于以下开源项目开发：

- [ragflow](https://github.com/infiniflow/ragflow)

- [v3-admin-vite](https://github.com/un-pany/v3-admin-vite)

## 更新信息获取

主要更新日志会在我的微信公众号[我有一计]上发布，欢迎关注。

## Star History

![Stargazers over time](https://starchart.cc/zstar1003/ragflow-plus.svg)