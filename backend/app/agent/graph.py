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
from app.agent.tools import ALL_TOOLS, compute_sentiment
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _patch_gemini_multiple_tools():
    """Patch langchain_google_genai to seamlessly support multiple function calls in a single turn."""
    try:
        import uuid
        from typing import Any, Dict, List, Union, cast
        import proto
        from langchain_core.messages import AIMessage, AIMessageChunk, ToolCall, InvalidToolCall, ToolCallChunk
        from langchain_core.output_parsers.openai_tools import parse_tool_calls
        import langchain_google_genai.chat_models as gm

        def _custom_parse_candidate(response_candidate, streaming: bool = False):
            content: Union[None, str, List[Union[str, Dict[Any, Any]]]] = None
            additional_kwargs: Dict[str, Any] = {}
            tool_calls: List[ToolCall] = []
            invalid_tool_calls: List[InvalidToolCall] = []
            tool_call_chunks: List[ToolCallChunk] = []

            for part in response_candidate.content.parts:
                text = part.text
                if text is not None:
                    if not content:
                        content = text
                    elif isinstance(content, str) and text:
                        content = [content, text]
                    elif isinstance(content, list) and text:
                        content.append(text)

                if part.function_call:
                    raw_args = proto.Message.to_dict(part.function_call).get("args", {})
                    fn_dict = {
                        "name": part.function_call.name,
                        "arguments": json.dumps(raw_args),
                    }
                    if "function_call" not in additional_kwargs:
                        additional_kwargs["function_call"] = fn_dict

                    if streaming:
                        tool_call_chunks.append(
                            ToolCallChunk(
                                name=fn_dict["name"],
                                args=fn_dict["arguments"],
                                id=str(uuid.uuid4()),
                                index=len(tool_call_chunks),
                            )
                        )
                    else:
                        try:
                            parsed = parse_tool_calls([{"function": fn_dict}], return_id=False)
                            for tc in parsed:
                                tool_calls.append(
                                    ToolCall(
                                        name=tc["name"],
                                        args=tc["args"],
                                        id=tc.get("id", str(uuid.uuid4())),
                                    )
                                )
                        except Exception as e:
                            invalid_tool_calls.append(
                                InvalidToolCall(
                                    name=fn_dict["name"],
                                    args=fn_dict["arguments"],
                                    id=str(uuid.uuid4()),
                                    error=str(e),
                                )
                            )

            if content is None:
                content = ""

            if streaming:
                return AIMessageChunk(
                    content=cast(Union[str, List[Union[str, Dict[Any, Any]]]], content),
                    additional_kwargs=additional_kwargs,
                    tool_call_chunks=tool_call_chunks,
                )

            return AIMessage(
                content=cast(Union[str, List[Union[str, Dict[Any, Any]]]], content),
                additional_kwargs=additional_kwargs,
                tool_calls=tool_calls,
                invalid_tool_calls=invalid_tool_calls,
            )

        gm._parse_response_candidate = _custom_parse_candidate
        logger.info("Successfully patched langchain_google_genai to support multiple tool calls")
    except Exception as e:
        logger.warning("Could not patch langchain_google_genai: %s", e)


_patch_gemini_multiple_tools()


def _build_raw_llm():
    """Instantiate the raw LLM without tools."""
    if settings.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.llm_model or "gemini-3.1-flash-lite",
            google_api_key=settings.gemini_api_key,
            temperature=0.7,
        )
    else:
        return ChatOpenAI(
            model=settings.llm_model or "gpt-4o-mini",
            openai_api_key=settings.openai_api_key,
            temperature=0.7,
            streaming=True,
        )


def _build_llm():
    """Instantiate the LLM with tool binding."""
    return _build_raw_llm().bind_tools(ALL_TOOLS)


# ── Agent Node ────────────────────────────────────────────
def agent_node(state: AgentState) -> dict:
    """Main reasoning node — calls LLM with tools or synthesizes tool output."""
    # Automatically compute sentiment on customer's latest input
    sentiment_data = {"sentiment_score": state.get("sentiment_score", 0.0), "sentiment_label": state.get("sentiment_label", "neutral")}
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            sentiment_data = compute_sentiment(str(msg.content))
            break

    system_msg = SystemMessage(
        content=SYSTEM_PROMPT.format(
            session_id=state["session_id"],
            language=state.get("language", "en"),
            bant_score=state.get("bant_score", 0),
            sentiment=sentiment_data["sentiment_label"],
        )
    )

    # If the previous turn was tool execution, synthesize final response with tool knowledge
    if state["messages"] and isinstance(state["messages"][-1], ToolMessage):
        tool_results_text = "\n".join(
            f"[{getattr(m, 'name', 'Tool')}] {m.content}"
            for m in state["messages"]
            if isinstance(m, ToolMessage)
        )
        human_msgs = [m for m in state["messages"] if isinstance(m, HumanMessage)]
        last_human_text = human_msgs[-1].content if human_msgs else ""
        synthesis_prompt = HumanMessage(
            content=(
                f"{last_human_text}\n\n"
                f"[Grounded Knowledge & Tool Output]:\n{tool_results_text}\n\n"
                "Please provide a direct, concise, natural voice response (1-2 sentences) to the customer using the facts above."
            )
        )
        synthesis_msgs = [system_msg] + human_msgs[:-1] + [synthesis_prompt]
        response = _build_raw_llm().invoke(synthesis_msgs)
    else:
        llm = _build_llm()
        messages_with_system = [system_msg] + list(state["messages"])
        response = llm.invoke(messages_with_system)

    content = response.content if isinstance(response.content, str) else ""
    intent = _detect_intent(content, state)

    return {
        "messages": [response],
        "intent": intent,
        "sentiment_score": sentiment_data["sentiment_score"],
        "sentiment_label": sentiment_data["sentiment_label"],
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
    updates: dict = {"last_tool_output": "updated"}

    # Find the most recent ToolMessages
    for msg in reversed(state["messages"]):
        if not isinstance(msg, ToolMessage):
            break

        updates["last_tool_output"] = str(msg.content)[:200]
        tool_name = getattr(msg, "name", "") or ""
        if tool_name == "retrieve_product_info":
            updates["rag_context"] = str(msg.content)

        try:
            data = json.loads(msg.content)
        except (json.JSONDecodeError, TypeError):
            continue

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
