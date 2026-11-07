import asyncio
from app.database import SessionLocal
from app.schemas import RetrievalFilters
from app.services.retrieval import keyword_search


if __name__=="__main__":
    session = SessionLocal()
    filter = RetrievalFilters()
    # filter.topic = "测试主题"
    # filter.document_ids = ['05129ece-2292-450c-8dc9-d68f9d3739fc']
    asyncio.run(keyword_search(
        session=session,
        query="涉及敏感个人信息",
        top_k=3,
        filters=filter
    ))
