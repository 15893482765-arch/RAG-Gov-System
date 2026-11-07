import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import EvaluationCase, EvaluationDataset, EvaluationRun
from app.schemas import DatasetCreate, RunCreate
from app.services.evaluation_service import execute_evaluation_run

router=APIRouter(prefix="/evaluation",tags=['evaluation'])
@router.get("/datasets",summary="查询数据集以及每个数据中包含用例数")
async def list_datasets(session:Session=Depends(get_session)):
    count_query=(
        select(EvaluationCase.dataset_id,func.count(EvaluationCase.id).label("count"))
        .group_by(EvaluationCase.dataset_id)
        .subquery()
    )
    rows=(
        session.execute(
            select(EvaluationDataset,func.coalesce(count_query.c.count,0))
            .outerjoin(count_query,count_query.c.dataset_id==EvaluationDataset.id)
            .order_by(EvaluationDataset.created_at.desc())
        )
    ).all()
    return [
        {
            "id":dataset.id,
            "name":dataset.name,
            "description":dataset.description,
            "case_count":count,
            "created_at":dataset.created_at
         }
        for dataset,count in rows
    ]

@router.get("/runs",summary="查看评估运行情况")
async def list_runs(session:Session=Depends(get_session)):
    runs=session.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).all()
    runs_list=[]
    for row in runs:
        runs_list.append({
            "id":row.id,
            "name":row.name,
            "dataset_id":row.dataset_id,
            "status":row.status,
            "metrics":row.metrics,
            "rag_config":row.rag_config,
            "created_at":row.created_at
        })
    return runs_list

async def _create_dataset(session:Session,payload:DatasetCreate):
    dataset=EvaluationDataset(name=payload.name,description=payload.description)
    session.add(dataset)
    session.flush()
    for case in payload.cases:
        session.add(
            EvaluationCase(
                dataset_id=dataset.id,
                question=case.question,
                reference_answer=case.reference_answer,
                expected_chunk_ids=case.expected_chunk_ids,
                question_type=case.question_type,
                should_refuse=case.should_refuse,
                metadata_json=case.metadata,
            )
        )
    session.commit()
    return {"id":dataset.id,"name":dataset.name,"case_count":len(payload.cases)}
@router.post("/datasets")
async def create_dataset(
        payload:DatasetCreate,session:Session=Depends(get_session)
):
    return await _create_dataset(session,payload)
@router.post("/runs")
async def start_run(payload:RunCreate,session:Session=Depends(get_session)):
    # 先保存run
    # 判断数据集是否存在
    dataset_id = payload.dataset_id
    dataset=session.get(EvaluationDataset,dataset_id)
    if not dataset:
        raise HTTPException(status_code=404,detail="测试集不存在")
    # 保存run对象
    run =EvaluationRun(
        dataset_id=dataset_id,
        name=payload.name,
        # rag_config 的意思是本次运行时，页面上选择的一些配置参数
        rag_config=payload.model_dump(exclude={"dataset_id","name"}),

    )
    session.add(run)
    session.flush()
    run_id=run.id
    session.commit()
    # 真正执行的评估的代码
    asyncio.create_task(execute_evaluation_run(run_id))
    return {"id":run.id,"status":run.status}












