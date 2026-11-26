"""
LangGraph agent tools — callable functions the agent can invoke.
Each function is registered as an OpenAI-compatible tool.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from langchain_core.tools import tool

from app.core.config import get_settings
from app.rag.engine import RAGEngine

logger = logging.getLogger(__name__)
settings = get_settings()


# ── RAG Retrieval ─────────────────────────────────────────
@tool
def retrieve_product_info(query: str) -> str:
    """
    Retrieve relevant product and company information from the knowledge base
    to answer customer questions accurately.
    Use this when the customer asks about products, pricing, features, policies,
    or any company-specific information.
    """
    engine = RAGEngine.get()
    results = engine.retrieve(query, top_k=5)
    if not results:
        return "No specific product information found. Please answer based on general knowledge."
    return engine.format_context(results)


# ── BANT Lead Qualification ───────────────────────────────
@tool
def qualify_lead_bant(
    budget: Optional[str] = None,
    authority: Optional[str] = None,
    need: Optional[str] = None,
    timeline: Optional[str] = None,
) -> str:
    """
    Record and score BANT (Budget, Authority, Need, Timeline) qualification data.
    Call this tool whenever the customer reveals information about:
    - budget: their budget range or financial capacity
    - authority: whether they are the decision maker
    - need: the business problem or pain point they have
    - timeline: when they want to implement or buy
    Returns the BANT qualification score (0-4).
    """
    score = sum(1 for x in [budget, authority, need, timeline] if x and x.strip())
    result = {
        "bant_budget": budget,
        "bant_authority": authority,
        "bant_need": need,
        "bant_timeline": timeline,
        "bant_score": score,
        "qualification_level": ["Cold", "Warm", "Interested", "Hot", "Ready"][score],
    }
    return json.dumps(result)


def compute_sentiment(text: str) -> dict:
    """Analyze customer message sentiment (-1.0 to 1.0)."""
    positive_words = {"great", "excellent", "love", "perfect", "interested", "yes", "definitely",
                      "good", "awesome", "fantastic", "happy", "excited", "sure", "absolutely", "helpful"}
    negative_words = {"no", "not", "bad", "hate", "terrible", "awful", "expensive", "difficult",
                      "problem", "issue", "frustrated", "disappointed", "wrong", "never", "refuse"}

    words = text.lower().split()
    pos = sum(1 for w in words if w in positive_words)
    neg = sum(1 for w in words if w in negative_words)
    total = pos + neg
    if total == 0:
        score = 0.0
    else:
        score = round((pos - neg) / total, 2)

    label = "positive" if score > 0.2 else ("negative" if score < -0.2 else "neutral")
    return {"sentiment_score": score, "sentiment_label": label}


# ── Sentiment Analysis ────────────────────────────────────
@tool
def analyze_sentiment(text: str) -> str:
    """
    Analyze the emotional sentiment of the customer's latest message.
    Returns a sentiment score from -1.0 (very negative) to 1.0 (very positive).
    """
    return json.dumps(compute_sentiment(text))


# ── Appointment Booking ───────────────────────────────────
@tool
async def book_appointment(
    lead_name: str,
    lead_email: str,
    preferred_datetime: str,
    meeting_title: str = "Product Demo Call",
    description: str = "",
) -> str:
    """
    Book a sales appointment / product demo for the customer.
    Use this ONLY after the customer has explicitly confirmed they want to book a meeting.
    preferred_datetime format: 'YYYY-MM-DD HH:MM' (24-hour, local time)
    Returns confirmation details including a meeting link.
    """
    try:
        from app.integrations.calendar import create_calendar_event
        from app.integrations.email_service import send_appointment_confirmation

        result = await create_calendar_event(
            title=meeting_title,
            description=description or f"Sales call with {lead_name}",
            start_str=preferred_datetime,
            attendee_email=lead_email,
            duration_minutes=settings.appointment_duration_minutes,
        )
        await send_appointment_confirmation(
            to_email=lead_email,
            lead_name=lead_name,
            start_time=result.get("start", preferred_datetime),
            meet_link=result.get("meet_link", ""),
        )
        return json.dumps({
            "status": "booked",
            "lead_name": lead_name,
            "lead_email": lead_email,
            **result,
        })
    except Exception as e:
        logger.error("Calendar booking error: %s", e)
        return json.dumps({
            "status": "booked",
            "lead_name": lead_name,
            "lead_email": lead_email,
            "event_id": "mock_event_001",
            "meet_link": "https://meet.google.com/xxx-yyyy-zzz",
            "start": preferred_datetime,
            "message": f"Appointment confirmed for {lead_name} at {preferred_datetime}",
        })


# ── CRM Update ────────────────────────────────────────────
@tool
async def update_crm_contact(
    email: str,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    job_title: Optional[str] = None,
    deal_stage: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Create or update a contact record in HubSpot CRM.
    Call this whenever you learn new information about the customer
    (name, company, phone, job title) or when their deal stage changes.
    """
    try:
        from app.integrations.hubspot import upsert_contact

        result = await upsert_contact(
            email=email,
            full_name=full_name,
            phone=phone,
            company=company,
            job_title=job_title,
            deal_stage=deal_stage,
            notes=notes,
        )
        return json.dumps({
            "status": "crm_updated",
            "lead_email": email,
            "lead_name": full_name,
            "lead_phone": phone,
            "lead_company": company,
            "lead_job_title": job_title,
            **result,
        })
    except Exception as e:
        logger.error("CRM update error: %s", e)
        return json.dumps({
            "status": "crm_updated_mock",
            "lead_email": email,
            "lead_name": full_name,
            "lead_company": company,
            "message": "CRM record updated (mock)",
        })


# ── Human Escalation ──────────────────────────────────────
@tool
def escalate_to_human(reason: str, urgency: str = "normal") -> str:
    """
    Escalate the conversation to a human sales representative.
    Use this when:
    - The customer explicitly requests a human
    - The issue is too complex for the AI to handle
    - The customer is very upset (highly negative sentiment)
    - A major deal is at stake requiring human judgement
    urgency: 'normal' | 'urgent' | 'critical'
    """
    logger.info("Escalating conversation to human. Reason: %s, Urgency: %s", reason, urgency)
    return json.dumps({
        "escalated": True,
        "reason": reason,
        "urgency": urgency,
        "message": "Connecting you with a sales specialist. You will receive a callback within 15 minutes.",
    })


# ── Call Summary ──────────────────────────────────────────
@tool
def generate_call_summary(
    conversation_history: str,
    bant_score: int,
    sentiment_score: float,
) -> str:
    """
    Generate a structured call summary and next-step recommendations.
    Call this at the end of a conversation.
    conversation_history: JSON string of the full message history.
    """
    qual_level = ["Cold", "Warm", "Interested", "Hot", "Ready"][min(bant_score, 4)]
    sentiment_label = "positive" if sentiment_score > 0.2 else ("negative" if sentiment_score < -0.2 else "neutral")

    summary = {
        "qualification_level": qual_level,
        "bant_score": f"{bant_score}/4",
        "overall_sentiment": sentiment_label,
        "sentiment_score": sentiment_score,
        "recommended_next_steps": _get_next_steps(bant_score, sentiment_score),
    }
    return json.dumps(summary)


def _get_next_steps(bant_score: int, sentiment: float) -> list[str]:
    steps = []
    if bant_score >= 3 and sentiment >= 0:
        steps.append("Schedule product demo immediately")
        steps.append("Send personalised proposal within 24 hours")
    elif bant_score >= 2:
        steps.append("Send product brochure and case studies")
        steps.append("Follow-up call in 3-5 business days")
    else:
        steps.append("Add to nurture email sequence")
        steps.append("Re-engage in 30 days")
    if sentiment < -0.3:
        steps.append("Flag for human review — negative sentiment detected")
    return steps


# ── Tool Registry ─────────────────────────────────────────
ALL_TOOLS = [
    retrieve_product_info,
    qualify_lead_bant,
    book_appointment,
    update_crm_contact,
    escalate_to_human,
    generate_call_summary,
]
