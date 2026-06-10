"""
routers/knowledge_base.py

Endpoints for managing the RAG knowledge base:

  POST   /api/kb/upload              Upload a PDF or TXT to global or personal KB
  GET    /api/kb/documents           List KB documents visible to the current user
  DELETE /api/kb/documents/{doc_id}  Delete a KB document
  GET    /api/kb/search              Preview RAG retrieval for a given query
  GET    /api/kb/stats               Chunk counts for global + personal collections
"""

import uuid
import io
from typing import Optional

import aiofiles
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.connection import get_db
from database.models import UserRecord
from database import crud
from models.schemas import KbUploadResponse, KbDocumentResponse, KbSearchResult
from services.auth_service import get_current_user
from services.rag_service import get_rag_service

router = APIRouter()


# ── Text extraction helpers ───────────────────────────────────────────────────────

async def _extract_text(content: bytes, filename: str) -> str:
    """Extract plain text from PDF or TXT bytes."""
    fname_lower = filename.lower()

    if fname_lower.endswith(".pdf"):
        import pdfplumber, asyncio
        def _read():
            text_parts = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
            return "\n\n".join(text_parts)

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, _read)
        return text

    elif fname_lower.endswith((".txt", ".md")):
        return content.decode("utf-8", errors="replace")

    else:
        raise HTTPException(
            status_code=415,
            detail="Only PDF, TXT, and MD files are accepted for the knowledge base.",
        )


# ── Routes ────────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=KbUploadResponse, status_code=201)
async def upload_kb_document(
    file: UploadFile = File(...),
    scope: str = Form("global"),          # "global" | "personal"
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
):
    """
    Upload a PDF or TXT document to the knowledge base.

    - **scope=global** adds it to the shared regulatory KB (visible to all users).
    - **scope=personal** adds it to the current user's private company KB.
    """
    settings = get_settings()

    if scope not in ("global", "personal"):
        raise HTTPException(status_code=400, detail="scope must be 'global' or 'personal'")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    content = await file.read()
    if len(content) > 30 * 1024 * 1024:  # 30 MB cap for KB docs
        raise HTTPException(status_code=413, detail="File too large. Maximum 30 MB.")

    # Extract text
    text = await _extract_text(content, file.filename)
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted from the file. "
                   "Ensure PDFs have a text layer (not scanned images).",
        )

    doc_id = str(uuid.uuid4())
    user_id_for_personal = current_user.id if scope == "personal" else None

    # Index into ChromaDB
    rag = get_rag_service()
    chunk_count = await rag.add_document(
        doc_id=doc_id,
        filename=file.filename,
        text=text,
        scope=scope,
        user_id=current_user.id if scope == "personal" else None,
    )

    if chunk_count == 0:
        raise HTTPException(status_code=422, detail="Document produced no indexable chunks.")

    # Save metadata to SQL
    await crud.save_kb_document(
        db=db,
        doc_id=doc_id,
        filename=file.filename,
        scope=scope,
        uploaded_by=current_user.id,
        user_id=user_id_for_personal,
        chunk_count=chunk_count,
        char_count=len(text),
        description=description,
    )

    return KbUploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        scope=scope,
        chunk_count=chunk_count,
        char_count=len(text),
    )


@router.get("/documents", response_model=list[KbDocumentResponse])
async def list_kb_documents(
    scope: str = Query("all"),   # "all" | "global" | "personal"
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
):
    """
    List knowledge base documents.
    - scope=all      → global + this user's personal docs
    - scope=global   → only shared regulatory docs
    - scope=personal → only this user's company docs
    """
    records = await crud.list_kb_documents(db, scope=scope, user_id=current_user.id)
    return [
        KbDocumentResponse(
            id=r.id,
            filename=r.filename,
            description=r.description,
            scope=r.scope,
            uploaded_by=r.uploader.username if r.uploader else "unknown",
            chunk_count=r.chunk_count,
            char_count=r.char_count,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.delete("/documents/{doc_id}")
async def delete_kb_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
):
    """
    Delete a knowledge base document and remove its vectors from ChromaDB.
    Personal docs can only be deleted by their owner.
    Global docs can be deleted by any authenticated user.
    """
    record = await crud.get_kb_document(db, doc_id)
    if not record:
        raise HTTPException(status_code=404, detail="KB document not found.")

    if record.scope == "personal" and record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete another user's personal KB document.")

    # Remove from ChromaDB
    rag = get_rag_service()
    await rag.delete_document(
        doc_id=doc_id,
        scope=record.scope,
        user_id=record.user_id,
    )

    # Remove metadata from SQL
    await crud.delete_kb_document(db, doc_id, requesting_user_id=current_user.id)
    return {"deleted": doc_id}


@router.get("/search", response_model=list[KbSearchResult])
async def search_kb(
    query: str = Query(..., min_length=3),
    n_results: int = Query(5, ge=1, le=20),
    current_user: UserRecord = Depends(get_current_user),
):
    """
    Preview what chunks would be retrieved for a given query.
    Useful for debugging the knowledge base before running a full analysis.
    """
    settings = get_settings()
    rag = get_rag_service()

    hits = await rag.query(
        query_text=query,
        user_id=current_user.id,
        n_results=n_results,
        score_threshold=settings.rag_score_threshold,
    )

    return [
        KbSearchResult(
            doc_id=h["source_doc_id"],
            source_doc_name=h["source_doc_name"],
            scope=h["scope"],
            chunk_index=h["chunk_index"],
            excerpt=h["text"][:400] + ("…" if len(h["text"]) > 400 else ""),
            score=h["score"],
        )
        for h in hits
    ]


@router.get("/stats")
async def kb_stats(
    current_user: UserRecord = Depends(get_current_user),
):
    """Return chunk counts for the global and personal KB collections."""
    rag = get_rag_service()
    stats = await rag.collection_stats(user_id=current_user.id)
    return stats
