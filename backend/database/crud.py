import json
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc
from database.models import (
    DocumentRecord, ComparisonRecord, AnnotationRecord, KnowledgeBaseDocumentRecord
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


# ── Knowledge Base ──────────────────────────────────────────────────────────────

async def save_kb_document(
    db: AsyncSession,
    doc_id: str,
    filename: str,
    scope: str,
    uploaded_by: str,
    user_id: Optional[str],
    chunk_count: int,
    char_count: int,
    description: Optional[str] = None,
) -> KnowledgeBaseDocumentRecord:
    record = KnowledgeBaseDocumentRecord(
        id=doc_id,
        filename=filename,
        description=description,
        scope=scope,
        uploaded_by=uploaded_by,
        user_id=user_id,
        chunk_count=chunk_count,
        char_count=char_count,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def list_kb_documents(
    db: AsyncSession,
    scope: str = "all",          # "all" | "global" | "personal"
    user_id: Optional[str] = None,
) -> List[KnowledgeBaseDocumentRecord]:
    """
    List KB documents visible to the given user.
    - scope="global"   → only global docs
    - scope="personal" → only this user's personal docs
    - scope="all"      → global docs + this user's personal docs
    """
    if scope == "global":
        stmt = select(KnowledgeBaseDocumentRecord).where(
            KnowledgeBaseDocumentRecord.scope == "global"
        )
    elif scope == "personal" and user_id:
        stmt = select(KnowledgeBaseDocumentRecord).where(
            KnowledgeBaseDocumentRecord.scope == "personal",
            KnowledgeBaseDocumentRecord.user_id == user_id,
        )
    else:
        # all: global + personal for this user
        from sqlalchemy import or_
        stmt = select(KnowledgeBaseDocumentRecord).where(
            or_(
                KnowledgeBaseDocumentRecord.scope == "global",
                (
                    (KnowledgeBaseDocumentRecord.scope == "personal") &
                    (KnowledgeBaseDocumentRecord.user_id == user_id)
                ) if user_id else False,
            )
        )
    stmt = stmt.order_by(desc(KnowledgeBaseDocumentRecord.created_at))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_kb_document(
    db: AsyncSession, doc_id: str
) -> Optional[KnowledgeBaseDocumentRecord]:
    result = await db.execute(
        select(KnowledgeBaseDocumentRecord).where(KnowledgeBaseDocumentRecord.id == doc_id)
    )
    return result.scalar_one_or_none()


async def delete_kb_document(
    db: AsyncSession,
    doc_id: str,
    requesting_user_id: str,
) -> bool:
    """
    Delete a KB document. Global docs can be deleted by anyone (team tool).
    Personal docs only by their owner.
    """
    record = await get_kb_document(db, doc_id)
    if not record:
        return False
    if record.scope == "personal" and record.user_id != requesting_user_id:
        return False

    await db.execute(
        delete(KnowledgeBaseDocumentRecord).where(
            KnowledgeBaseDocumentRecord.id == doc_id
        )
    )
    await db.commit()
    return True
