"""Unit tests verifying structured response schemas and deterministic readiness scoring."""

import pytest
from app.schemas import AgentResponse, ReadinessBreakdown, ReadinessBreakdownItem
from app.event_store import EventDossier
from app.tools import compute_event_readiness, rebalance_event_budget, get_event_store


def test_agent_response_schema():
    """Verify AgentResponse schema serialization and default fields."""
    resp = AgentResponse(
        status="ok",
        response_type="readiness_scan",
        title="EventOps Guard Scan",
        summary="Score: 95/100",
        event_id="evt_test_01",
    )
    data = resp.model_dump()
    assert data["status"] == "ok"
    assert data["response_type"] == "readiness_scan"
    assert data["request_id"].startswith("req_")
    assert "data" in data
    assert "recommendations" in data


def test_authoritative_readiness_scoring_math():
    """Verify single source of truth readiness score calculation and deduction breakdown."""
    event = EventDossier(
        event_id="evt_unit_math_01",
        title="Perfect 100 Event",
        guest_count=20,  # under 25, no coat check required
        total_budget=5000.0,
        budget_allocations=[
            {"category": "Food & Beverage", "allocated_amount": 3000.0, "is_protected": True},
            {"category": "Venue & Space", "allocated_amount": 1000.0, "is_protected": False},
            {"category": "Contingency Reserve", "allocated_amount": 1000.0, "is_protected": True},  # 20% contingency
        ],
        venue_requirements={"space_type": "Private dining room with door closure"},
        food_beverage={"dietary_protocol": "Advance dietary survey on RSVP"},
        tasks=[{"task": "Confirm catering", "owner": "Alice"}],
    )

    score, findings, breakdown = compute_event_readiness(event)
    assert score == 100
    assert breakdown.score == 100
    assert len(breakdown.items) == 6
    for item in breakdown.items:
        assert item.points == 0


def test_contingency_deduction_and_explanation():
    """Verify exact point deduction when contingency is under 10%."""
    event = EventDossier(
        event_id="evt_unit_math_02",
        title="Tight Contingency Event",
        guest_count=20,
        total_budget=4000.0,
        budget_allocations=[
            {"category": "Food & Beverage", "allocated_amount": 3650.0},
            {"category": "Contingency Reserve", "allocated_amount": 350.0},  # 8.75% -> triggers -5 deduction
        ],
        venue_requirements={"space_type": "Private dining room with door closure"},
        food_beverage={"dietary_protocol": "Advance dietary survey on RSVP"},
        tasks=[{"task": "Confirm venue", "owner": "Host"}],
    )

    score, findings, breakdown = compute_event_readiness(event)
    assert score == 95
    assert breakdown.score == 95
    assert "Contingency Reserve (-5)" in breakdown.explanation
