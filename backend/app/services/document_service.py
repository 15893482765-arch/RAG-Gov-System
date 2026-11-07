import asyncio
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm.session import Session
from fastapi import  UploadFile

from app.config import get_settings
from app.models import DocumentStatus, PolicyDocument, DocumentChunk

from app.services.chunking import split_policy_text
from app.services.vector_store import VectorStoreService

# set集合
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}



from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


def extract_pages(path: Path) -> list[tuple[int | None, str]]:
	suffix=path.suffix.lower()
	if suffix==".pdf":
		return [(index+1,page.extract_text() or "") for index,page in enumerate(PdfReader(str(path)).pages)]
	if suffix==".docx":
		document = DocxDocument(str(path))
		return  [(None, "\n".join(paragraph.text for paragraph in document.paragraphs))]
	else:
		txtPath = Path(str(path))
		return [(None, txtPath.read_text(encoding="utf-8"))]

async def ingest_upload(
	session: Session,
    upload: UploadFile,
    topic: str | None = None,
    effective_date: date | None = None,)->PolicyDocument:
	settings=get_settings()
	fileName = upload.filename
	# 校验一下文件的后缀
	suffix = Path(fileName).suffix.lower()
	if suffix not in ALLOWED_EXTENSIONS:
		raise ValueError("仅支持 PDF、DOCX、TXT 文件")
	# 校验一下文件的大小
	content = await upload.read()
	if len(content) > settings.max_upload_mb*1024*1024:
		raise ValueError("文件大小超出限制")
	settings.upload_path.mkdir(parents=True,exist_ok=True)


	#将数据保存到数据库里
	document = PolicyDocument(
		filename=upload.filename or f"policy{suffix}",
		stored_path="",
		content_type=upload.content_type or "application/octet-stream",
		topic=topic,
		effective_date=effective_date,
		status=DocumentStatus.indexing,
	)
	session.add(document)
	# 获取数据库uuid
	session.flush()

	# uploadPath 绝对不是一个字符串，而是一个Path 对象
	uploadPath = settings.upload_path / f"{document.id}{suffix}"
	uploadPath.write_bytes(content)

	document.stored_path = str(uploadPath)
	session.commit()
	try:
		chunk_rows:list[DocumentChunk]=[]
		ordinal=0
		for page,text in extract_pages(uploadPath):
			drafts=split_policy_text(text,page=page)
			local_rows:dict[int,DocumentChunk]={}
			for draft_index,draft in enumerate(drafts):
				row=DocumentChunk(
					document_id=document.id,
					ordinal=ordinal,
					section=draft.section,
					page=draft.page,
					content=draft.content,
					is_parent=draft.is_parent,
					token_count=len(draft.content),
					metadata_json=draft.metadata
				)
				session.add(row)
				#这个必须flush，否则，后面没办法获取row对应的id值
				session.flush()
				# 此处是一个非常巧妙的设计，它使用到了我们第六章的内容
				# draft 是一个页面中 被切分后的父块或者子块，如果是子块，那么它的parent_index 绝对不是空的
				local_rows[draft_index]=row
				if draft.parent_index is not None:
				# 由于这个local_rows 中存放了所有的父块和子块的信息，那么我通过draft中的parent_index，就能获取到它对应的DocumentChunk，这个chunk绝对的是一个父块的chunk，获取它的id 就是数据库中对应的id
					row.parent_id=local_rows[draft.parent_index].id
					chunk_rows.append(row)
				ordinal+=1

			# #改造文档入库服务
			# chunk_rows:list[DocumentChunk]=[]
			# vector_records:list[DocumentChunk]=[]
			# if not drafts.is_parent:
			# 	vector_records.append(row)


		child_chunks=[chunk for chunk in chunk_rows if not chunk.is_parent]
		chunk_num=len(child_chunks)
		# 将这些子块全部向量化然后保存在向量数据库中
		vectorService=VectorStoreService()
		# async方法中，如果需要异步方法，要进行await
		await vectorService.add_chunks(document,child_chunks)


		document.chunk_count=chunk_num
		document.status=DocumentStatus.ready
		document.error_message=None
		session.commit()
		session.refresh(document)
		return document
	except Exception as exc:
		document.status=DocumentStatus.failed
		document.error_message=str(exc)[:2000]
		session.commit()
		raise
#删除文档时先删除milvus向量，在删除mysql记录和本地文件
async def delete_document(session:Session,document:PolicyDocument):
	await VectorStoreService().delete_document(document.id)

	def sync_delete():
		path=Path(document.stored_path)
		session.delete(document)
		session.commit()
		if path.exists():
			path.unlink()
	await asyncio.to_thread(sync_delete)
# 增加重建索引方法
async def rebuild_index(session:Session)->int:
	result=session.execute(
		select(DocumentChunk,PolicyDocument)
		.join(PolicyDocument,DocumentChunk.document_id==PolicyDocument.id)
		.where(DocumentChunk.is_parent.is_(False))
	)
	rows=list(result.all())
	store=VectorStoreService()
	await store.reset()
	grouped:dict[str,tuple[PolicyDocument,list[DocumentChunk]]]={}
	for chunk,document in rows:
		grouped.setdefault(document.id,(document,[]))[1].append(chunk)
	for document,chunks in grouped.values():
		await store.add_chunks(document,chunks)
		document.index_version+=1
	session.commit()
	return len(rows)









