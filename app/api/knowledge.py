from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.knowledge import KnowledgeItem
from app.services.vector_store import search_knowledge, delete_knowledge

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    source_type: str
    source_name: str | None
    tags: list[str]
    created_at: str


def _to_response(k: KnowledgeItem) -> KnowledgeResponse:
    return KnowledgeResponse(
        id=k.id,
        title=k.title,
        content=k.content,
        category=k.category,
        source_type=k.source_type,
        source_name=k.source_name,
        tags=[t.strip() for t in (k.tags or "").split(",") if t.strip()],
        created_at=k.created_at.isoformat(),
    )


@router.get("/search")
async def search(
    q: str = Query(..., description="検索クエリ"),
    category: str | None = Query(None),
    n: int = Query(10, ge=1, le=50),
):
    where = {"category": category} if category else None
    results = search_knowledge(q, n_results=n, where=where)
    return results


@router.get("/list")
async def list_knowledge(
    category: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(KnowledgeItem).order_by(KnowledgeItem.created_at.desc())
    if category:
        stmt = stmt.where(KnowledgeItem.category == category)
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    items = result.scalars().all()
    return [_to_response(k) for k in items]


@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge(knowledge_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == knowledge_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_response(item)


@router.delete("/{knowledge_id}")
async def delete_knowledge_item(knowledge_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == knowledge_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    if item.chroma_id:
        delete_knowledge(item.chroma_id)

    await db.execute(delete(KnowledgeItem).where(KnowledgeItem.id == knowledge_id))
    await db.commit()
    return {"deleted": True}


@router.get("/stats/summary")
async def get_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    result = await db.execute(
        select(KnowledgeItem.category, func.count(KnowledgeItem.id))
        .group_by(KnowledgeItem.category)
    )
    by_category = {row[0]: row[1] for row in result}

    total_result = await db.execute(select(func.count(KnowledgeItem.id)))
    total = total_result.scalar()

    return {"total": total, "by_category": by_category}
