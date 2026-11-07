from datetime import date,datetime
from typing import Literal, Any

from pydantic import BaseModel,ConfigDict,Field
class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
class ORMModel(APIModel):
    model_config = ConfigDict(from_attributes=True,extra="forbid")
class DocumentOut(ORMModel):
    id:str
    filename:str
    content_type:str
    topic:str|None
    effective_date:date|None
    status:str
    error_message:str|None
    chunk_count:int
    index_version:int
    created_at:datetime
class RetrievalFilters(APIModel):
    document_ids:list[str]= Field(default_factory=list)
    topic: str | None = None
    effective_before: date | None = None

class ChatRequest(APIModel):
    question: str = Field(min_length=2, max_length=2000)
    conversation_id: str | None = None
    filters: RetrievalFilters = Field(default_factory=RetrievalFilters)
    debug: bool = False

# 用于接收前端传递的参数
class ModelConfigIn(APIModel):
    provider:Literal["ollama","deepseek"]
    model:str|None=None
    base_url:str|None=None

# 用于后端传递给前端的数据
class ModelConfigOut(APIModel):
    provider:str
    model:str
    base_url:str
    configured:bool
class EvaluationCaseIn(APIModel):
    question: str
    reference_answer: str = ""
    expected_chunk_ids: list[str] = Field(default_factory=list)
    question_type: str = "direct"
    should_refuse: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

class DatasetCreate(APIModel):
    name: str
    description: str | None = None
    cases: list[EvaluationCaseIn] = Field(default_factory=list)
class RunCreate(APIModel ):
    dataset_id: str
    name: str
    mode: Literal["vector", "hybrid", "hybrid_rerank", "full"] = "full"
    top_k: int = Field(default=8, ge=1, le=50)
    rerank_top_k: int = Field(default=4, ge=1, le=20)
    min_evidence_score: float = Field(default=0.25, ge=0, le=1)
    enable_judge: bool = False
class ManualScoreIn(APIModel):
    faithfulness: float | None = Field(default=None, ge=0, le=1)
    relevance: float | None = Field(default=None, ge=0, le=1)
    factual_accuracy: float | None = Field(default=None, ge=0, le=1)
    notes: str = ""
