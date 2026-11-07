import enum
import uuid
from datetime import date, datetime
from sqlalchemy import String, Date, Enum, Text, Integer, func, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base,engine
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey

def new_id()->str:
    return str(uuid.uuid4())
class DocumentStatus(str,enum.Enum):
    pending="pending"    #已创建记录，尚未处理
    ready="ready"       #处理完成，可以用于后续检索
    failed="failed"      #处理失败，查看 error_message
    indexing="indexing"  #正在解析、分块或入库

class TimestampMixin:
    created_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),server_default=func.now()
    )
    updated_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),server_default=func.now(),onupdate=func.now()
    )
class PolicyDocument(TimestampMixin, Base):
    __tablename__ = "policy_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100))
    topic: Mapped[str | None] = mapped_column(String(100), index=True)
    effective_date: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.pending, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    index_version: Mapped[int] = mapped_column(Integer, default=1)
    chunks:Mapped[list['DocumentChunk']]=relationship(
        back_populates="document",cascade="all,delete-orphan"
    )
class DocumentChunk(TimestampMixin, Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("policy_documents.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(255))
    page: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    is_parent: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    document: Mapped[PolicyDocument] = relationship(back_populates="chunks")
class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(255), default="新会话")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
class ChatMessage(TimestampMixin, Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    refused: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    trace: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )
class Citation(TimestampMixin, Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    message_id: Mapped[str] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[str] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(20))
    quote: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float, default=0)

    message: Mapped[ChatMessage] = relationship(back_populates="citations")

class SystemSetting(Base):
    __tablename__ = "system_settings"
    key:Mapped[str]=mapped_column(String(100),primary_key=True)
    value:Mapped[str]=mapped_column(String(500),nullable=False)
class RunStatus(str,enum.Enum):
    pending="pending"
    running="running"
    completed="completed"
    failed="failed"
class EvaluationDataset(TimestampMixin, Base):
    __tablename__ = "evaluation_datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    cases: Mapped[list["EvaluationCase"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )

class EvaluationCase(TimestampMixin, Base):
    __tablename__ = "evaluation_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), index=True
    )
    question: Mapped[str] = mapped_column(Text)
    reference_answer: Mapped[str] = mapped_column(Text)
    expected_chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    question_type: Mapped[str] = mapped_column(String(50), index=True)
    should_refuse: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    dataset: Mapped[EvaluationDataset] = relationship(back_populates="cases")



class EvaluationRun(TimestampMixin, Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus), default=RunStatus.pending, index=True
    )
    rag_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    knowledge_base_version: Mapped[str] = mapped_column(String(50), default="1")
    prompt_version: Mapped[str] = mapped_column(String(50), default="v1")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class EvaluationResult(TimestampMixin, Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True
    )
    case_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_cases.id", ondelete="CASCADE"), index=True
    )
    answer: Mapped[str] = mapped_column(Text)
    refused: Mapped[bool] = mapped_column(Boolean, default=False)
    retrieved_chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    cited_chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    trace: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    judge_score: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    manual_score: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)