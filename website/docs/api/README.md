本项目采用了和ragflow一致的api接口，python的api接口如下。

http接口可参考原文档：https://github.com/infiniflow/ragflow/blob/main/docs/references/http_api_reference.md

# 目录
- 1. 依赖安装/密钥准备
- 2. 创建聊天(Create chat completion)
- 3. 知识库管理(DATASET MANAGEMENT)
   * 3.1 创建知识库(Create dataset)
   * 3.2 查询知识库(List datasets)
   * 3.3 删除知识库(Delete datasets)
   * 3.4 更新知识库配置(Update dataset)
- 4. 文件管理 (FILE MANAGEMENT WITHIN DATASET)
   * 4.1 上传文件(Upload documents)
   * 4.2 更新文件配置(Upload documents)
   * 4.3 下载文件(Download document)
   * 4.4 删除文件(Delete documents)
   * 4.5 文件解析(Parse documents)
   * 4.5 停止文件解析(Stop parsing documents)
- 5. 块管理(CHUNK MANAGEMENT WITHIN DATASET)
   * 5.1 添加块(Add chunk)
   * 5.2 查询块(List chunks)
   * 5.3 删除块(Delete chunks)
   * 5.4 更新块内容(Update chunk)
   * 5.5 检索块 Retrieve chunks
- 6. 聊天助手管理(CHAT ASSISTANT MANAGEMENT)
   * 6.1 创建聊天助手(Create chat assistant)]
   * 6.2 更新聊天助手配置(Update chat assistant)
   * 6.3 删除聊天助手(Delete chat assistants)
   * 6.4 查询聊天助手(List chat assistants)
- 7. 会话管理(SESSION MANAGEMENT)
   * 7.1 创建会话(Create session with chat assistant)
   * 7.2 更新会话信息(Update chat assistant's session)
   * 7.3 查询会话历史记录(List chat assistant's sessions)
   * 7.4 删除会话(Delete chat assistant's sessions)
   * 7.5 交互会话(Converse with chat assistant)
- 8. 智能体管理(AGENT MANAGEMENT)
   * 8.1 创建智能体(Create session with agent)
   * 8.2 智能体交互(Converse with agent)
   * 8.3 查询智能体会话(List agent sessions)
   * 8.4 查询智能体(List agents)


# 1. 依赖安装/密钥准备
使用python调用API接口，需要安装`ragflow-sdk`依赖，可用pip进行安装：
```python
pip install ragflow-sdk
```

之后，需要在API菜单中，创建一个`API KEY`，复制该值，后续要用到。

# 2. 创建聊天(Create chat completion)
通过OpenAI的API为选择助理进行聊天。

这里的示例需要修改三个值：
- model：模型名称
- api_key：替换成自己的api_key，后文同理
- base_url：最后面一串为具体助手的`dialogId`，可直接从url中查看获取

可选参数：stream，用于指定是否采用流式输出

```python
from openai import OpenAI

model = "deepseek-r1:1.5b"
client = OpenAI(api_key="ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm", base_url=f"http://localhost/api/v1/chats_openai/ec69b3f4fbeb11ef862c0242ac120002")

completion = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "你是一个乐于助人的助手"},
        {"role": "user", "content": "你是谁？"},
    ],
    stream=True
)

stream = True
if stream:
    for chunk in completion:
        print(chunk)
else:
    print(completion.choices[0].message.content)
```

如果使用 `Infinity`，作为检索引擎，实测会发现遇到报错，等待官方后续完善支持。
```c
省略xxx条内容
2025-03-25 22:30:52     raise InfinityException(res.error_code, res.error_msg)
2025-03-25 22:30:52 infinity.common.InfinityException
```

# 3. 知识库管理(DATASET MANAGEMENT)
## 3.1 创建知识库(Create dataset)

创建一个名称为`kb_1`的知识库
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.create_dataset(name="kb_1")
```


![](https://files.mdnice.com/user/11855/52fbd13e-1eac-4f0f-8cbc-ba64b2d1d4c7.png)



## 3.2 查询知识库(List datasets)
根据名称，查询知识库信息
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)

# 查询所有知识库
for dataset in rag_object.list_datasets():
    print(dataset)
# 根据name查询某一知识库
dataset = rag_object.list_datasets(name = "kb_1")
print(dataset[0])
```

## 3.3 删除知识库(Delete datasets)
删除指定知识库

只能根据知识库id进行删除，无name接口，id通过上一步查询得到

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
rag_object.delete_datasets(ids = ["50f80d7c099111f0ad0e0242ac120006"])
```

## 3.4 更新知识库配置(Update dataset)
更新已存在的知识库配置

这里原始文档给的示例存在小问题，`rag_object.list_datasets`返回的是一个list，因此需要取出list中第一项，对于该问题，我提交了一个PR：Fix: python_api_reference.md update dataset bug

PR链接：https://github.com/infiniflow/ragflow/pull/6527

官方响应还是挺快的，晚上提交的，第二天上午review，下午就merge了。


```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
dataset.update({"chunk_method":"manual"})
```

# 4. 文件管理 (FILE MANAGEMENT WITHIN DATASET)

## 4.1 上传文件(Upload documents)
上传文件进入到`kb_1`的知识库

两个主要参数：

- display_name：文件名
- blob：文件的二进制内容

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
dataset.upload_documents([{"display_name": "1.txt", "blob": open('1.txt',"rb").read()}])
```


## 4.2 更新文件配置(Upload documents)
更新已有文件的配置信息

原文档这里也有个小错误：`doc.update`外层多一个list，这里直接进行修正。

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
doc = dataset.list_documents(id="7c5ea41409f811f0b9270242ac120006")
doc = doc[0]
doc.update({"parser_config": {"chunk_token_count": 256}})
```

## 4.3 下载文件(Download document)
根据documents id，下载文件

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
doc = dataset.list_documents(id="7c5ea41409f811f0b9270242ac120006")
doc = doc[0]
open("ragflow.txt", "wb+").write(doc.download())
```

这是按照文档实现的方法，但存在问题，`doc.download()`返回的是json数据，而不是二进制数据，会导致写入失败，尚未修复。

## 4.4 删除文件(Delete documents)
根据documents id，删除文件

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
dataset.delete_documents(ids=["7c5ea41409f811f0b9270242ac120006"])
```



## 4.5 文件解析(Parse documents)
传入documents id，批量解析文件

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
dataset.async_parse_documents(["91bd7c5e0a0711f08a730242ac120006"])
print("Async bulk parsing initiated.")
```


## 4.5 停止文件解析(Stop parsing documents)
传入documents id，批量停止解析文件
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
dataset.async_cancel_parse_documents(["91bd7c5e0a0711f08a730242ac120006"])
print("Async bulk parsing cancelled.")
```

# 5. 块管理(CHUNK MANAGEMENT WITHIN DATASET)
## 5.1 添加块(Add chunk)
增加一个分块，content为具体chunk的内容

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
doc = dataset.list_documents(id="91bd7c5e0a0711f08a730242ac120006")
doc = doc[0]
chunk = doc.add_chunk(content="xxxxxxx")
```

![](https://files.mdnice.com/user/11855/1bdb3ad0-cf7a-4c8f-83c7-8efc2dcb61bb.png)


## 5.2 查询块(List chunks)
查询`kb_1`中所有块的具体信息

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
docs = dataset.list_documents(keywords="1", page=1, page_size=12)
for chunk in docs[0].list_chunks(keywords="", page=1, page_size=12):
    print(chunk)
```
## 5.3 删除块(Delete chunks)
根据文档id和块id，删除块

```python

from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
doc = dataset.list_documents(id="91bd7c5e0a0711f08a730242ac120006")
doc = doc[0]
doc.delete_chunks(["b7119fec099611f0b3d60242ac120006"])
```

实测运行会出现如下报错，原因未知：
```bash
Traceback (most recent call last):
  File "D:\Code\ragflow\python_api\api_doc.py", line 12, in <module>
    doc.delete_chunks(["b7119fec099611f0b3d60242ac120006"])
  File "<@beartype(ragflow_sdk.modules.document.Document.delete_chunks) at 0x298f9cf4b80>", line 47, in delete_chunks
  File "D:\anaconda3\envs\lianghua\lib\site-packages\ragflow_sdk\modules\document.py", line 93, in delete_chunks
    raise Exception(res.get("message"))
Exception: rm_chunk deleted chunks 0, expect 1
```


## 5.4 更新块内容(Update chunk)
将添加的chunk的内容进行更新：
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
doc = dataset.list_documents(id="91bd7c5e0a0711f08a730242ac120006")
doc = doc[0]
chunk = doc.add_chunk(content="123")
chunk.update({"content":"sdfx..."})
```
## 5.5 检索块 Retrieve chunks
检索块中的信息

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
doc = dataset.list_documents(id="91bd7c5e0a0711f08a730242ac120006")
doc = doc[0]
doc.add_chunk(content="This is a chunk addition test")
for c in rag_object.retrieve(dataset_ids=[dataset.id],document_ids=[doc.id]):
    print(c)
```
运行结果：无报错，但无检索出内容，原因未知

# 6. 聊天助手管理(CHAT ASSISTANT MANAGEMENT)
## 6.1 创建聊天助手(Create chat assistant)
创建一个名为`"Miss R"`的聊天助手

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
datasets = rag_object.list_datasets(name="kb_1")
dataset_ids = []
for dataset in datasets:
    dataset_ids.append(dataset.id)
assistant = rag_object.create_chat("Miss R", dataset_ids=dataset_ids)
```

## 6.2 更新聊天助手配置(Update chat assistant)
更新聊天助手的各种配置，可选项参考原文档

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
datasets = rag_object.list_datasets(name="kb_1")
dataset_id = datasets[0].id
assistant = rag_object.create_chat("Miss R2", dataset_ids=[dataset_id])
assistant.update({"name": "Stefan", "llm": {"temperature": 0.8}, "prompt": {"top_n": 8}})
```
## 6.3 删除聊天助手(Delete chat assistants)
根据dialogId，删除指定助手

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
rag_object.delete_chats(ids=["a39fa5480a2d11f082850242ac120006"])
```

## 6.4 查询聊天助手(List chat assistants)
查询所有聊天助手信息

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
for assistant in rag_object.list_chats():
    print(assistant)
```
# 7. 会话管理(SESSION MANAGEMENT)

## 7.1 创建会话(Create session with chat assistant)
选择`Miss R`助理，创建新会话
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
assistant = rag_object.list_chats(name="Miss R")
assistant = assistant[0]
session = assistant.create_session()
```

## 7.2 更新会话信息(Update chat assistant's session)
创建完会话，并更新了会话名称
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
assistant = rag_object.list_chats(name="Miss R")
assistant = assistant[0]
session = assistant.create_session("session_name")
session.update({"name": "updated_name"})
```

## 7.3 查询会话历史记录(List chat assistant's sessions)
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
assistant = rag_object.list_chats(name="Miss R")
assistant = assistant[0]
for session in assistant.list_sessions():
    print(session)
```

## 7.4 删除会话(Delete chat assistant's sessions)
根据conversationId，删除某一会话
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
assistant = rag_object.list_chats(name="Miss R")
assistant = assistant[0]
assistant.delete_sessions(ids=["0ed10bce0a3111f0a3240242ac120006"])
```

## 7.5 交互会话(Converse with chat assistant)
指定某一助手，进行交互提问
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
assistant = rag_object.list_chats(name="Miss R")
assistant = assistant[0]
session = assistant.create_session()    

print("\n==================== Miss R =====================\n")
print("Hello. What can I do for you?")

while True:
    question = input("\n==================== User =====================\n> ")
    print("\n==================== Miss R =====================\n")
    
    cont = ""
    for ans in session.ask(question, stream=True):
        print(ans.content[len(cont):], end='', flush=True)
        cont = ans.content
```
