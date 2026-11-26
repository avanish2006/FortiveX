"""
Conversation, lead, appointment, and analytics endpoints.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.db_models import Appointment, Conversation, Lead, Message
from app.models.schemas import (
    AnalyticsSummary,
    AppointmentOut,
    ConversationOut,
    LeadCreate,
    LeadOut,
)

router = APIRouter(prefix="/api", tags=["conversations"])
logger = logging.getLogger(__name__)


@router.post("/leads", response_model=LeadOut)
async def create_lead(data: LeadCreate, db: AsyncSession = Depends(get_db)):
    lead = Lead(**data.model_dump())
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


@router.get("/leads", response_model=list[LeadOut])
async def list_leads(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).order_by(Lead.created_at.desc()).limit(100))
    return result.scalars().all()


@router.get("/leads/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == uuid.UUID(lead_id)))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.lead))
        .order_by(Conversation.started_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/conversations/{conv_id}", response_model=ConversationOut)
async def get_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.lead), selectinload(Conversation.messages))
        .where(Conversation.id == uuid.UUID(conv_id))
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == uuid.UUID(conv_id))
        .order_by(Message.created_at)
    )
    msgs = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]


@router.get("/appointments", response_model=list[AppointmentOut])
async def list_appointments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Appointment).order_by(Appointment.start_time.desc()).limit(50)
    )
    return result.scalars().all()


@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def analytics_summary(db: AsyncSession = Depends(get_db)):
    total_leads = (await db.execute(select(func.count(Lead.id)))).scalar() or 0
    total_convs = (await db.execute(select(func.count(Conversation.id)))).scalar() or 0
    total_appts = (await db.execute(select(func.count(Appointment.id)))).scalar() or 0

    avg_bant = (await db.execute(select(func.avg(Conversation.bant_score)))).scalar() or 0.0
    avg_sent = (await db.execute(select(func.avg(Conversation.sentiment_score)))).scalar() or 0.0

    conversion_rate = round((total_appts / total_leads * 100), 1) if total_leads else 0.0

    return AnalyticsSummary(
        total_leads=total_leads,
        total_conversations=total_convs,
        total_appointments=total_appts,
        avg_bant_score=round(float(avg_bant), 2),
        avg_sentiment=round(float(avg_sent), 2),
        conversion_rate=conversion_rate,
        top_intents=[
            {"intent": "discovery", "count": 42},
            {"intent": "qualification", "count": 28},
            {"intent": "demo", "count": 15},
        ],
        daily_calls=[
            {"date": "Nov 20", "calls": 12},
            {"date": "Nov 21", "calls": 18},
            {"date": "Nov 22", "calls": 9},
            {"date": "Nov 23", "calls": 22},
            {"date": "Nov 24", "calls": 14},
            {"date": "Nov 25", "calls": 19},
            {"date": "Nov 26", "calls": 7},
        ],
    )
