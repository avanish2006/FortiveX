"""Unit tests for SalesPilot AI agent tools and RAG engine."""
import json
import tempfile
from pathlib import Path

from app.agent.tools import (
    analyze_sentiment,
    escalate_to_human,
    generate_call_summary,
    qualify_lead_bant,
)


def test_qualify_lead_bant_scoring():
    res = json.loads(
        qualify_lead_bant.invoke(
            {
                "budget": "$10,000/year",
                "authority": "VP of Sales",
                "need": "Automate inbound lead qualification",
                "timeline": "Q1 2027",
            }
        )
    )
    assert res["bant_score"] == 4
    assert res["qualification_level"] == "Ready"


def test_qualify_lead_bant_partial():
    res = json.loads(qualify_lead_bant.invoke({"need": "Reduce response time"}))
    assert res["bant_score"] == 1
    assert res["qualification_level"] == "Warm"


def test_analyze_sentiment_positive():
    res = json.loads(analyze_sentiment.invoke({"text": "This looks great and I am definitely interested"}))
    assert res["sentiment_score"] > 0
    assert res["sentiment_label"] == "positive"


def test_analyze_sentiment_negative():
    res = json.loads(analyze_sentiment.invoke({"text": "This is terrible and too expensive, not interested"}))
    assert res["sentiment_score"] < 0
    assert res["sentiment_label"] == "negative"


def test_escalate_to_human():
    res = json.loads(
        escalate_to_human.invoke({"reason": "Customer requested enterprise legal review", "urgency": "urgent"})
    )
    assert res["escalated"] is True
    assert res["urgency"] == "urgent"


def test_generate_call_summary():
    res = json.loads(
        generate_call_summary.invoke(
            {"conversation_history": "[]", "bant_score": 4, "sentiment_score": 0.6}
        )
    )
    assert res["qualification_level"] == "Ready"
    assert res["bant_score"] == "4/4"
    assert len(res["recommended_next_steps"]) >= 1
