이 프로젝트는 ragflow와 동일한 api 인터페이스를 사용하며, python의 api 인터페이스는 다음과 같습니다.

http 인터페이스는 원본 문서를 참고하세요: https://github.com/infiniflow/ragflow/blob/main/docs/references/http_api_reference.md

# 목차
- 1. 의존성 설치/키 준비
- 2. 채팅 생성(Create chat completion)
- 3. 지식베이스 관리(DATASET MANAGEMENT)
   * 3.1 지식베이스 생성(Create dataset)
   * 3.2 지식베이스 조회(List datasets)
   * 3.3 지식베이스 삭제(Delete datasets)
   * 3.4 지식베이스 설정 업데이트(Update dataset)
- 4. 파일 관리 (FILE MANAGEMENT WITHIN DATASET)
   * 4.1 파일 업로드(Upload documents)
   * 4.2 파일 설정 업데이트(Upload documents)
   * 4.3 파일 삭제(Delete documents)
- 5. 청크 관리(CHUNK MANAGEMENT WITHIN DATASET)
   * 5.1 청크 추가(Add chunk)
   * 5.2 청크 조회(List chunks)
- 6. 채팅 어시스턴트 관리(CHAT ASSISTANT MANAGEMENT)
   * 6.1 채팅 어시스턴트 생성(Create chat assistant)
   * 6.2 채팅 어시스턴트 설정 업데이트(Update chat assistant)
   * 6.3 채팅 어시스턴트 삭제(Delete chat assistants)
   * 6.4 채팅 어시스턴트 조회(List chat assistants)
- 7. 세션 관리(SESSION MANAGEMENT)
   * 7.1 세션 생성(Create session with chat assistant)
   * 7.2 세션 정보 업데이트(Update chat assistant's session)
   * 7.3 세션 기록 조회(List chat assistant's sessions)
   * 7.4 세션 삭제(Delete chat assistant's sessions)
   * 7.5 대화 세션(Converse with chat assistant)


# 1. 의존성 설치/키 준비
python을 사용하여 API 인터페이스를 호출하려면 `ragflow-sdk` 의존성을 설치해야 하며, pip로 설치할 수 있습니다:
```python
pip install ragflow-sdk
```

그 후, API 메뉴에서 `API KEY`를 생성하고, 해당 값을 복사하여 이후에 사용합니다.

# 2. 채팅 생성(Create chat completion)
OpenAI의 API를 통해 선택한 어시스턴트와 채팅합니다.

여기 예제에서는 세 개의 값을 수정해야 합니다:
- model: 모델 이름
- api_key: 자신의 api_key로 교체하세요, 이후 동일
- base_url: 마지막 문자열은 구체적인 어시스턴트의 `dialogId`이며, url에서 직접 확인할 수 있습니다

선택 매개변수: stream, 스트림 출력 사용 여부를 지정합니다

```python
from openai import OpenAI

model = "deepseek-r1:1.5b"
client = OpenAI(api_key="ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm", base_url=f"http://localhost/api/v1/chats_openai/ec69b3f4fbeb11ef862c0242ac120002")

completion = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "당신은 도움이 되는 어시스턴트입니다"},
        {"role": "user", "content": "당신은 누구인가요?"},
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


# 3. 지식베이스 관리(DATASET MANAGEMENT)
## 3.1 지식베이스 생성(Create dataset)

`kb_1`이라는 이름의 지식베이스를 생성합니다
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.create_dataset(name="kb_1")
```



## 3.2 지식베이스 조회(List datasets)
이름을 기준으로 지식베이스 정보를 조회합니다
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)

# 모든 지식베이스 조회
for dataset in rag_object.list_datasets():
    print(dataset)
# 이름으로 특정 지식베이스 조회
dataset = rag_object.list_datasets(name = "kb_1")
print(dataset[0])
```

## 3.3 지식베이스 삭제(Delete datasets)
지정된 지식베이스를 삭제합니다

지식베이스 id로만 삭제할 수 있으며, name 인터페이스는 없습니다. id는 이전 단계의 조회를 통해 얻을 수 있습니다

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
rag_object.delete_datasets(ids = ["50f80d7c099111f0ad0e0242ac120006"])
```

## 3.4 지식베이스 설정 업데이트(Update dataset)

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
dataset.update({"chunk_method":"manual"})
```

# 4. 파일 관리 (FILE MANAGEMENT WITHIN DATASET)

## 4.1 파일 업로드(Upload documents)
`kb_1` 지식베이스에 파일을 업로드합니다

두 가지 주요 매개변수:

- display_name: 파일명
- blob: 파일의 바이너리 내용

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
dataset.upload_documents([{"display_name": "1.txt", "blob": open('1.txt',"rb").read()}])
```


## 4.2 파일 설정 업데이트(Upload documents)

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


## 4.3 파일 삭제(Delete documents)
documents id를 기반으로 파일을 삭제합니다

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
dataset = rag_object.list_datasets(name="kb_1")
dataset = dataset[0]
dataset.delete_documents(ids=["7c5ea41409f811f0b9270242ac120006"])
```

# 5. 청크 관리(CHUNK MANAGEMENT WITHIN DATASET)
## 5.1 청크 추가(Add chunk)
청크를 추가합니다. content는 구체적인 chunk의 내용입니다

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


## 5.2 청크 조회(List chunks)
`kb_1`에 있는 모든 청크의 구체적인 정보를 조회합니다

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


# 6. 채팅 어시스턴트 관리(CHAT ASSISTANT MANAGEMENT)
## 6.1 채팅 어시스턴트 생성(Create chat assistant)
`"Miss R"`이라는 이름의 채팅 어시스턴트를 생성합니다

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

## 6.2 채팅 어시스턴트 설정 업데이트(Update chat assistant)
채팅 어시스턴트의 다양한 설정을 업데이트합니다. 선택 항목은 원본 문서를 참조하세요

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

## 6.3 채팅 어시스턴트 삭제(Delete chat assistants)
dialogId를 기반으로 지정된 어시스턴트를 삭제합니다

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
rag_object.delete_chats(ids=["a39fa5480a2d11f082850242ac120006"])
```

## 6.4 채팅 어시스턴트 조회(List chat assistants)
모든 채팅 어시스턴트 정보를 조회합니다

```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
for assistant in rag_object.list_chats():
    print(assistant)
```
# 7. 세션 관리(SESSION MANAGEMENT)

## 7.1 세션 생성(Create session with chat assistant)
`Miss R` 어시스턴트를 선택하여 새 세션을 생성합니다
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
assistant = rag_object.list_chats(name="Miss R")
assistant = assistant[0]
session = assistant.create_session()
```

## 7.2 세션 정보 업데이트(Update chat assistant's session)
세션을 생성하고 세션 이름을 업데이트합니다
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

## 7.3 세션 기록 조회(List chat assistant's sessions)
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

## 7.4 세션 삭제(Delete chat assistant's sessions)
conversationId를 기반으로 특정 세션을 삭제합니다
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
assistant = rag_object.list_chats(name="Miss R")
assistant = assistant[0]
assistant.delete_sessions(ids=["0ed10bce0a3111f0a3240242ac120006"])
```

## 7.5 대화 세션(Converse with chat assistant)
특정 어시스턴트를 지정하여 대화형 질문을 합니다
```python
from ragflow_sdk import RAGFlow

api_key = "ragflow-I0NmRjMWNhMDk3ZDExZjA5NTA5MDI0Mm"
base_url = "http://localhost:9380"

rag_object = RAGFlow(api_key=api_key, base_url=base_url)
assistant = rag_object.list_chats(name="Miss R")
assistant = assistant[0]
session = assistant.create_session()    

print("\n==================== Miss R =====================\n")
print("안녕하세요. 무엇을 도와드릴까요?")

while True:
    question = input("\n==================== 사용자 =====================\n> ")
    print("\n==================== Miss R =====================\n")
    
    cont = ""
    for ans in session.ask(question, stream=True):
        print(ans.content[len(cont):], end='', flush=True)
        cont = ans.content
```
