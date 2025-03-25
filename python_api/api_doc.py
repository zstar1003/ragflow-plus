from openai import OpenAI

model = "deepseek-r1:1.5b"
client = OpenAI(api_key="ragflow-FiNzM5YTEyMDk0MjExZjA5OTg4MDI0Mm", base_url=f"http://localhost/api/v1/chats_openai/ec69b3f4fbeb11ef862c0242ac120002")

completion = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "你是一个乐于助人的助手"},
        {"role": "user", "content": "你是谁？"},
    ],
    stream=False
)

stream = False
if stream:
    for chunk in completion:
        print(chunk)
else:
    print(completion.choices[0].message.content)