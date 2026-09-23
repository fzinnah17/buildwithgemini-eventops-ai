"""Unit tests for EventOps Analytics, 4-domain metrics, and privacy sanitization."""

import pytest
from app.integrations.analytics import AnalyticsService, sanitize_telemetry_metadata
from app.tools import get_event_analytics, get_portfolio_analytics
from app.event_store import get_event_store, EventDossier


def test_sanitize_telemetry_metadata_removes_pii():
    raw = {
        "email": "director@example.com",
        "recipient": "guest@domain.com",
        "guest_name": "Alice Smith",
        "dietary": "Vegan / Gluten-Free",
        "token": "SECRET_BEARER_123",
        "body": "Confidential executive notes",
        "raw_prompt": "Tell me about Alice's allergies",
        "guest_count": 28,
        "category": "Food & Beverage",
        "status": "approved",
    }

    sanitized = sanitize_telemetry_metadata(raw)
    assert "email" not in sanitized
    assert "recipient" not in sanitized
    assert "guest_name" not in sanitized
    assert "dietary" not in sanitized
    assert "token" not in sanitized
    assert "body" not in sanitized
    assert "raw_prompt" not in sanitized

    # Allowed operational metrics retained
    assert sanitized["guest_count"] == 28
    assert sanitized["category"] == "Food & Beverage"
    assert sanitized["status"] == "approved"


def test_analytics_service_recording_and_aggregations():
    service = AnalyticsService(max_buffer_size=10)
    service.record_telemetry(
        category="system",
        operation="test_operation",
        event_id="evt_test_analytics",
        latency_ms=150.0
    )
    service.record_telemetry(
        category="system",
        operation="test_operation",
        event_id="evt_test_analytics",
        latency_ms=250.0
    )

    dossier = {
        "event_id": "evt_test_analytics",
        "title": "Test Analytics Event",
        "total_budget": 5000.0,
        "budget_allocations": [
            {"category": "Catering", "allocated_amount": 4000.0},
            {"category": "Contingency Reserve", "allocated_amount": 1000.0},
        ],
        "risks": [{"severity": "attention", "issue": "Weather delay risk"}],
    }
    decisions = [{"status": "approved"}, {"status": "pending"}]
    actions = [{"status": "executed"}]

    metrics = service.get_event_analytics(dossier, decisions, actions)
    assert metrics["scope"] == "event"
    assert metrics["financial"]["contingency_pct"] == 20.0
    assert metrics["governance"]["approved_decisions"] == 1
    assert metrics["governance"]["pending_decisions"] == 1
    assert metrics["system"]["telemetry_events_recorded"] >= 2


def test_analytics_tools_four_domain_metrics():
    import json
    store = get_event_store()
    event = store.get_event("evt_wit_manhattan_2026")
    if not event:
        store.create_event(EventDossier(
            event_id="evt_wit_manhattan_2026",
            title="Women in Tech Leadership Dinner",
            location="Private Dining Room, Midtown Manhattan",
            total_budget=4000.0,
            guest_count=30
        ))

    event_metrics_json = get_event_analytics("evt_wit_manhattan_2026")
    data = json.loads(event_metrics_json)
    assert data["scope"] == "event"
    assert "health" in data
    assert "financial" in data
    assert "governance" in data
    assert "system" in data

    port_metrics_json = get_portfolio_analytics()
    port_data = json.loads(port_metrics_json)
    assert port_data["scope"] == "portfolio"
    assert "summary" in port_data
    assert "governance" in port_data
    assert "system_reliability" in port_data
