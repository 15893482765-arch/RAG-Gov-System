import asyncio

from app.services.vector_store import VectorStoreService
def search():
    service = VectorStoreService()
    document_ids = ["d95c029a-1e82-411e-9807-1493675dcf2f"]
    results = asyncio.run(service.search("青年人在这里可以申请人才公寓吗?", 3, document_ids))
    print("搜索结果:", results)
def text_delete():
    service = VectorStoreService()
    document_id= "27969611-88aa-43f2-9191-1c48f6f00eed"
    asyncio.run(service.delete_document(document_id))

def milvus_delete():
    service = VectorStoreService()
    asyncio.run(service.reset())
if __name__ == '__main__':
    # text_delete()
    # milvus_delete()
    search()