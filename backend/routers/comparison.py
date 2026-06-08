import uuid
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from models.schemas import (
    ComparisonResult, DocumentStats, SectionAnalysis,
    SectionMatch, ComparisonListItem,
)
from services.text_diff import TextDiffService
from services.semantic_analyzer import SemanticAnalyzer
from services.embeddings import EmbeddingService
from services.section_aligner import SectionAligner
from services.auth_service import get_current_user
from routers.documents import get_document_data
from database.connection import get_db
from database.models import UserRecord
from database import crud
from config import get_settings
import asyncio

router = APIRouter()
diff_service = TextDiffService()

# In-memory cache to avoid deserialising JSON on every /api/comparison/{id} call
_result_cache: dict[str, ComparisonResult] = {}
_analysis_cache: dict[str, SectionAnalysis] = {}


class CompareRequest(BaseModel):
    doc1_id: str
    doc2_id: str


@router.post("/analyze", response_model=ComparisonResult)
async def analyze_documents(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
):
    settings = get_settings()
    doc1 = await get_document_data(request.doc1_id, db)
    doc2 = await get_document_data(request.doc2_id, db)

    analyzer = SemanticAnalyzer(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key, 
        model=settings.openai_model,
    )
    emb_svc   = EmbeddingService(
        base_url=settings.openai_embedding_base_url,
        api_key=settings.openai_embedding_api_key,
        model=settings.openai_embedding_model,
    )
    aligner   = SectionAligner(embedding_service=emb_svc)

    # ── Step 1: Text diff ───────────────────────────────────────────────────────
    diff_chunks = await asyncio.get_event_loop().run_in_executor(
        None, diff_service.compute_paragraph_diff, doc1["text"], doc2["text"]
    )
    similarity = diff_service.get_similarity_ratio(doc1["text"], doc2["text"])

    # ── Step 2: Semantic analysis ───────────────────────────────
    semantic_changes = await analyzer.analyze_changes(
        diff_chunks=diff_chunks,
        doc1_text=doc1["text"],
        doc2_text=doc2["text"],
        doc1_name=doc1["filename"],
        doc2_name=doc2["filename"],
    )

    # ── Step 3: Executive summary ───────────────────────────────────────────────
    summary = await analyzer.generate_executive_summary(
        semantic_changes=semantic_changes,
        doc1_name=doc1["filename"],
        doc2_name=doc2["filename"],
        similarity_ratio=similarity,
    )

    # ── Step 4 (Phase 2): Section alignment via embeddings ──────────────────────
    section_alignment = await aligner.align(doc1["text"], doc2["text"])

    section_analysis = SectionAnalysis(
        matches=[
            SectionMatch(
                id=m.id,
                doc1_section=m.doc1_section,
                doc2_section=m.doc2_section,
                doc1_content=m.doc1_content,
                doc2_content=m.doc2_content,
                similarity_score=m.similarity_score,
                match_type=m.match_type,
                doc1_index=m.doc1_index,
                doc2_index=m.doc2_index,
            )
            for m in section_alignment.matches
        ],
        similarity_matrix=section_alignment.similarity_matrix,
        doc1_section_labels=section_alignment.doc1_section_labels,
        doc2_section_labels=section_alignment.doc2_section_labels,
        overall_structural_similarity=section_alignment.overall_structural_similarity,
        semantic_clone_pairs=[list(p) for p in section_alignment.semantic_clone_pairs],
    )

    comparison_id = str(uuid.uuid4())

    result = ComparisonResult(
        comparison_id=comparison_id,
        doc1_name=doc1["filename"],
        doc2_name=doc2["filename"],
        doc1_stats=DocumentStats(
            total_pages=doc1["pages"],
            total_words=doc1["word_count"],
            total_characters=len(doc1["text"]),
            sections_detected=doc1["sections"],
        ),
        doc2_stats=DocumentStats(
            total_pages=doc2["pages"],
            total_words=doc2["word_count"],
            total_characters=len(doc2["text"]),
            sections_detected=doc2["sections"],
        ),
        diff_chunks=diff_chunks,
        semantic_changes=semantic_changes,
        summary=summary,
        doc1_content=doc1["text"],
        doc2_content=doc2["text"],
        doc1_sections=doc1["sections"],
        doc2_sections=doc2["sections"],
        section_analysis=section_analysis,
        text_similarity_ratio=similarity,
    )

    # ── Persist ─────────────────────────────────────────────────────────────────
    try:
        await crud.save_comparison(
            db=db,
            comparison_id=comparison_id,
            doc1_id=request.doc1_id,
            doc2_id=request.doc2_id,
            result_obj=result,
            section_analysis_obj=section_analysis,
            structural_similarity=section_alignment.overall_structural_similarity,
            user_id=current_user.id,
        )
    except Exception:
        pass  # don't fail the response if DB write fails

    _result_cache[comparison_id] = result
    _analysis_cache[comparison_id] = section_analysis
    return result


@router.get("/history", response_model=list[ComparisonListItem])
async def list_history(
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user)
):
    records = await crud.list_comparisons(db, user_id=current_user.id)
    items = []
    for r in records:
        doc1_name = r.doc1.filename if r.doc1 else "Unknown"
        doc2_name = r.doc2.filename if r.doc2 else "Unknown"
        items.append(ComparisonListItem(
            id=r.id,
            doc1_name=doc1_name,
            doc2_name=doc2_name,
            total_changes=r.total_changes,
            additions=r.additions,
            deletions=r.deletions,
            modifications=r.modifications,
            overall_impact=r.overall_impact,
            structural_similarity=r.structural_similarity,
            created_at=r.created_at,
        ))
    return items


@router.get("/{comparison_id}", response_model=ComparisonResult)
async def get_comparison(
    comparison_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
):
    if comparison_id in _result_cache:
        cached = _result_cache[comparison_id]
        # Verify ownership via DB
        record = await crud.get_comparison(db, comparison_id)
        if record and record.user_id and record.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your comparison")
        return cached

    record = await crud.get_comparison(db, comparison_id)
    if not record:
        raise HTTPException(status_code=404, detail="Comparison not found.")
    if record.user_id and record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your comparison")

    result = ComparisonResult.model_validate_json(record.result_json)
    _result_cache[comparison_id] = result
    return result


@router.delete("/{comparison_id}")
async def delete_comparison(
    comparison_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
):
    deleted = await crud.delete_comparison(db, comparison_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Comparison not found.")
    _result_cache.pop(comparison_id, None)
    _analysis_cache.pop(comparison_id, None)
    return {"deleted": comparison_id}
