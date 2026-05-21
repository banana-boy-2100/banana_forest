from __future__ import annotations
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import get_db
from app.models.knowledge import User, KnowledgeItem, TranscriptionRecord

USER_COLORS = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2", "#be185d", "#854d0e"]
router = APIRouter(prefix="/users", tags=["users"])


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


class CreateUserRequest(BaseModel):
    name: str
    display_name: str
    pin: str


class LoginRequest(BaseModel):
    name: str
    pin: str


@router.post("/register")
async def register(req: CreateUserRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.name == req.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="この名前は既に使われています")
    count_result = await db.execute(select(User))
    count = len(count_result.scalars().all())
    color = USER_COLORS[count % len(USER_COLORS)]
    user = User(
        name=req.name,
        display_name=req.display_name,
        pin_hash=hash_pin(req.pin),
        color=color,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "name": user.name, "display_name": user.display_name, "color": user.color}


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.name == req.name))
    user = result.scalar_one_or_none()
    if not user or user.pin_hash != hash_pin(req.pin):
        raise HTTPException(status_code=401, detail="名前またはPINが違います")
    return {"id": user.id, "name": user.name, "display_name": user.display_name, "color": user.color}


@router.get("/list")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    out = []
    for u in users:
        k_result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.contributor_id == u.id))
        k_count = len(k_result.scalars().all())
        t_result = await db.execute(select(TranscriptionRecord).where(TranscriptionRecord.user_id == u.id))
        t_count = len(t_result.scalars().all())
        out.append({
            "id": u.id,
            "name": u.name,
            "display_name": u.display_name,
            "color": u.color,
            "knowledge_count": k_count,
            "transcript_count": t_count,
            "created_at": u.created_at.isoformat(),
        })
    return out
