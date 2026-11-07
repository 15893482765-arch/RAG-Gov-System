import asyncio
from functools import lru_cache
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document

from app.config import get_settings
from app.models import DocumentChunk,PolicyDocument
@lru_cache
def get_embeddings():
    settings=get_settings()
    embeddings_model=DashScopeEmbeddings(
        model=settings.embedding_model,
        dashscope_api_key=settings.dashscope_api_key
    )
    return embeddings_model
def get_vector_store():
    settings=get_settings()
    settings.milvus_path.mkdir(parents=True,exist_ok=True)
    from langchain_milvus import Milvus
    db_url=r"D:\newcode\PythonProject\langchainproject\backend\data\milvus\milvus_demo.db"

    vector_store=Milvus(
        embedding_function=get_embeddings(),
        connection_args={"uri":db_url},
        collection_name="policy_chunks",
        auto_id=False,
        consistency_level="Strong",
        index_params={
            "metric_type": "COSINE",  # 关键
            "index_type": "HNSW",
            "params": {"M": 8, "efConstruction": 64}
        }
    )
    return vector_store
class VectorStoreService:
    # 传递 两个参数，第一个参数是整个文档对象  第二个参数是切割之后的父子块集合
    async def add_chunks(
            self,
            document: PolicyDocument,
            chunks: list[DocumentChunk]
    ) -> None:

        # 将所有的子块中的内容放入到一个list集合中
        texts = [chunk.content for chunk in chunks]

        # 将所有的子块中的id放入到一个list集合中
        chunk_ids = [chunk.id for chunk in chunks]

        # 将所有的子块中的元数据放入到一个list集合中
        metadatas = []
        for chunk in chunks:
            if document.effective_date:
                effective_date = document.effective_date.isoformat()
            else:
                effective_date = ""

            # metadata 方便将来查找
            metadatas.append(
                {
                    "document_id": document.id,
                    "filename": document.filename,
                    "topic": document.topic or "",
                    "effective_date": effective_date,
                    "section": chunk.section or "",
                    "page": chunk.page or 0,
                    "parent_id": chunk.parent_id or "",
                    "chunk_id":chunk.id
                }
            )
        # 此时形成了三个list ,这三个list的长度一样，根据下标获取的内容也可以一一照应上
        # 此时可以形成拉链 zip
        doc_list: list[Document] = []
        vector_store = get_vector_store()
        for chunk_id, content, metadata in zip(chunk_ids, texts, metadatas):
            doc = Document(page_content=content, metadata=metadata, id=chunk_id)
            doc_list.append(doc)
            if len(doc_list) == 10:
                vector_store.add_documents(doc_list)
                doc_list = []
        if len(doc_list)>0:
            vector_store.add_documents(doc_list)
            doc_list.clear()
    async def search(self,
                     query:str,
                     top_k:int,
                     document_ids:list[str]|None=None)->list[dict]:
        vector_store=get_vector_store()
        if document_ids:
            # Milvus expr表达式语法，$in
            ids_list=[f'"{x}"' for x in document_ids]
            ids=",".join(ids_list)
            expr=f'document_id in [{ids}]'
        else:
            expr=None
        results=vector_store.similarity_search_with_score(query,top_k,expr=expr)

        return [
            {
                "chunk_id": tuple[0].metadata["chunk_id"],
                "content": tuple[0].page_content,
                "metadata": tuple[0].metadata,
                "score": tuple[1],
                "source": tuple[0].metadata["filename"],
            }
            for index, tuple in enumerate(results)
        ]
    async def delete_document(self,document_id:str)->None:
        vector_store=get_vector_store()
        expr=f'document_id=="{document_id}"'
        vector_store.delete(expr=expr)
    #将数据库清空
    async def reset(self)->None:
        vector_store=get_vector_store()
        expr=f'pk>0'
        vector_store.delete(expr=expr)

















