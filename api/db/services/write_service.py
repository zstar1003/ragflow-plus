from api.db import LLMType, ParserType
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMBundle
from api import settings
from rag.app.tag import label_question
from rag.prompts import kb_prompt


def write_dialog(question, kb_ids, tenant_id):
    """
    处理用户搜索请求，从知识库中检索相关信息并生成回答

    参数:
        question (str): 用户的问题或查询
        kb_ids (list): 知识库ID列表，指定要搜索的知识库
        tenant_id (str): 租户ID，用于权限控制和资源隔离

    流程:
        1. 获取指定知识库的信息
        2. 确定使用的嵌入模型
        3. 根据知识库类型选择检索器(普通检索器或知识图谱检索器)
        4. 初始化嵌入模型和聊天模型
        5. 执行检索操作获取相关文档片段
        6. 格式化知识库内容作为上下文
        7. 构建系统提示词
        8. 生成回答并添加引用标记
        9. 流式返回生成的回答

    返回:
        generator: 生成器对象，产生包含回答和引用信息的字典
    """

    kbs = KnowledgebaseService.get_by_ids(kb_ids)
    embedding_list = list(set([kb.embd_id for kb in kbs]))

    is_knowledge_graph = all([kb.parser_id == ParserType.KG for kb in kbs])
    retriever = settings.retrievaler if not is_knowledge_graph else settings.kg_retrievaler
    # 初始化嵌入模型，用于将文本转换为向量表示
    embd_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING, embedding_list[0])
    # 初始化聊天模型，用于生成回答
    chat_mdl = LLMBundle(tenant_id, LLMType.CHAT)
    # 获取聊天模型的最大token长度，用于控制上下文长度
    max_tokens = chat_mdl.max_length
    # 获取所有知识库的租户ID并去重
    tenant_ids = list(set([kb.tenant_id for kb in kbs]))
    # 调用检索器检索相关文档片段
    kbinfos = retriever.retrieval(question, embd_mdl, tenant_ids, kb_ids, 1, 12, 0.1, 0.3, aggs=False, rank_feature=label_question(question, kbs))
    # 将检索结果格式化为提示词，并确保不超过模型最大token限制
    knowledges = kb_prompt(kbinfos, max_tokens)
    prompt = """
    角色：你是一个聪明的助手。  
    任务：总结知识库中的信息并回答用户的问题。  
    要求与限制：
    - 绝不要捏造内容，尤其是数字。
    - 如果知识库中的信息与用户问题无关，**只需回答：对不起，未提供相关信息。
    - 使用Markdown格式进行回答。
    - 使用用户提问所用的语言作答。
    - 绝不要捏造内容，尤其是数字。

    ### 来自知识库的信息
    %s

    以上是来自知识库的信息。

    """ % "\n".join(knowledges)
    msg = [{"role": "user", "content": question}]

    # 生成完成后添加回答中的引用标记
    # def decorate_answer(answer):
    #     nonlocal knowledges, kbinfos, prompt
    #     answer, idx = retriever.insert_citations(answer, [ck["content_ltks"] for ck in kbinfos["chunks"]], [ck["vector"] for ck in kbinfos["chunks"]], embd_mdl, tkweight=0.7, vtweight=0.3)
    #     idx = set([kbinfos["chunks"][int(i)]["doc_id"] for i in idx])
    #     recall_docs = [d for d in kbinfos["doc_aggs"] if d["doc_id"] in idx]
    #     if not recall_docs:
    #         recall_docs = kbinfos["doc_aggs"]
    #     kbinfos["doc_aggs"] = recall_docs
    #     refs = deepcopy(kbinfos)
    #     for c in refs["chunks"]:
    #         if c.get("vector"):
    #             del c["vector"]

    #     if answer.lower().find("invalid key") >= 0 or answer.lower().find("invalid api") >= 0:
    #         answer += " Please set LLM API-Key in 'User Setting -> Model Providers -> API-Key'"
    #     refs["chunks"] = chunks_format(refs)
    #     return {"answer": answer, "reference": refs}

    answer = ""
    for ans in chat_mdl.chat_streamly(prompt, msg, {"temperature": 0.1}):
        answer = ans
        yield {"answer": answer, "reference": {}}
    # yield decorate_answer(answer)
