"""
Voice WebSocket endpoint.
Handles binary audio frames and text messages from the browser:
  - Receive audio chunk
  - Transcribe with STT
  - Run LangGraph agent
  - Synthesize TTS
  - Persist conversation/lead/messages to PostgreSQL and state to Redis
  - Return audio + transcript + live insights back to client
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessage, HumanMessage, messages_from_dict, messages_to_dict
from sqlalchemy import select

from app.agent.graph import get_graph
from app.agent.state import AgentState
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.redis_client import cache_get, cache_set
from app.models.db_models import Appointment, Conversation, Lead, Message
from app.voice.stt import transcribe_audio
from app.voice.tts import synthesize_speech

router = APIRouter(prefix="/ws", tags=["voice"])
logger = logging.getLogger(__name__)
settings = get_settings()


def _initial_state(session_id: str, language: str = "en") -> AgentState:
    return {
        "messages": [],
        "session_id": session_id,
        "language": language,
        "bant_budget": None,
        "bant_authority": None,
        "bant_need": None,
        "bant_timeline": None,
        "bant_score": 0,
        "sentiment_score": 0.0,
        "sentiment_label": "neutral",
        "lead_name": None,
        "lead_email": None,
        "lead_phone": None,
        "lead_company": None,
        "lead_job_title": None,
        "status": "active",
        "intent": "greeting",
        "suggested_action": None,
        "appointment_booked": False,
        "appointment_details": None,
        "crm_updated": False,
        "last_tool_output": None,
        "rag_context": None,
        "call_summary": None,
    }


@router.websocket("/voice/{session_id}")
async def voice_ws(websocket: WebSocket, session_id: str, language: str = "en"):
    """
    WebSocket endpoint for voice interaction.
    Protocol:
      Client -> Server : binary audio bytes (WebM/PCM chunks) or JSON {"message": "..."}
      Server -> Client : JSON { type, transcript?, response?, audio_b64?, state? }
    """
    await websocket.accept()
    logger.info("Voice WS connected: session=%s lang=%s", session_id, language)

    cached = await cache_get(f"session:{session_id}")
    state: AgentState = cached if cached else _initial_state(session_id, language)

    if isinstance(state.get("messages"), list) and state["messages"]:
        if isinstance(state["messages"][0], dict):
            state["messages"] = messages_from_dict(state["messages"])

    graph = get_graph()

    try:
        # Send greeting on connection if brand new session
        if not state["messages"]:
            state = await _run_agent(graph, state, "Hello, I just connected.", language)
            ai_text = _extract_last_ai_text(state)
            audio_bytes = await synthesize_speech(ai_text, language)
            await _save_state(session_id, state)
            await _persist_turn(session_id, "", ai_text, state)

            await websocket.send_json({
                "type": "greeting",
                "transcript": "",
                "response": ai_text,
                "audio_b64": _b64(audio_bytes),
                "state": _safe_state(state),
            })

        while True:
            data = await websocket.receive()

            if "bytes" in data and data["bytes"]:
                audio_bytes_in = data["bytes"]
                await websocket.send_json({"type": "processing"})

                transcript = await transcribe_audio(audio_bytes_in, language)
                if not transcript.strip():
                    await websocket.send_json({"type": "empty_audio"})
                    continue

                await websocket.send_json({"type": "transcript", "transcript": transcript})

                state = await _run_agent(graph, state, transcript, language)
                ai_text = _extract_last_ai_text(state)
                audio_out = await synthesize_speech(ai_text, language)

                await _save_state(session_id, state)
                await _persist_turn(session_id, transcript, ai_text, state)

                await websocket.send_json({
                    "type": "response",
                    "transcript": transcript,
                    "response": ai_text,
                    "audio_b64": _b64(audio_out),
                    "state": _safe_state(state),
                })

            elif "text" in data and data["text"]:
                payload = json.loads(data["text"])
                if payload.get("type") == "end_call":
                    state["status"] = "ended"
                    await _save_state(session_id, state)
                    await _persist_turn(session_id, "", "", state)
                    await websocket.send_json({"type": "ended", "state": _safe_state(state)})
                    break

                msg_text = payload.get("message", "")
                if not msg_text.strip():
                    continue

                await websocket.send_json({"type": "processing"})
                state = await _run_agent(graph, state, msg_text, language)
                ai_text = _extract_last_ai_text(state)
                audio_out = await synthesize_speech(ai_text, language)

                await _save_state(session_id, state)
                await _persist_turn(session_id, msg_text, ai_text, state)

                await websocket.send_json({
                    "type": "response",
                    "transcript": msg_text,
                    "response": ai_text,
                    "audio_b64": _b64(audio_out),
                    "state": _safe_state(state),
                })

    except WebSocketDisconnect:
        logger.info("Voice WS disconnected: session=%s", session_id)
        await _save_state(session_id, state)
    except Exception as e:
        logger.error("Voice WS error: %s", e, exc_info=True)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


async def _run_agent(graph, state: AgentState, user_text: str, language: str) -> AgentState:
    state["messages"] = list(state["messages"]) + [HumanMessage(content=user_text)]
    state["language"] = language
    return await graph.ainvoke(state)


def _extract_last_ai_text(state: AgentState) -> str:
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage):
            if isinstance(msg.content, str) and msg.content.strip():
                return msg.content
            if isinstance(msg.content, list):
                text = " ".join(
                    p.get("text", "") for p in msg.content if isinstance(p, dict)
                ).strip()
                if text:
                    return text
    return "I'm here to help. What can I do for you today?"


async def _save_state(session_id: str, state: AgentState):
    serialisable = dict(state)
    serialisable["messages"] = messages_to_dict(list(state["messages"]))
    await cache_set(f"session:{session_id}", serialisable, ttl=86400)


async def _persist_turn(session_id: str, user_text: str, ai_text: str, state: AgentState):
    """Best-effort async persistence of conversation, messages, and lead into PostgreSQL."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Conversation).where(Conversation.session_id == session_id)
            )
            conv = result.scalar_one_or_none()

            lead_id = conv.lead_id if conv else None
            if state.get("lead_email"):
                lead_res = await db.execute(select(Lead).where(Lead.email == state["lead_email"]))
                lead = lead_res.scalar_one_or_none()
                if not lead:
                    lead = Lead(
                        full_name=state.get("lead_name"),
                        email=state.get("lead_email"),
                        phone=state.get("lead_phone"),
                        company=state.get("lead_company"),
                        job_title=state.get("lead_job_title"),
                        language=state.get("language", "en"),
                    )
                    db.add(lead)
                    await db.flush()
                else:
                    if state.get("lead_name"):
                        lead.full_name = state["lead_name"]
                    if state.get("lead_company"):
                        lead.company = state["lead_company"]
                    if state.get("lead_phone"):
                        lead.phone = state["lead_phone"]
                lead_id = lead.id

            if not conv:
                conv = Conversation(
                    session_id=session_id,
                    lead_id=lead_id,
                    language=state.get("language", "en"),
                    status=state.get("status", "active"),
                )
                db.add(conv)
                await db.flush()
            else:
                conv.lead_id = lead_id
                conv.status = state.get("status", conv.status)

            conv.bant_budget = state.get("bant_budget")
            conv.bant_authority = state.get("bant_authority")
            conv.bant_need = state.get("bant_need")
            conv.bant_timeline = state.get("bant_timeline")
            conv.bant_score = state.get("bant_score", 0)
            conv.sentiment_score = state.get("sentiment_score")
            if state.get("status") == "ended" and not conv.ended_at:
                conv.ended_at = datetime.now(timezone.utc)

            if user_text:
                db.add(Message(conversation_id=conv.id, role="user", content=user_text))
            if ai_text:
                db.add(Message(conversation_id=conv.id, role="assistant", content=ai_text))

            await db.commit()
    except Exception as e:
        logger.warning("DB persist skipped/failed: %s", e)


def _safe_state(state: AgentState) -> dict:
    return {
        "bant_score": state.get("bant_score", 0),
        "sentiment_score": state.get("sentiment_score", 0.0),
        "sentiment_label": state.get("sentiment_label", "neutral"),
        "intent": state.get("intent", "discovery"),
        "suggested_action": state.get("suggested_action"),
        "appointment_booked": state.get("appointment_booked", False),
        "crm_updated": state.get("crm_updated", False),
        "status": state.get("status", "active"),
        "lead_name": state.get("lead_name"),
        "lead_email": state.get("lead_email"),
        "lead_company": state.get("lead_company"),
    }


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode() if data else ""
