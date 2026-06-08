import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import UserRecord
from services.auth_service import (
    hash_password, create_access_token,
    authenticate_user, get_user_by_username, get_current_user,
)

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username:  str = Field(..., min_length=3, max_length=40)
    password:  str = Field(..., min_length=6)
    full_name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    full_name: Optional[str]


class UserResponse(BaseModel):
    id: str
    username: str
    full_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_username(db, body.username.strip().lower())
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    user = UserRecord(
        id=str(uuid.uuid4()),
        username=body.username.strip().lower(),
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        is_active=1,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.username)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(db, form.username.strip().lower(), form.password)
    token = create_access_token(user.username)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: UserRecord = Depends(get_current_user)):
    return current_user
