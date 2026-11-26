"""
REST chat endpoint (fallback for text-only interactions and testing).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, messages_from_dict

from app.agent.graph import get_graph
from app.agent.state import AgentState
from app.core.redis_client import cache_get
from app.models.schemas import ChatRequest, ChatResponse
from app.routers.voice import (
    _extract_last_ai_text,
    _initial_state,
    _persist_turn,
    _safe_state,
    _save_state,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a text message to the AI agent and get a response."""
    session_id = request.session_id
    language = request.language

    cached = await cache_get(f"session:{session_id}")
    state: AgentState = cached if cached else _initial_state(session_id, language)

    if isinstance(state.get("messages"), list) and state["messages"]:
        if isinstance(state["messages"][0], dict):
            state["messages"] = messages_from_dict(state["messages"])

    graph = get_graph()
    state["messages"] = list(state["messages"]) + [HumanMessage(content=request.message)]
    state["language"] = language

    try:
        state = await graph.ainvoke(state)
    except Exception as e:
        logger.error("Agent error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    await _save_state(session_id, state)
    ai_text = _extract_last_ai_text(state)
    await _persist_turn(session_id, request.message, ai_text, state)
    safe = _safe_state(state)

    return ChatResponse(
        session_id=session_id,
        response=ai_text,
        bant_score=safe["bant_score"],
        sentiment=safe["sentiment_score"],
        intent=safe["intent"],
        suggested_action=safe["suggested_action"],
    )
