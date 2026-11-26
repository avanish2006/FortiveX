"""
LangGraph Agent Orchestrator for SalesPilot AI.

Graph topology:
  START → agent_node → (tool_condition) → tools_node → agent_node → ...
                     → END (when no tools called or status=ended/escalated)
"""
from __future__ import annotations

import json
import logging
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.agent.tools import ALL_TOOLS
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_llm():
    """Instantiate the LLM with tool binding."""
    if settings.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=settings.llm_model or "gemini-1.5-pro",
            google_api_key=settings.gemini_api_key,
            temperature=0.7,
        )
    else:
        llm = ChatOpenAI(
            model=settings.llm_model or "gpt-4o-mini",
            openai_api_key=settings.openai_api_key,
            temperature=0.7,
            streaming=True,
        )
    return llm.bind_tools(ALL_TOOLS)


# ── Agent Node ────────────────────────────────────────────
def agent_node(state: AgentState) -> dict:
    """Main reasoning node — calls LLM with tools."""
    llm = _build_llm()

    system_msg = SystemMessage(
        content=SYSTEM_PROMPT.format(
            session_id=state["session_id"],
            language=state.get("language", "en"),
            bant_score=state.get("bant_score", 0),
            sentiment=state.get("sentiment_label", "neutral"),
        )
    )

    # Prepend system message to messages for this call
    messages_with_system = [system_msg] + list(state["messages"])
    response: AIMessage = llm.invoke(messages_with_system)

    # Update intent heuristic
    content = response.content if isinstance(response.content, str) else ""
    intent = _detect_intent(content, state)

    return {
        "messages": [response],
        "intent": intent,
        "suggested_action": _suggest_action(state),
    }


# ── Tools Node ────────────────────────────────────────────
tool_node = ToolNode(ALL_TOOLS)


# ── State Updater Node ────────────────────────────────────
def state_updater_node(state: AgentState) -> dict:
    """
    After tools run, parse their JSON outputs and update state fields
    (BANT, sentiment, appointment, CRM flag etc.).
    """
    updates: dict = {}

    # Find the most recent ToolMessages
    for msg in reversed(state["messages"]):
        if not isinstance(msg, ToolMessage):
            break
        try:
            data = json.loads(msg.content)
        except (json.JSONDecodeError, TypeError):
            continue

        tool_name = getattr(msg, "name", "") or ""

        if "bant_score" in data and isinstance(data["bant_score"], int):
            budget = data.get("bant_budget") or state.get("bant_budget")
            authority = data.get("bant_authority") or state.get("bant_authority")
            need = data.get("bant_need") or state.get("bant_need")
            timeline = data.get("bant_timeline") or state.get("bant_timeline")
            updates["bant_budget"] = budget
            updates["bant_authority"] = authority
            updates["bant_need"] = need
            updates["bant_timeline"] = timeline
            updates["bant_score"] = sum(
                1 for x in (budget, authority, need, timeline) if x and str(x).strip()
            )

        if "sentiment_score" in data:
            updates["sentiment_score"] = data["sentiment_score"]
            updates["sentiment_label"] = data.get("sentiment_label", "neutral")

        if data.get("status") == "booked":
            updates["appointment_booked"] = True
            updates["appointment_details"] = data

        if "crm_updated" in data.get("status", ""):
            updates["crm_updated"] = True

        for field in ("lead_name", "lead_email", "lead_company", "lead_phone", "lead_job_title"):
            if data.get(field):
                updates[field] = data[field]

        if "recommended_next_steps" in data:
            updates["call_summary"] = data

        if data.get("escalated"):
            updates["status"] = "escalated"

    return updates


# ── Routing Condition ─────────────────────────────────────
def should_continue(state: AgentState) -> Literal["tools", "updater", "__end__"]:
    """Route after agent_node: call tools, end conversation, or finish."""
    if state.get("status") in ("ended", "escalated"):
        return "__end__"

    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "tools"

    return "__end__"


def after_tools(state: AgentState) -> Literal["updater"]:
    return "updater"


def after_updater(state: AgentState) -> Literal["agent"]:
    return "agent"


# ── Build Graph ───────────────────────────────────────────
def build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("updater", state_updater_node)

    workflow.set_entry_point("agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "__end__": END},
    )
    workflow.add_edge("tools", "updater")
    workflow.add_edge("updater", "agent")

    return workflow.compile()


# Compiled graph singleton
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ── Helper Functions ──────────────────────────────────────
def _detect_intent(content: str, state: AgentState) -> str:
    lower = content.lower()
    if any(w in lower for w in ["hello", "hi ", "welcome", "good morning", "good afternoon"]):
        return "greeting"
    if any(w in lower for w in ["budget", "authority", "timeline", "decision"]):
        return "qualification"
    if any(w in lower for w in ["demo", "trial", "schedule", "book", "appointment"]):
        return "demo"
    if any(w in lower for w in ["feature", "product", "how does", "what is", "pricing"]):
        return "discovery"
    if any(w in lower for w in ["thank", "goodbye", "bye", "talk soon"]):
        return "close"
    return state.get("intent", "discovery")


def _suggest_action(state: AgentState) -> str | None:
    score = state.get("bant_score", 0)
    if state.get("appointment_booked"):
        return "Send confirmation email"
    if score >= 3 and not state.get("appointment_booked"):
        return "Offer product demo"
    if score >= 2:
        return "Send product brochure"
    return None
