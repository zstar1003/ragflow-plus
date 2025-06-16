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
   * 4.3 删除文件(Delete documents)
- 5. 块管理(CHUNK MANAGEMENT WITHIN DATASET)
   * 5.1 添加块(Add chunk)
   * 5.2 查询块(List chunks)
- 6. 聊天助手管理(CHAT ASSISTANT MANAGEMENT)
   * 6.1 创建聊天助手(Create chat assistant)
   * 6.2 更新聊天助手配置(Update chat assistant)
   * 6.3 删除聊天助手(Delete chat assistants)
   * 6.4 查询聊天助手(List chat assistants)
- 7. 会话管理(SESSION MANAGEMENT)
   * 7.1 创建会话(Create session with chat assistant)
   * 7.2 更新会话信息(Update chat assistant's session)
   * 7.3 查询会话历史记录(List chat assistant's sessions)
   * 7.4 删除会话(Delete chat assistant's sessions)
   * 7.5 交互会话(Converse with chat assistant)


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


## 4.3 删除文件(Delete documents)
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
