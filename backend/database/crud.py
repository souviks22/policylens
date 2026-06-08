import json
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc
from database.models import (
    DocumentRecord, ComparisonRecord,
    AnnotationRecord, SectionEmbeddingRecord,
)


# ── Documents ──────────────────────────────────────────────────────────────────

async def save_document(db: AsyncSession, doc_data: dict) -> DocumentRecord:
    record = DocumentRecord(
        id=doc_data["file_id"],
        filename=doc_data["filename"],
        text=doc_data["text"],
        pages=doc_data["pages"],
        word_count=doc_data["word_count"],
        char_count=len(doc_data["text"]),
        sections=doc_data.get("sections", []),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_document(db: AsyncSession, doc_id: str) -> Optional[DocumentRecord]:
    result = await db.execute(select(DocumentRecord).where(DocumentRecord.id == doc_id))
    return result.scalar_one_or_none()


# ── Comparisons ─────────────────────────────────────────────────────────────────

async def save_comparison(
    db: AsyncSession,
    comparison_id: str,
    doc1_id: str,
    doc2_id: str,
    result_obj,
    section_analysis_obj,
    structural_similarity: float,
    user_id: Optional[str] = None,
) -> ComparisonRecord:
    record = ComparisonRecord(
        id=comparison_id,
        user_id=user_id,
        doc1_id=doc1_id,
        doc2_id=doc2_id,
        result_json=result_obj.model_dump_json(),
        section_analysis_json=section_analysis_obj.model_dump_json() if section_analysis_obj else None,
        total_changes=result_obj.summary.total_changes,
        additions=result_obj.summary.additions,
        deletions=result_obj.summary.deletions,
        modifications=result_obj.summary.modifications,
        overall_impact=result_obj.summary.overall_impact_level.value,
        structural_similarity=structural_similarity,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_comparison(db: AsyncSession, comparison_id: str) -> Optional[ComparisonRecord]:
    result = await db.execute(
        select(ComparisonRecord).where(ComparisonRecord.id == comparison_id)
    )
    return result.scalar_one_or_none()


async def list_comparisons(
    db: AsyncSession,
    user_id: str,
    limit: int = 100,
) -> List[ComparisonRecord]:
    """Return comparisons owned by this user, newest first."""
    result = await db.execute(
        select(ComparisonRecord)
        .where(ComparisonRecord.user_id == user_id)
        .order_by(desc(ComparisonRecord.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def delete_comparison(
    db: AsyncSession,
    comparison_id: str,
    user_id: str,
) -> bool:
    """Delete only if it belongs to this user."""
    result = await db.execute(
        delete(ComparisonRecord).where(
            ComparisonRecord.id == comparison_id,
            ComparisonRecord.user_id == user_id,
        )
    )
    await db.commit()
    return result.rowcount > 0


# ── Annotations ─────────────────────────────────────────────────────────────────

async def create_annotation(db: AsyncSession, record: AnnotationRecord) -> AnnotationRecord:
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_annotations(db: AsyncSession, comparison_id: str) -> List[AnnotationRecord]:
    result = await db.execute(
        select(AnnotationRecord)
        .where(AnnotationRecord.comparison_id == comparison_id)
        .order_by(AnnotationRecord.created_at)
    )
    return list(result.scalars().all())


async def resolve_annotation(
    db: AsyncSession, annotation_id: str
) -> Optional[AnnotationRecord]:
    result = await db.execute(
        select(AnnotationRecord).where(AnnotationRecord.id == annotation_id)
    )
    ann = result.scalar_one_or_none()
    if ann:
        ann.resolved = 1
        await db.commit()
        await db.refresh(ann)
    return ann


async def delete_annotation(db: AsyncSession, annotation_id: str) -> bool:
    result = await db.execute(
        delete(AnnotationRecord).where(AnnotationRecord.id == annotation_id)
    )
    await db.commit()
    return result.rowcount > 0
