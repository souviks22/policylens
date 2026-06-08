from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
import re

from database.connection import get_db
from database.models import UserRecord
from database import crud
from models.schemas import ComparisonResult
from services.export_pdf import generate_pdf
from services.export_docx import generate_docx
from services.auth_service import get_current_user
from routers.comparison import _result_cache

router = APIRouter()


async def _load_result(comparison_id: str, user_id: str, db: AsyncSession) -> ComparisonResult:
    if comparison_id in _result_cache:
        record = await crud.get_comparison(db, comparison_id)
        if record and record.user_id and record.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not your comparison")
        return _result_cache[comparison_id]

    record = await crud.get_comparison(db, comparison_id)
    if not record:
        raise HTTPException(status_code=404, detail="Comparison not found")
    if record.user_id and record.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your comparison")

    result = ComparisonResult.model_validate_json(record.result_json)
    _result_cache[comparison_id] = result
    return result


@router.get("/{comparison_id}/pdf")
async def export_pdf(
    comparison_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user)):
    result = await _load_result(comparison_id, current_user.id, db)
    try:
        pdf_bytes = generate_pdf(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    filename = _safe_filename(result.doc1_name, result.doc2_name) + ".pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{comparison_id}/docx")
async def export_docx(
    comparison_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user)
):
    result = await _load_result(comparison_id, current_user.id, db)
    try:
        docx_bytes = generate_docx(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DOCX generation failed: {exc}")

    filename = _safe_filename(result.doc1_name, result.doc2_name) + ".docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _safe_filename(doc1: str, doc2: str) -> str:
    def clean(s: str) -> str:
        s = re.sub(r"\.pdf$", "", s, flags=re.I)
        return re.sub(r"[^\w\-]", "_", s)[:28]
    return f"comparison_{clean(doc1)}_vs_{clean(doc2)}"
