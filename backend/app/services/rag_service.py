import time
from dataclasses import dataclass
from typing import Any
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Conversation, ChatMessage, Citation
from app.schemas import RetrievalFilters
from app.services.model_fectory import create_chat_model, invoke_text

from app.services.retrieval import retrieve

REFUSAL_TEXT = (
    "根据当前知识库资料，无法找到足够可靠的依据回答该问题。请补充政策名称、地区或办理事项。"
)


# 用户的问题，rag回答的内容需要封装成这个类 返回
@dataclass
class RAGAnswer:
    answer: str
    refused: bool
    citations: list[dict[str, Any]]
    trace: dict[str, Any]
    latency_ms: int
    token_usage: dict[str, Any]

import re
CITATION_PATTERN = re.compile(r"\[(\d+)\]")
def validate_citations(answer: str, evidence: list[dict]) -> tuple[str, list[int]]:
    """
    校验回答里的角标引用标记 [数字]，过滤无效引用；返回清理后的回答 + 合法引用编号列表
    :param answer: LLM输出的回答文本，里面带有 [1][2] 这类引用标记
    :param evidence: RAG检索出来的证据片段列表，长度N，合法引用编号是 1~N
    :return: (清理后的回答文本, 真正有效的引用id有序列表)
    """
    # 提取answer中的序号
    r1=CITATION_PATTERN.findall(answer)
    cited=set()
    for value in r1:
        cited.add(int(value))
    print(cited)
    # 根据证据中的list的长度，获取一个set集合
    valid=set()
    for i in range(1,len(evidence)+1):
        valid.add(i)
    print(valid)
    # 不合理的编号   就是模型中有，但是不应该存在的
    invalid = cited - valid
    print(invalid)
    if invalid:
        for index in invalid:
            answer=answer.replace(f'[{index}]','')
    print(answer)
    # set集合会自动从小到大排序，添加完list之后依然可以排序，所以此处不用sorted
    return answer, list(cited & valid)

if __name__ == '__main__':
    validate_citations('向量数据库[2]，大模型幻觉[4]，Reranker[3]',[{},{},{},{}])

    set1=list({1,2,3,5,4})
    print(set1)


# 先检索找证据，然后才能调用大模型
async def answer_question(
    session: Session,
    question: str,
    filters: RetrievalFilters | None = None,
    mode: str = "full",
    top_k: int | None = 8,
    rerank_top_k: int | None = 4,
    min_score: float | None = 0.25,
) -> RAGAnswer:
    start = time.perf_counter()
    print("++++++++")

    retrieve_result=await retrieve(session, question, filters, top_k, 4, min_score, mode)
    print("------------")
    if retrieve_result.refused:
        return RAGAnswer(
            REFUSAL_TEXT,
            True,
            [],
            retrieve_result.trace,
            int((time.perf_counter() - start)*1000),
            {}
        )
    # 代码如果能到这里，说明问题有检索的结果
    evidences=retrieve_result.evidence
    contexts=[]
    for index,evidence in enumerate(evidences,start=1):

        content=evidence['content']
        page=evidence['metadata']['page']
        section=evidence['metadata']['section']
        filename=evidence['metadata']['filename']
        contexts.append(f"[{index}] 文档：{filename},章节：{section},页码：{page}\n{content}")

    context="\n\n".join(contexts)
    print(context)

    prompt = f"""你是政务政策知识库助手。必须遵守：
    1. 只能依据“政策证据”回答，不得使用外部知识补充政策内容。
    2. 每个包含政策事实、数字、日期、对象或条件的句子末尾标注引用编号，如[1]。
    3. 证据没有说明的内容，明确回答“资料未说明”。
    4. 不得编造政策名称、办理条件、部门、时间或引用。

    政策证据：
    {context}

    用户问题：{question}
    """
    llm=create_chat_model(temperature=0)
    answer,usage=await invoke_text(llm,prompt)
    print(answer,usage)

    # 将结果和之前的证据进行匹配，过掉中结果中不合理的编号
    answer,list_xh=validate_citations(answer,evidences)
    # 收集该答案对应的引用信息
    citations=[]
    for index in list_xh:
        item=evidences[index-1]
        citations.append(
            {
                "chunk_id": item["chunk_id"],
                "document_id": item["metadata"].get("document_id", ""),
                "filename": item["metadata"].get("filename", ""),
                "section": item["metadata"].get("section") or None,
                "page": item["metadata"].get("page") or None,
                "quote": item["content"][:500],
                "score": item["evidence_score"],
                "label": str(index),
            }
        )

    if mode=='full' and not citations:
        answer=REFUSAL_TEXT
        refused=True
    else:
        refused=False

    trace=retrieve_result.trace
    trace["citation_validation"]={
        'cited_indexes':list_xh,
        'valid': not refused
    }

    ragAnswer=RAGAnswer(
        answer,
        refused,
        citations,
        trace,
        int((time.perf_counter() - start) * 1000),
        usage
    )
    # 在返回数据之前，将信息保存到数据库中
    await save_chat(session,question,ragAnswer,None)


    return ragAnswer


async def save_chat(
    session: Session,
    question: str,
    result: RAGAnswer,
    conversation_id: str | None,
) -> tuple[Conversation, ChatMessage]:

    # 保存会话数据
    if conversation_id:
        conversation=session.get(Conversation,conversation_id)
    else:
        conversation=None

    if not conversation:
        conversation=Conversation(title=question[:10])
        session.add(conversation)
        # 刷新一下，就会出现id
        session.flush()

    # 先保存用户提出的问题，用户的问题也是消息
    # 保存消息数据
    userMessage=ChatMessage(
        conversation_id=conversation.id,
        content=question,
        role='user'
    )
    session.add(userMessage)
    assistant_message = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=result.answer,
        refused=result.refused,
        latency_ms=result.latency_ms,
        token_usage=result.token_usage,
        trace=result.trace,
    )
    session.add(assistant_message)
    session.flush()

    #保存引用数据
    if result.citations:
        for citation in result.citations:
            session.add(Citation(
                message_id=assistant_message.id,
                chunk_id=citation["chunk_id"],
                label=citation["label"],
                quote=citation["quote"],
                score=citation["score"],
            ))

    session.commit()

    return conversation,assistant_message










