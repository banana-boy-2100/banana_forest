from __future__ import annotations
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.knowledge import KnowledgeItem, SourceType
from app.services.extractor import (
    extract_knowledge_from_text,
    extract_from_transcript,
    extract_from_chat,
)
from app.services.vector_store import upsert_knowledge

router = APIRouter(prefix="/ingest", tags=["ingestion"])


async def _save_items(
    items: list[dict],
    source_type: str,
    source_name: str,
    db: AsyncSession,
    user_id: int | None = None,
) -> list[int]:
    saved_ids = []
    for item in items:
        knowledge = KnowledgeItem(
            title=item.get("title", ""),
            content=item.get("content", ""),
            category=item.get("category", "other"),
            source_type=source_type,
            source_name=source_name,
            tags=",".join(item.get("tags", [])),
            contributor_id=user_id,
        )
        db.add(knowledge)
        await db.flush()

        chroma_id = f"knowledge_{knowledge.id}"
        upsert_knowledge(
            doc_id=chroma_id,
            content=f"{item['title']}\n{item['content']}",
            metadata={
                "title": item.get("title", ""),
                "category": item.get("category", "other"),
                "source_type": source_type,
                "db_id": knowledge.id,
            },
        )
        knowledge.chroma_id = chroma_id
        saved_ids.append(knowledge.id)

    await db.commit()
    return saved_ids


@router.post("/document")
async def ingest_document(
    file: UploadFile = File(...),
    source_hint: str = Form(default=""),
    user_id: int | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="UTF-8テキストファイルのみ対応しています")

    items = await extract_knowledge_from_text(text, source_hint or file.filename)
    if not items:
        return {"message": "知見を抽出できませんでした", "extracted_count": 0}

    ids = await _save_items(items, SourceType.DOCUMENT, file.filename, db, user_id=user_id)
    return {"extracted_count": len(ids), "knowledge_ids": ids}


@router.post("/text")
async def ingest_text(
    text: str = Form(...),
    source_type: str = Form(default="document"),
    source_name: str = Form(default="手動入力"),
    user_id: int | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    if source_type == "audio":
        items = await extract_from_transcript(text)
    elif source_type == "chat":
        items = await extract_from_chat(text)
    else:
        items = await extract_knowledge_from_text(text, source_name)

    if not items:
        return {"message": "知見を抽出できませんでした", "extracted_count": 0}

    ids = await _save_items(items, source_type, source_name, db, user_id=user_id)
    return {"extracted_count": len(ids), "knowledge_ids": ids}
