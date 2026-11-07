import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.database import get_session, SessionLocal
from app.models import Conversation, ChatMessage, DocumentChunk, PolicyDocument, Citation
from app.schemas import ChatRequest
from app.services.rag_service import answer_question, save_chat

router = APIRouter(prefix="/chat", tags=["chat"])

# 查询所有会话内容，将来展示在页面上
@router.get("/conversations")
async def list_conversations(session: Session = Depends(get_session)):
    # 通过sqlalchemy 获取所有的会话数据
    conversation_result=session.query(Conversation).order_by(Conversation.updated_at.desc()).all()
    conversation_list=[]
    for item in conversation_result:
        print(item)
        conversation_list.append({
            "id": item.id,
            "title": item.title,
            "updated_at": item.updated_at
        })
    return conversation_list


@router.get("/conversations/{conversation_id}")
async def conversation_detail(conversation_id: str,session: Session = Depends(get_session)):
    """
       1、根据会话id 查询会话
       2、根据会话查询 消息列表
    """
    conversation=session.get(Conversation,conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages=session.query(ChatMessage).filter(ChatMessage.conversation_id==conversation_id).order_by(ChatMessage.created_at).all()

    # 接着查询引用以及文档块和文档信息
    # 通过message_id 进行获取
    message_ids=[message.id for message in messages]
    #print(message_ids)
    if message_ids:
        citation_rows = session.query(Citation,DocumentChunk,PolicyDocument) \
            .join(DocumentChunk,Citation.chunk_id==DocumentChunk.id) \
            .join(PolicyDocument,DocumentChunk.document_id==PolicyDocument.id) \
            .where(Citation.message_id.in_(message_ids)) \
            .order_by(Citation.message_id, Citation.label).all()
        print(citation_rows)

        # 分装一个字典，字典的key=message_id value=id对应的证据列表
        citations_by_message:dict[str,list[dict]]={}
        for citation,chunk,document in citation_rows:
            message_id=citation.message_id
            if message_id not in citations_by_message.keys():
                citations_by_message[message_id]=[]
            citations_by_message[message_id].append(
                {
                    "chunk_id": chunk.id,
                    "document_id": document.id,
                    "filename": document.filename,
                    "section": chunk.section,
                    "page": chunk.page,
                    "quote": citation.quote,
                    "score": citation.score,
                    "label": citation.label,
                }
            )

        messages_list=[]
        for item in messages:
            messages_list.append({
                "id": item.id,
                "role": item.role,
                "content": item.content,
                "refused": item.refused,
                "citations": citations_by_message.get(item.id),
                "created_at": item.created_at,
            })


        return {
            "id": conversation.id,
            "title": conversation.title,
            "messages":messages_list
        }
    else:
        return {
            "id": conversation.id,
            "title": conversation.title,
            "messages": []
        }


@router.delete("/conversations/{conversation_id}")
async def conversation_delete(conversation_id: str,session: Session = Depends(get_session)):
    """
       1、根据会话id 查询会话
       2、根据会话查询 消息列表
    """
    conversation=session.get(Conversation,conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    session.delete(conversation)
    session.commit()

# 传递一个event的名字和数据，封装好固定格式
def event(name: str, data) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

async def generate(chatRequest:ChatRequest):
    yield event("status", {"stage": "retrieving", "message": "正在检索政策依据"})
    # 开始进行检索
    try:
        with SessionLocal() as session:
            result=await answer_question(session,chatRequest.question,chatRequest.filters)
            yield event(
                "retrieval",
                {
                    "rewritten_query": result.trace.get("rewritten_query"),
                    "evidence_count": len(result.trace.get("final_evidence", [])),
                }
            )

            # 将内容分段传递给页面
            for index in range(0,len(result.answer),24):
                yield event('token',{'content':result.answer[index : index + 24]})
                #await asyncio.sleep(0)
            # 将消息保存到数据库中
            conversation,message=await save_chat(session,chatRequest.question,result,chatRequest.conversation_id)
            yield event(
                "done",
                {
                    "conversation_id": conversation.id,
                    "message_id": message.id,
                    "refused": result.refused,
                    "refusal_reason": (
                        result.trace.get("refusal_reason") if result.refused else None
                    ),
                    "citations": result.citations,
                    "latency_ms": result.latency_ms,
                    "trace": result.trace if chatRequest.debug else None,
                },
            )
    except Exception as exc:
        yield event("error", {"message": str(exc)})




@router.post("/stream")
async def chat_stream(payload:ChatRequest):

    return StreamingResponse(generate(payload), media_type="text/event-stream")



