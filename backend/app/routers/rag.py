"""
RAG document management endpoints.
Upload PDF/TXT/DOCX files to build the knowledge base.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db_models import Document
from app.models.schemas import DocumentOut
from app.rag.engine import RAGEngine

router = APIRouter(prefix="/api/rag", tags=["rag"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("/app/docs_upload")
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".doc"}


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document to the knowledge base."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {sorted(ALLOWED_EXTENSIONS)}")

    doc_id = str(uuid.uuid4())
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    save_path = UPLOAD_DIR / f"{doc_id}{ext}"

    content = await file.read()
    async with aiofiles.open(save_path, "wb") as f:
        await f.write(content)

    doc = Document(
        id=uuid.UUID(doc_id),
        filename=file.filename or "unknown",
        file_type=ext.lstrip("."),
        status="processing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    try:
        engine = RAGEngine.get()
        num_chunks = engine.ingest_file(str(save_path), doc_id)
        doc.num_chunks = num_chunks
        doc.status = "indexed"
    except Exception as e:
        logger.error("RAG ingestion error: %s", e)
        doc.status = "error"
        doc.error_message = str(e)

    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all uploaded documents."""
    result = await db.execute(select(Document).order_by(Document.uploaded_at.desc()))
    return result.scalars().all()


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Remove a document record."""
    result = await db.execute(select(Document).where(Document.id == uuid.UUID(doc_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    await db.delete(doc)
    await db.commit()
    return {"deleted": doc_id}


@router.post("/query")
async def query_knowledge_base(body: dict):
    """Test RAG retrieval directly."""
    query = body.get("query", "")
    if not query:
        raise HTTPException(400, "query is required")
    engine = RAGEngine.get()
    results = engine.retrieve(query, top_k=body.get("top_k", 5))
    return {"results": results}
