import asyncio
import re
from dataclasses import dataclass
from typing import Any, List

import jieba
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentChunk, PolicyDocument
from app.schemas import RetrievalFilters
from app.services.model_fectory import create_chat_model, invoke_text
from app.services.pipline_untils import reciprocal_rank_fusion, normalize_logit, filter_evidence
from app.services.vector_store import VectorStoreService

# @dataclass
# class RetrievalResult:
#     query:str
#     candidates:list[dict[str,Any]]
#     evidence:list[dict[str,Any]]
#     refused:bool
#     refusal_reason:str|None
#     trace:dict[str,Any]

async def apply_metadata_filters(vector_results, filters):
    if vector_results is None:          # 防御性处理
        return []
    rows = vector_results
    if filters.topic:
        rows = [result for result in rows if result['metadata']['topic'] == filters.topic]
        print("过滤完topic之后的数据", rows)
    if filters.effective_before:
        rows = [result for result in rows if result['metadata']['effective_date'] <= filters.effective_before.isoformat()]
        print("过滤完时间之后的数据", rows)
    return rows                          # 确保所有分支都有返回值
async def expand_parent_context(
    session: Session, evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    parent_ids = {
        item["metadata"].get("parent_id")
        for item in evidence
        if item["metadata"].get("parent_id")
    }
    if not parent_ids:
        return evidence
    #通过sqlalchemy查询父块信息
    chunk_list=session.query(DocumentChunk).filter(DocumentChunk.id.in_(parent_ids)).all()
    # 将这个list 信息保存成 字典   {父块id-> 父块信息}
    parents=dict()
    for chunk in chunk_list:
        parents[chunk.id]=chunk
    print("封装父块信息如下：")
    print(parents)
    # set 集合中存储的都是父id,已经在某个子块中添加过的父块信息，其他子块不需要再添加了
    seen_parents=set()
    # 将每一个包含父块和子块信息的 字典，放入到这个集合中，方便  return 返回
    expanded:list[dict[str,Any]]=[]
    # 循环每一个子块，给子块添加对应的父块信息
    for item in evidence:
        # item 其实就是milvus中的一个子块
        parent_id=item['metadata'].get("parent_id")
        # 根据字典获取父块信息，其实父块信息来自于数据库
        parent=parents.get(parent_id)
        if parent and parent_id not in seen_parents:
            item={
                **item,
                "content":parent.content,
                "metadata":{
                    **item['metadata'],
                    "section":parent.section or item['metadata'].get("section",""),
                    "page":parent.page or item['metadata'].get("page",0),
                    "context_chunk_id":parent_id

                }
            }
            seen_parents.add(parent_id)
            expanded.append(item)
    return expanded


@dataclass
class RetrievalResult:
    query: str
    candidates: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    refused: bool
    refusal_reason: str | None
    trace: dict[str, Any]

async def retrieve(
    session: Session,
    question: str,
    filters: RetrievalFilters,
    top_k: int = 8,
    evidence_top_k:int =4,
    min_score: float = 0.25,
    mode:str="full"
) -> RetrievalResult:
    new_question=await rewrite_query(question)

    # 查询milvus数据
    vector_results =await VectorStoreService().search(
        new_question,
        top_k,
        document_ids=filters.document_ids or None
    )
    # 过滤
    vector_results = await apply_metadata_filters(vector_results, filters)
    # 由于vector_results 里面的 source 默认是文件名，所以想将其修改为 vector
    for item in vector_results:
        item['source']='vector'

    if mode=="vector":
        print("vector_results", vector_results)
        keyword_list:list[dict]=[]
    else:
        # 向量检索结果 + bm25检索结果 综合得分高的 作为候选数据
        keyword_list=await keyword_search(session,new_question,top_k*2,filters)
        print("keyword_list",keyword_list)
    fused=[vector_results[:top_k],keyword_list]
    rrf_list=reciprocal_rank_fusion(fused)
    # candidates 获取的是通过向量数据库召回的数据
    # 获取候选数据
    candidates = rrf_list[:top_k]
    #print(candidates)
    # 证据，所谓的证据就是候选数据打分比较高的数据
    evidence = []
    for item in candidates:
        #分数要在0和1之间
        #score=float(item.get('score',0))
        score = max(0.0, min(1.0, float(item.get("score", 0))))
        if score >= min_score:
            # 这个分数目前来讲没有用
            item["evidence_score"] = score
            evidence.append(item)
    #print("打印证据")
    #print(evidence)
    # 根据子块数据获取parent_id 从而去数据库mysql查询父块信息

    evidence = await expand_parent_context(session, evidence)

    # evidence 就是包含了父块信息的子块内容
    print("---------------打印最终的证据------------------")
    #print(evidence)
    evidence=evidence[:max(evidence_top_k,top_k)]
    if mode in ["hybrid_rerank","full"]:
        evidence=await rerank(new_question,evidence,evidence_top_k)
    else:
        evidence=evidence[:evidence_top_k]
    # 给每一个证据重新赋予一个得分evidence_score
    """
      假如证据中有rerank_score， evidence_score=rerank_score
      假如证据中有score，        evidence_score=score
      假如证据中有rrf_score      evidence_score=rrf_score*30
      接着  对 evidence_score 进行归一化处理
    """
    for item in evidence:
        normalized=item.get("rerank_score")
        if normalized is None:
            normalized=item.get("score",item.get("rrf_score",0)*30)
        item['evidence_score']=max(0.0,min(1.0,float(normalized)))
    #假如是full模型，将证据中的比较低的得分再次过滤一下
    #第一次过滤是基于旧分数（RRF/向量）的粗筛，为了减少计算量；
    # 第二次过滤是在获得最精确的分数（Rerank Score） 之后，进行的精筛，
    # 目的是保证喂给最终大模型的上下文全部是高质量、高相关的，剔除扩展上下文时带来的“凑数”内容。
    if mode=="full":
        evidence=filter_evidence(evidence,min_score)

    trace = {
        "original_query": new_question,
        "vector_results": vector_results,
        "final_evidence": evidence,
    }

    refused=True if len(evidence)==0 else False
    # 添加解决错误拒绝
    refusal_reason = "没有查询到合适的数据" if refused else None
    if not refused:
        max_evidence_score = max(
            (item.get("evidence_score", 0.0) for item in evidence),
            default=0.0
        )
        ABS_SCORE_THRESHOLD = 0.6  # 可调整
        if max_evidence_score < ABS_SCORE_THRESHOLD:
            refused = True
            refusal_reason = f"证据相关性不足，最高分 {max_evidence_score:.2f} 低于阈值 {ABS_SCORE_THRESHOLD}"


    return  RetrievalResult(
        query=new_question,
        candidates=candidates,
        evidence=evidence,
        refused=refused,
        refusal_reason=refusal_reason,
        trace=trace
    )


STOP_WORDS={"的", "了", "是", "在", "和", "有", "就", "都", "而", "及"}
valid_pat = re.compile(r"^([\u4e00-\u9fff]+|[A-Za-z0-9]+)$")
def tokenize_chinese(text:str)->list[str]:
    """
      中文文本分词
      :param text: 原始输入文本
      :return: 过滤后的token列表
      """
    text_low=text.lower()
    words = jieba.lcut_for_search(text_low)
    word_list=[]
    for word in words:
        if word not in STOP_WORDS and valid_pat.fullmatch(word) and len(word)>1:
            word_list.append(word)
    return word_list

from rank_bm25 import BM25Okapi



async def keyword_search(
        session:Session,
        query:str,
        top_k:int,
        filters:RetrievalFilters
)->list[dict[str,Any]]:
    statement=(
        select(DocumentChunk,PolicyDocument)
        .join(PolicyDocument,DocumentChunk.document_id==PolicyDocument.id)
        .where(DocumentChunk.is_parent.is_(False))
    )
    if filters.document_ids:
        statement=statement.where(DocumentChunk.document_id.in_(filters.document_ids))
    if filters.topic:
        statement=statement.where(PolicyDocument.topic==filters.topic)
    if filters.effective_before:
        statement=statement.where(PolicyDocument.effective_date<=filters.effective_before)
    rows=list(session.execute(statement).all())
    if not rows:
        return []
    corpus:List[List[str]]=[]
    for chunk in rows:
        print("chunk[0].content",chunk[0].content)
        corpus.append(tokenize_chinese(chunk[0].content))
    print("corpus的长度",len(corpus))
    bm25_model=BM25Okapi(corpus)
    print("query tokens:", tokenize_chinese(query))
    scores=bm25_model.get_scores(tokenize_chinese(query))
    ranks=sorted(enumerate(scores),key=lambda item:item[1],reverse=True)[:top_k]
    print("排名",ranks)
    print("分数",scores)
    result_list=[]
    for index,score in ranks:
        if score>0:
            document_chunk=rows[index][0]
            policy_document=rows[index][1]
            result_list.append({
                "chunk_id": document_chunk.id,
                "content": document_chunk.content,
                "score": float(score),
                "source": "bm25",
                "metadata": {
                    "document_id": policy_document.id,
                    "filename": policy_document.filename,
                    "topic": policy_document.topic or "",
                    "section": document_chunk.section or "",
                    "page": document_chunk.page or 0,
                    "parent_id": document_chunk.parent_id or "",
            },
            })

    return result_list
from functools import lru_cache
from app.config import get_settings
@lru_cache
def get_reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(get_settings().reranker_model,local_files_only=True)


async def rerank(query:str,candidates:list[dict],top_k:int)->list[dict]:
    if not candidates:
        return []
    settings=get_settings()
    if not settings.enable_reranker:
        return candidates[:top_k]
    try:
        scores=await asyncio.to_thread(
            get_reranker().predict,
            [(query,item['content']) for item in candidates],
        )
        print("开始打印分数：",scores)
        for item,score in zip(candidates,scores):
            raw_score=float(score)
            item['rerank_raw_score']=raw_score
            item['rerank_score']=normalize_logit(raw_score)
        return sorted(candidates,key=lambda item:item['rerank_score'],reverse=True)[:top_k]
    except Exception:
        for item in candidates:
            item['rerank_score']=min(1.0,item.get("rrf_score",0)+30)
        return candidates[:top_k]
async def rewrite_query(question:str)->str:
    """把口语化问题改写成更适合检索的查询：失败时退回原问题"""
    prompt=(
        "将下面的政务咨询改写为一个适合知识库检索的简洁中文查询。"
        "不得添加问题中没有的地区、政策或条件，只输出改写结果"
        f"问题：{question}"
    )
    try:
        model=create_chat_model(temperature=0)
        answer,_=await invoke_text(model,prompt)
        return answer.strip()[:500] or question
    except Exception:
        return question









