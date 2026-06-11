from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import UserRecord
from database import crud
from models.schemas import ComparisonResult
from services.chat_service import ChatService
from services.auth_service import get_current_user
from routers.comparison import _result_cache
from config import get_settings

router = APIRouter()


class ChatMessage(BaseModel):
    role: str     # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


async def _load_result(
    comparison_id: str,
    user_id: str,
    db: AsyncSession,
) -> ComparisonResult:
    """Load comparison result, verifying ownership."""
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


@router.post("/{comparison_id}")
async def chat(
    comparison_id: str,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
):
    """
    Stream a chat response grounded in a specific comparison.
    The client manages conversation history and sends it on every request.
    Nothing is persisted — conversations are volatile by design.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    result = await _load_result(comparison_id, current_user.id, db)

    settings = get_settings()
    svc = ChatService(api_key=settings.openai_api_key, model=settings.openai_model)

    system_prompt = svc.build_system_prompt(result)
    messages      = [{"role": m.role, "content": m.content} for m in request.messages]

    return StreamingResponse(
        svc.stream(system_prompt, messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control":              "no-cache",
            "X-Accel-Buffering":          "no",
            "Access-Control-Allow-Origin": "*",
        },
    )
