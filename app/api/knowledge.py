from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.knowledge import KnowledgeItem, KnowledgeFeedback
from app.services.vector_store import search_knowledge, delete_knowledge, upsert_knowledge
from app.services.enrichment import enrich_knowledge_item, synthesize_category

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    source_type: str
    source_name: str | None
    tags: list[str]
    contributor_id: int | None = None
    support_count: int = 1
    enriched_at: str | None = None
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
        contributor_id=k.contributor_id,
        support_count=k.support_count,
        enriched_at=k.enriched_at.isoformat() if k.enriched_at else None,
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


@router.put("/{knowledge_id}")
async def update_knowledge(
    knowledge_id: int,
    title: str = Body(...),
    content: str = Body(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == knowledge_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    item.title = title
    item.content = content

    if item.chroma_id:
        upsert_knowledge(
            doc_id=item.chroma_id,
            content=f"{title}\n{content}",
            metadata={
                "title": title,
                "category": item.category,
                "source_type": item.source_type,
                "db_id": item.id,
            },
        )

    await db.commit()
    await db.refresh(item)
    return _to_response(item)


@router.post("/{knowledge_id}/enrich")
async def enrich(knowledge_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == knowledge_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    enriched = await enrich_knowledge_item(item.title, item.content, item.category)

    item.title = enriched.get("title", item.title)
    item.content = enriched.get("content", item.content)
    if enriched.get("tags"):
        item.tags = ",".join(enriched["tags"])
    item.enriched_at = datetime.utcnow()

    if item.chroma_id:
        upsert_knowledge(
            doc_id=item.chroma_id,
            content=f"{item.title}\n{item.content}",
            metadata={
                "title": item.title,
                "category": item.category,
                "source_type": item.source_type,
                "db_id": item.id,
            },
        )

    await db.commit()
    await db.refresh(item)
    return _to_response(item)


@router.post("/{knowledge_id}/feedback")
async def feedback(
    knowledge_id: int,
    helpful: bool = Body(...),
    comment: str | None = Body(None),
    user_id: int | None = Body(None),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == knowledge_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    fb = KnowledgeFeedback(
        knowledge_id=knowledge_id,
        user_id=user_id,
        helpful=helpful,
        comment=comment,
    )
    db.add(fb)

    if helpful:
        item.support_count = (item.support_count or 0) + 1

    await db.commit()
    return {"saved": True, "support_count": item.support_count}


@router.post("/synthesize")
async def synthesize(
    category: str = Body(...),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(KnowledgeItem).where(KnowledgeItem.category == category).order_by(
        KnowledgeItem.support_count.desc(), KnowledgeItem.created_at.desc()
    ).limit(20)
    result = await db.execute(stmt)
    items = result.scalars().all()

    if not items:
        raise HTTPException(status_code=404, detail="このカテゴリにナレッジがありません")

    items_dicts = [{"title": k.title, "content": k.content} for k in items]
    synthesis = await synthesize_category(category, items_dicts)
    return {"category": category, "synthesis": synthesis, "item_count": len(items)}
