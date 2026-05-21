from __future__ import annotations
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import get_db
from app.models.knowledge import TranscriptionRecord, KnowledgeItem, SourceType
from app.services.transcription import transcribe_audio_file, SUPPORTED_FORMATS
from app.services.extractor import extract_from_transcript
from app.services.vector_store import upsert_knowledge
from pathlib import Path

router = APIRouter(prefix="/audio", tags=["audio"])


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    user_id: int | None = Form(default=None),
    extract_knowledge: bool = Form(default=True),
    db: AsyncSession = Depends(get_db),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise HTTPException(status_code=400, detail=f"非対応フォーマット: {suffix}")

    audio_bytes = await file.read()
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="ファイルサイズは25MB以下にしてください")

    try:
        transcript = await transcribe_audio_file(audio_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    record = TranscriptionRecord(
        user_id=user_id,
        filename=file.filename,
        transcript=transcript,
        source_type="file_upload",
    )
    db.add(record)
    await db.flush()

    knowledge_ids = []
    if extract_knowledge and transcript.strip():
        items = await extract_from_transcript(transcript)
        for item in items:
            k = KnowledgeItem(
                title=item.get("title", ""),
                content=item.get("content", ""),
                category=item.get("category", "other"),
                source_type=SourceType.AUDIO,
                source_name=file.filename,
                tags=",".join(item.get("tags", [])),
                contributor_id=user_id,
            )
            db.add(k)
            await db.flush()
            chroma_id = f"knowledge_{k.id}"
            upsert_knowledge(chroma_id, f"{item['title']}\n{item['content']}", {
                "title": item.get("title", ""),
                "category": item.get("category", "other"),
                "source_type": SourceType.AUDIO,
                "db_id": k.id,
            })
            k.chroma_id = chroma_id
            knowledge_ids.append(k.id)

    await db.commit()
    return {
        "transcript_id": record.id,
        "transcript": transcript,
        "extracted_knowledge_count": len(knowledge_ids),
        "knowledge_ids": knowledge_ids,
    }


@router.post("/save-transcript")
async def save_browser_transcript(
    transcript: str = Form(...),
    source_type: str = Form(default="browser_recording"),
    user_id: int | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    record = TranscriptionRecord(
        user_id=user_id,
        transcript=transcript,
        source_type=source_type,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {"id": record.id, "transcript": transcript}


@router.get("/transcripts")
async def list_transcripts(
    user_id: int | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, desc
    stmt = select(TranscriptionRecord).order_by(desc(TranscriptionRecord.created_at)).limit(limit)
    if user_id:
        stmt = stmt.where(TranscriptionRecord.user_id == user_id)
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "transcript": r.transcript,
            "source_type": r.source_type,
            "user_id": r.user_id,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]
