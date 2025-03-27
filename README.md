# Ragflow-Plus

## 项目介绍

在原有 Ragflow 的基础中，该项目做了一些二开，以解决实际应用中的一些痛点。

## 名字说明
Ragflow-Plus，该名字不是说比 Ragflow 项目牛的意思，而是对标 Dify-Plus 作为 Ragflow 的二开项目，以解决行业应用时共同的痛点问题。

## 新增功能介绍

### 一. 用户批量注册/批量加入团队
隐藏了原本用户注册的功能，改为管理员通过后台批量注册，并加入管理员团队，可共享团队知识库及默认模型配置

使用方式:
1. python环境安装依赖：

参考python版本：python == 3.10.16
```python
pip install mysql-connector-python
pip install pycryptodomex
pip install werkzeug
```

2. 修改`python_sql\add.json`文件内容：

- student_id 为 待添加用户学号
- tenant_id 为 共享知识库的队长id，需要连接数据库查看

3. 执行批量插入操作：

```python
python python_sql/add_sql_final.py
```

默认用户名为 `学号@xidian.cn`
默认密码为 `学号`


### 二. 优化对话显示
微调了对话界面的样式，使其观感更为友好

### 三. 文档撰写功能
新增文档撰写全新的交互方式，支持直接导出为 Word 文档

## 使用方式
1. 克隆项目
```bash
git clone https://github.com/zstar1003/ragflow-plus.git
```

2. 打包web文件
```bash
cd web
npm run build
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


## TODO

- [ ] 用户批量注册可视化后台管理

- [ ] 文档撰写插入图片

- [ ] 知识库批量上传解析

## 交流群
如果有其它需求或问题建议，可加入交流群进行讨论

![交流群.jpg](assets/group.jpg)


## License

版权说明：本项目在 Ragflow 项目基础上进行二开，需要遵守 Ragflow 的开源协议，如下

This repository is available under the [Ragflow
 Open Source License](LICENSE), which is essentially Apache 2.0 with a few additional restrictions.