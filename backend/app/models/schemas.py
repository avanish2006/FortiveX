"""Pydantic request/response schemas."""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


# ── Auth ──────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "agent"


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Leads ─────────────────────────────────────────────────
class LeadCreate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    language: str = "en"


class LeadOut(LeadCreate):
    id: UUID
    hubspot_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Conversations ─────────────────────────────────────────
class ConversationOut(BaseModel):
    id: UUID
    session_id: str
    status: str
    language: str
    bant_score: int
    sentiment_score: Optional[float]
    summary: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    lead: Optional[LeadOut]

    class Config:
        from_attributes = True


# ── Messages ──────────────────────────────────────────────
class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    audio_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Appointments ──────────────────────────────────────────
class AppointmentCreate(BaseModel):
    lead_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"


class AppointmentOut(AppointmentCreate):
    id: UUID
    calendar_event_id: Optional[str]
    status: str
    meet_link: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Documents ─────────────────────────────────────────────
class DocumentOut(BaseModel):
    id: UUID
    filename: str
    file_type: Optional[str]
    num_chunks: int
    status: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ── Chat (REST fallback) ──────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str
    language: str = "en"


class ChatResponse(BaseModel):
    session_id: str
    response: str
    bant_score: int
    sentiment: float
    intent: str
    suggested_action: Optional[str]


# ── Analytics ─────────────────────────────────────────────
class AnalyticsSummary(BaseModel):
    total_leads: int
    total_conversations: int
    total_appointments: int
    avg_bant_score: float
    avg_sentiment: float
    conversion_rate: float
    top_intents: List[dict]
    daily_calls: List[dict]
