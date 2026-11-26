"""
LangGraph conversation state definition.
This TypedDict is passed through all agent nodes and updated at each step.
"""
from __future__ import annotations

from typing import Annotated, Any, Optional, Sequence
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Full state carried through the LangGraph workflow."""

    # Core conversation
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    language: str

    # Lead qualification
    bant_budget: Optional[str]
    bant_authority: Optional[str]
    bant_need: Optional[str]
    bant_timeline: Optional[str]
    bant_score: int

    # Sentiment
    sentiment_score: float
    sentiment_label: str

    # Lead info (collected progressively)
    lead_name: Optional[str]
    lead_email: Optional[str]
    lead_phone: Optional[str]
    lead_company: Optional[str]
    lead_job_title: Optional[str]

    # Conversation lifecycle
    status: str                   # active | ended | escalated
    intent: str                   # greeting | discovery | qualification | demo | close | escalate
    suggested_action: Optional[str]

    # Appointment
    appointment_booked: bool
    appointment_details: Optional[dict]

    # CRM
    crm_updated: bool

    # Tool outputs
    last_tool_output: Optional[str]
    rag_context: Optional[str]

    # Summary
    call_summary: Optional[dict]
