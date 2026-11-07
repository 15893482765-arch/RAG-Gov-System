import asyncio
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.schemas import RetrievalFilters
from app.services.retrieval import retrieve


def print_evidence(mode: str, result) -> None:
    print(f"模式：{mode}")
    print("是否拒答：", result.refused)
    print("拒答原因：", result.refusal_reason)
    print("候选数量：", len(result.candidates))
    print("证据数量：", len(result.evidence))
    for item in result.evidence:
        metadata = item.get("metadata", {})
        print(
            {
                "chunk_id": item.get("chunk_id"),
                "source": item.get("source"),
                "sources": item.get("sources"),
                "rrf_score": round(float(item.get("rrf_score", 0)), 4),
                "rerank_score": round(float(item.get("rerank_score", 0)), 4),
                "evidence_score": round(float(item.get("evidence_score", 0)), 4),
                "filename": metadata.get("filename"),
                "section": metadata.get("section"),
                "content_preview": item.get("content", "")[:80],
            }
        )
    print()


async def main() -> None:
    # question = "申请青年人才租房补贴流程是什么？"
    question = "数字化补贴申报材料"
    filters = RetrievalFilters()

    with SessionLocal() as session:
        hybrid = await retrieve(
            session=session,
            question=question,
            filters=filters,
            mode="hybrid",
            top_k=6,
            min_score=0.2,
        )
        hybrid_rerank = await retrieve(
            session=session,
            question=question,
            filters=filters,
            mode="hybrid_rerank",
            top_k=6,
            min_score=0.2,
        )
        full = await retrieve(
            session=session,
            question=question,
            filters=filters,
            mode="full",
            top_k=6,
            min_score=0.6,
        )

        vector = await retrieve(
            session=session,
            question=question,
            filters=filters,
            mode="vector",
            top_k=6,
            min_score=0.6,
        )

    print("问题：", question)
    print()
    print_evidence("hybrid", hybrid)
    print_evidence("hybrid_rerank", hybrid_rerank)
    print_evidence("full", full)
    print_evidence("vector", vector)


if __name__ == "__main__":
    asyncio.run(main())