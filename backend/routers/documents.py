import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models.schemas import UploadResponse
from services.pdf_extractor import PDFExtractor
from services.auth_service import get_current_user
from database.connection import get_db
from database.models import UserRecord
from database import crud
import asyncio

router = APIRouter()
extractor = PDFExtractor()

# In-memory fallback for documents not yet committed (avoids extra DB round-trip)
_doc_cache: dict[str, dict] = {}


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum 50 MB.")

    try:
        text, pages, sections = await asyncio.get_event_loop().run_in_executor(
            None, extractor.extract_text, content
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse PDF: {e}")

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted. The PDF may be image-only.",
        )

    file_id = str(uuid.uuid4())
    word_count = extractor.get_word_count(text)

    doc_data = {
        "file_id": file_id,
        "filename": file.filename,
        "text": text,
        "pages": pages,
        "sections": sections,
        "word_count": word_count,
    }

    # Persist to DB (non-blocking)
    try:
        await crud.save_document(db, doc_data)
    except Exception:
        pass  # fall through to cache

    _doc_cache[file_id] = doc_data

    return UploadResponse(
        file_id=file_id,
        filename=file.filename,
        pages=pages,
        word_count=word_count,
        status="processed",
    )


async def get_document_data(file_id: str, db: AsyncSession) -> dict:
    """Retrieve document from cache or DB."""
    if file_id in _doc_cache:
        return _doc_cache[file_id]

    record = await crud.get_document(db, file_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Document '{file_id}' not found. Please re-upload.")

    data = {
        "file_id": record.id,
        "filename": record.filename,
        "text": record.text,
        "pages": record.pages,
        "sections": record.sections or [],
        "word_count": record.word_count,
    }
    _doc_cache[file_id] = data
    return data
