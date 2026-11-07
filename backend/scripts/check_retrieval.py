import asyncio


from app.database import  SessionLocal
from app.schemas import RetrievalFilters
from app.services.retrieval import retrieve, RetrievalResult

if __name__ == '__main__':
	session=SessionLocal()
	filter=RetrievalFilters()

	#filter.topic="测试主题"
	#filter.document_ids=['05129ece-2292-450c-8dc9-d68f9d3739fc']

	result:RetrievalResult=asyncio.run(retrieve(
		session,
		"申请青年人才租房补贴流程是什么？",
		#"今晚上晚自习吗？",
		filter
	))
	print("******************************")
	print(result)





