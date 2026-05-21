from __future__ import annotations
from datetime import datetime
from enum import Enum
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.database import Base


class SourceType(str, Enum):
    INTERVIEW = "interview"
    DOCUMENT = "document"
    AUDIO = "audio"
    CHAT = "chat"


class KnowledgeCategory(str, Enum):
    OBJECTION_HANDLING = "objection_handling"
    RAPPORT_BUILDING = "rapport_building"
    NEEDS_DISCOVERY = "needs_discovery"
    CLOSING = "closing"
    PRODUCT_KNOWLEDGE = "product_knowledge"
    COMPETITOR_INFO = "competitor_info"
    PROCESS = "process"
    OTHER = "other"


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100))
    source_type: Mapped[str] = mapped_column(String(50))
    source_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    chroma_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contributor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    support_count: Mapped[int] = mapped_column(Integer, default=1)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True)
    interviewee_name: Mapped[str] = mapped_column(String(200))
    topic: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    messages: Mapped[list["InterviewMessage"]] = relationship("InterviewMessage", back_populates="session")


class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(100), ForeignKey("interview_sessions.session_id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="messages")


class Playbook(Base):
    __tablename__ = "playbooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    scenario: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    source_item_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    pin_hash: Mapped[str] = mapped_column(String(64))
    color: Mapped[str] = mapped_column(String(20), default="#2563eb")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TranscriptionRecord(Base):
    __tablename__ = "transcription_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transcript: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50))  # "file_upload", "browser_recording", "interview"
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KnowledgeFeedback(Base):
    __tablename__ = "knowledge_feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    knowledge_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_items.id"))
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    helpful: Mapped[bool] = mapped_column(Boolean, default=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
