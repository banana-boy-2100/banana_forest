from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.knowledge import Playbook
from app.services.playbook_gen import generate_playbook, get_realtime_suggestion

router = APIRouter(prefix="/playbook", tags=["playbook"])


class GeneratePlaybookRequest(BaseModel):
    scenario: str
    title: str | None = None


class RealtimeSuggestionRequest(BaseModel):
    situation: str


@router.post("/generate")
async def generate(req: GeneratePlaybookRequest, db: AsyncSession = Depends(get_db)):
    content = await generate_playbook(req.scenario)
    title = req.title or f"プレイブック: {req.scenario[:50]}"

    playbook = Playbook(title=title, scenario=req.scenario, content=content)
    db.add(playbook)
    await db.commit()
    await db.refresh(playbook)

    return {"id": playbook.id, "title": title, "content": content}


@router.post("/realtime")
async def realtime_suggestion(req: RealtimeSuggestionRequest):
    suggestion = await get_realtime_suggestion(req.situation)
    return {"suggestion": suggestion}


@router.get("/list")
async def list_playbooks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Playbook).order_by(Playbook.created_at.desc())
    )
    playbooks = result.scalars().all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "scenario": p.scenario,
            "created_at": p.created_at.isoformat(),
        }
        for p in playbooks
    ]


@router.get("/{playbook_id}")
async def get_playbook(playbook_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Playbook).where(Playbook.id == playbook_id))
    playbook = result.scalar_one_or_none()
    if not playbook:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": playbook.id,
        "title": playbook.title,
        "scenario": playbook.scenario,
        "content": playbook.content,
        "created_at": playbook.created_at.isoformat(),
    }
