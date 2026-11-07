import asyncio
from app.database import SessionLocal
from app.schemas import RetrievalFilters
from app.services.rag_service import answer_question, save_chat
from app.services.retrieval import RetrievalResult

async def main():
    session = SessionLocal()
    try:
        filter = RetrievalFilters()
        # filter.topic = "测试主题"
        # filter.document_ids = ['05129ece-2292-450c-8dc9-d68f9d3739fc']

        result = await answer_question(
            session=session,
            question="如何加强公共数据共享和治理",
            filters=filter,
            top_k=8,
            rerank_top_k=3,
            min_score=0.25
        )
        print("******************************")
        print(result)

        # 保存对话、消息、引用记录
        conv, msg = await save_chat(
            session=session,
            question="如何加强公共数据共享和治理",
            result=result,
            conversation_id=None  # None = 新建会话
        )
        print(f"✅ 会话持久化成功！conversation_id={conv.id}, message_id={msg.id}")
    finally:
        session.close()

if __name__ == '__main__':
    asyncio.run(main())