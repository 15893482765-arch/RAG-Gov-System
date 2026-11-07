from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import PolicyDocument
from app.schemas import DocumentOut
from app.services.document_service import ingest_upload


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    topic: str | None = Form(default=None),
    effective_date: date | None = Form(default=None),
    session: Session = Depends(get_session),
):
    try:
        return await ingest_upload(session, file, topic, effective_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[DocumentOut])
async def list_documents(session: Session = Depends(get_session)):
    return session.query(PolicyDocument).order_by(PolicyDocument.created_at.desc()).all()