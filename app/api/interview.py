import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.knowledge import InterviewSession, InterviewMessage, KnowledgeItem, SourceType
from app.services.interviewer import get_interview_response, synthesize_interview
from app.services.vector_store import upsert_knowledge

router = APIRouter(prefix="/interview", tags=["interview"])


class StartInterviewRequest(BaseModel):
    interviewee_name: str
    topic: str | None = None


class SendMessageRequest(BaseModel):
    session_id: str
    message: str


class StartInterviewResponse(BaseModel):
    session_id: str
    greeting: str


@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(req: StartInterviewRequest, db: AsyncSession = Depends(get_db)):
    session_id = str(uuid.uuid4())

    session = InterviewSession(
        session_id=session_id,
        interviewee_name=req.interviewee_name,
        topic=req.topic,
    )
    db.add(session)
    await db.flush()

    greeting = await get_interview_response(
        messages=[{"role": "user", "content": "インタビューを開始してください。"}],
        interviewee_name=req.interviewee_name,
        topic=req.topic,
    )

    db.add(InterviewMessage(session_id=session_id, role="assistant", content=greeting))
    await db.commit()

    return StartInterviewResponse(session_id=session_id, greeting=greeting)


@router.post("/message")
async def send_message(req: SendMessageRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.session_id == req.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.add(InterviewMessage(session_id=req.session_id, role="user", content=req.message))

    msg_result = await db.execute(
        select(InterviewMessage)
        .where(InterviewMessage.session_id == req.session_id)
        .order_by(InterviewMessage.created_at)
    )
    history = [{"role": m.role, "content": m.content} for m in msg_result.scalars()]
    history.append({"role": "user", "content": req.message})

    reply = await get_interview_response(
        messages=history,
        interviewee_name=session.interviewee_name,
        topic=session.topic,
    )

    db.add(InterviewMessage(session_id=req.session_id, role="assistant", content=reply))
    await db.commit()

    return {"reply": reply}


@router.post("/finalize/{session_id}")
async def finalize_interview(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await db.execute(
        select(InterviewMessage)
        .where(InterviewMessage.session_id == session_id)
        .order_by(InterviewMessage.created_at)
    )
    messages = [{"role": m.role, "content": m.content} for m in msg_result.scalars()]

    items = await synthesize_interview(messages, session.interviewee_name)

    saved_ids = []
    for item in items:
        knowledge = KnowledgeItem(
            title=item.get("title", ""),
            content=item.get("content", ""),
            category=item.get("category", "other"),
            source_type=SourceType.INTERVIEW,
            source_name=f"インタビュー: {session.interviewee_name}",
            tags=",".join(item.get("tags", [])),
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
                "source_type": SourceType.INTERVIEW,
                "db_id": knowledge.id,
            },
        )
        knowledge.chroma_id = chroma_id
        saved_ids.append(knowledge.id)

    session.status = "completed"
    await db.commit()

    return {"extracted_count": len(items), "knowledge_ids": saved_ids}


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(InterviewSession).order_by(InterviewSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "session_id": s.session_id,
            "interviewee_name": s.interviewee_name,
            "topic": s.topic,
            "status": s.status,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]
