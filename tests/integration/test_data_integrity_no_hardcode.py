"""Integration tests verifying Data Integrity, Test Isolation, and No Hardcoding."""

import json
import pytest
from app.integrations.analytics import analytics_service
from app.event_store import get_event_store, is_in_memory_mode
from frontend.main import (
    CANONICAL_EVENT_IDS,
    app,
)
from starlette.testclient import TestClient

client = TestClient(app)


def test_canonical_event_isolation_and_no_mutation():
    """Verify canonical events are never mutated and test isolation is strictly enforced."""
    # 1. Snapshot canonical events
    pre_snapshots = {}
    for eid in CANONICAL_EVENT_IDS:
        res = client.get(f"/api/event/{eid}")
        assert res.status_code == 200, f"Failed to fetch canonical event {eid}"
        pre_snapshots[eid] = res.json()

    # Verify WIT is at pristine 30 guests, 4000 budget, v1, 95 score
    wit = pre_snapshots["evt_wit_manhattan_2026"]
    assert wit.get("guest_count") == 30, f"Canonical WIT guests must be 30, got {wit.get('guest_count')}"
    assert float(wit.get("total_budget")) == 4000.0
    assert wit.get("version") == 1
    assert wit.get("readiness_score") == 95

    # 2. Verify guarded patch rejection/protection for canonical events in test environment
    # Attempting to patch canonical event through API during test should be protected
    patch_res = client.patch(
        "/api/events/evt_wit_manhattan_2026",
        json={"guest_count": 999, "total_budget": 99999.0},
    )
    assert patch_res.status_code in [200, 403]

    # 3. Create, mutate, and delete a temporary event
    temp_id = "evt_test_temp_isolation_99"
    temp_payload = {
        "event_id": temp_id,
        "title": "Temp Isolation Test Event",
        "guest_count": 25,
        "total_budget": 5000.0,
        "location": "Test Venue, NYC",
        "status": "planning",
        "version": 1,
        "readiness_score": 80,
    }
    create_res = client.post("/api/events", json=temp_payload)
    assert create_res.status_code == 200

    # Mutate the temporary event
    mut_res = client.patch(f"/api/events/{temp_id}", json={"guest_count": 35})
    assert mut_res.status_code == 200
    assert mut_res.json()["event"]["guest_count"] == 35

    # 4. Clean up temporary event
    store = get_event_store()
    if hasattr(store, "events") and temp_id in store.events:
        del store.events[temp_id]
    elif hasattr(store, "delete_event"):
        store.delete_event(temp_id)

    # 5. Snapshot after test operations and assert semantic identity
    for eid in CANONICAL_EVENT_IDS:
        post_res = client.get(f"/api/event/{eid}")
        assert post_res.status_code == 200
        post_data = post_res.json()
        assert post_data.get("guest_count") == pre_snapshots[eid].get("guest_count")
        assert post_data.get("total_budget") == pre_snapshots[eid].get("total_budget")
        assert post_data.get("version") == pre_snapshots[eid].get("version")
        assert post_data.get("readiness_score") == pre_snapshots[eid].get("readiness_score")


def test_hardcode_regression_synthetic_events():
    """Verify that Copilot and Analytics dynamically derive from active event dossier,
    with zero bleed from hardcoded literals (no 28, 30, $4,000, $3,000, 85, 90, 95).
    """
    event_a = {
        "event_id": "evt_synth_a",
        "title": "Synthetic Event A",
        "guest_count": 17,
        "total_budget": 7321.0,
        "location": "Pier 17, NYC",
        "status": "planning",
        "readiness_score": 73,
        "staffing": [
            {"name": "Lead Host", "role": "Host"},
            {"name": "Bar Lead", "role": "Beverage"},
            {"name": "Security Lead", "role": "Security"},
        ],
        "allocations": [
            {"category": "Venue & Production", "amount": 3500.0},
            {"category": "Food & Beverage", "amount": 2500.0},
            {"category": "Contingency Reserve", "amount": 1321.0},
        ],
        "decisions": [],
    }

    event_b = {
        "event_id": "evt_synth_b",
        "title": "Synthetic Event B",
        "guest_count": 91,
        "total_budget": 23457.0,
        "location": "Javits Center, NYC",
        "status": "planning",
        "readiness_score": 62,
        "staffing": [{"name": f"Staff Member {i}", "role": "Service"} for i in range(11)],
        "allocations": [
            {"category": "Venue & AV", "amount": 12000.0},
            {"category": "Catering", "amount": 8000.0},
            {"category": "Contingency Reserve", "amount": 3457.0},
        ],
        "decisions": [],
    }

    # Test Analytics Engine for Event A
    an_a = analytics_service.get_event_analytics(event_a, [], [])
    assert an_a["financial"]["allocated_budget"] == 7321.0
    assert an_a["financial"]["contingency_amount"] == 1321.0
    assert an_a["governance"]["approval_rate_pct"] is None  # 0 decisions = None, NOT 100%
    assert an_a["health"]["readiness_score"] == 73  # Exact score, NOT 90 or 95

    # Test Analytics Engine for Event B
    an_b = analytics_service.get_event_analytics(event_b, [], [])
    assert an_b["financial"]["allocated_budget"] == 23457.0
    assert an_b["financial"]["contingency_amount"] == 3457.0
    assert an_b["governance"]["approval_rate_pct"] is None
    assert an_b["health"]["readiness_score"] == 62

    # Portfolio Analytics over Event A and Event B
    port_an = analytics_service.get_portfolio_analytics([event_a, event_b], [], [])
    assert port_an["summary"]["events_managed"] == 2
    assert port_an["summary"]["total_portfolio_budget"] == 7321.0 + 23457.0
    assert port_an["summary"]["total_guests_managed"] == 17 + 91
    assert port_an["summary"]["avg_readiness_score"] == round((73 + 62) / 2, 1)
    assert port_an["governance"]["portfolio_approval_rate_pct"] is None

    # Test Chat Backend Staffing Analysis for Event A
    chat_a_res = client.post("/chat", json={
        "message": "Review staffing ratio and arrival coverage",
        "event_id": "evt_synth_a",
        "event_data": event_a,
    }).json()
    chat_a_staff = chat_a_res.get("structured", chat_a_res)
    assert "Staffing" in chat_a_staff.get("title", "")
    assert "17 guests" in chat_a_staff["summary"]
    assert "3 staff" in chat_a_staff["summary"]
    assert "5.7" in chat_a_staff["summary"]
    assert "28" not in chat_a_staff["summary"]
    assert "30" not in chat_a_staff["summary"]

    # Test Chat Backend Staffing Analysis for Event B
    chat_b_res = client.post("/chat", json={
        "message": "Review staffing ratio and arrival coverage",
        "event_id": "evt_synth_b",
        "event_data": event_b,
    }).json()
    chat_b_staff = chat_b_res.get("structured", chat_b_res)
    assert "Staffing" in chat_b_staff.get("title", "")
    assert "91 guests" in chat_b_staff["summary"]
    assert "11 staff" in chat_b_staff["summary"]
    assert "8.3" in chat_b_staff["summary"]
    assert "above 1:8 target" in chat_b_staff["summary"]
    assert "28" not in chat_b_staff["summary"]
    assert "30" not in chat_b_staff["summary"]

    # Test Chat Backend Budget Rebalancing for Event A
    chat_a_budget_res = client.post("/chat", json={
        "message": "Help me rebalance this event's budget.",
        "event_id": "evt_synth_a",
        "event_data": event_a,
    }).json()
    chat_a_budget = chat_a_budget_res.get("structured", chat_a_budget_res)
    assert chat_a_budget.get("response_type") == "budget_proposal" or chat_a_budget.get("type") == "budget_change_proposal"
    new_tot_a = chat_a_budget.get("data", {}).get("proposed_budget") or chat_a_budget.get("proposal", {}).get("new_total")
    assert new_tot_a == 7321.0
    text_a = str(chat_a_budget_res)
    assert "$4,000" not in text_a
    assert "$3,000" not in text_a

    # Test Chat Backend Budget Rebalancing for Event B
    chat_b_budget_res = client.post("/chat", json={
        "message": "Help me rebalance this event's budget.",
        "event_id": "evt_synth_b",
        "event_data": event_b,
    }).json()
    chat_b_budget = chat_b_budget_res.get("structured", chat_b_budget_res)
    assert chat_b_budget.get("response_type") == "budget_proposal" or chat_b_budget.get("type") == "budget_change_proposal"
    new_tot_b = chat_b_budget.get("data", {}).get("proposed_budget") or chat_b_budget.get("proposal", {}).get("new_total")
    assert new_tot_b == 23457.0
    text_b = str(chat_b_budget_res)
    assert "$4,000" not in text_b
    assert "$3,000" not in text_b


def test_copilot_quick_actions_event_aware_and_reliable():
    """Verify all 4 quick actions work reliably across canonical events with distinct outputs."""
    events_to_test = ["evt_wit_manhattan_2026", "evt_design_summit_2026"]
    prompts = [
        "What am I forgetting?",
        "Help me rebalance this event's budget.",
        "Explain our readiness score",
        "Review staffing ratio and arrival coverage",
    ]

    results = {eid: {} for eid in events_to_test}

    for eid in events_to_test:
        for prompt in prompts:
            res = client.post("/chat", json={"message": prompt, "event_id": eid})
            assert res.status_code == 200
            data = res.json()
            assert data.get("type") != "error", f"Prompt '{prompt}' failed for {eid}: {data}"
            assert data.get("title") != "Operation Incomplete", f"Prompt '{prompt}' incomplete for {eid}"
            results[eid][prompt] = data

    # Assert event awareness: responses must differ between WIT (30 guests, $4k) and Summit (85 guests, $18.5k)
    # 1. Budget rebalance differences
    wit_budget = results["evt_wit_manhattan_2026"]["Help me rebalance this event's budget."]
    summit_budget = results["evt_design_summit_2026"]["Help me rebalance this event's budget."]
    wit_st = wit_budget.get("structured", wit_budget)
    summit_st = summit_budget.get("structured", summit_budget)
    wit_total = wit_st.get("data", {}).get("proposed_budget") or wit_st.get("proposal", {}).get("new_total")
    summit_total = summit_st.get("data", {}).get("proposed_budget") or summit_st.get("proposal", {}).get("new_total")
    assert wit_total == 4000.0
    assert summit_total == 18500.0

    # 2. Staffing ratio differences
    wit_staff = results["evt_wit_manhattan_2026"]["Review staffing ratio and arrival coverage"]
    summit_staff = results["evt_design_summit_2026"]["Review staffing ratio and arrival coverage"]
    wit_staff_st = wit_staff.get("structured", wit_staff)
    summit_staff_st = summit_staff.get("structured", summit_staff)
    assert "30 guests" in wit_staff_st["summary"]
    assert "85 guests" in summit_staff_st["summary"]
    assert wit_staff_st["summary"] != summit_staff_st["summary"]


def test_no_adk_badge_and_truthful_greetings():
    """Verify ADK 1.1.0 badge is removed and greetings are truthful in HTML files."""
    from pathlib import Path

    live_html = Path("frontend/static/index.html").read_text()
    demo_html = Path("portfolio-demo/index.html").read_text()

    # Neither should contain ADK 1.1.0
    assert "ADK 1.1.0" not in live_html, "ADK 1.1.0 badge must be removed from live index.html"
    assert "ADK 1.1.0" not in demo_html, "ADK 1.1.0 badge must be removed from portfolio demo index.html"

    # Both should have copilotModeBadge
    assert 'id="copilotModeBadge"' in live_html
    assert 'id="copilotModeBadge"' in demo_html

    # Live should proclaim connection to agent and authoritative event state
    assert "Connected to the deployed EventOps agent and authoritative event state" in live_html

    # Demo should proclaim preserved local fixtures and no live cloud mutations
    assert "Using preserved local event fixtures and deterministic workflow simulations" in demo_html
    assert "No live cloud or external mutations are performed" in demo_html
