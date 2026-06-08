import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models.schemas import AnnotationCreate, AnnotationResponse
from database.connection import get_db
from database import crud
from database.models import AnnotationRecord, UserRecord
from services.auth_service import get_current_user

router = APIRouter()


@router.post("/", response_model=AnnotationResponse, status_code=201)
async def create_annotation(
    body: AnnotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
):
    record = AnnotationRecord(
        id=str(uuid.uuid4()),
        comparison_id=body.comparison_id,
        change_id=body.change_id,
        change_type=body.change_type or "semantic",
        author=body.author or current_user.full_name or current_user.username,
        text=body.text.strip(),
        resolved=0,
    )
    saved = await crud.create_annotation(db, record)
    return _to_response(saved)


@router.get("/{comparison_id}", response_model=list[AnnotationResponse])
async def get_annotations(
    comparison_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
):
    records = await crud.get_annotations(db, comparison_id)
    return [_to_response(r) for r in records]


@router.patch("/{annotation_id}/resolve", response_model=AnnotationResponse)
async def resolve_annotation(
    annotation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
):
    ann = await crud.resolve_annotation(db, annotation_id)
    if not ann:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    return _to_response(ann)


@router.delete("/{annotation_id}")
async def delete_annotation(
    annotation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
):
    deleted = await crud.delete_annotation(db, annotation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    return {"deleted": annotation_id}


def _to_response(r: AnnotationRecord) -> AnnotationResponse:
    return AnnotationResponse(
        id=r.id,
        comparison_id=r.comparison_id,
        change_id=r.change_id,
        change_type=r.change_type,
        author=r.author,
        text=r.text,
        resolved=bool(r.resolved),
        created_at=r.created_at,
    )
