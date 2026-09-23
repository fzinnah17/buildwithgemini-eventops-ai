"""Unit tests for the Two-Phase Action Governance Lifecycle and External Action Ledger."""

import json
import pytest
from app.event_store import get_event_store, EventDossier
from app.tools import preview_calendar_event, create_calendar_event


def test_action_governance_lifecycle():
    store = get_event_store()
    event_id = "evt_wit_manhattan_2026"
    if not store.get_event(event_id):
        store.create_event(EventDossier(
            event_id=event_id,
            title="Women in Tech Leadership Dinner",
            location="Private Dining Room, Midtown Manhattan",
            total_budget=4000.0,
            guest_count=28
        ))

    # Phase 1: Propose action
    res1_json = preview_calendar_event(
        event_id=event_id,
        milestones_only=False
    )
    res1 = json.loads(res1_json)
    assert res1["status"] == "pending_approval"
    action_id = res1["action_id"]

    # Verify action in store
    act = store.get_integration_action(event_id, action_id)
    assert act.status == "pending_approval"
    assert act.approved_at is None

    # Rejection flow
    ok = store.update_integration_action(event_id, action_id, "rejected")
    assert ok is True
    rejected_act = store.get_integration_action(event_id, action_id)
    assert rejected_act.status == "rejected"

    # Attempting to execute rejected action should be blocked
    fail_res_json = create_calendar_event(
        event_id=event_id,
        action_id=action_id
    )
    fail_res = json.loads(fail_res_json)
    assert fail_res["status"] == "blocked"

    # Propose new action and approve it
    res2_json = preview_calendar_event(
        event_id=event_id,
        milestones_only=False
    )
    res2 = json.loads(res2_json)
    new_action_id = res2["action_id"]
    store.update_integration_action(event_id, new_action_id, "approved")

    # Execution succeeds
    exec_res_json = create_calendar_event(
        event_id=event_id,
        action_id=new_action_id
    )
    exec_res = json.loads(exec_res_json)
    assert exec_res["status"] == "completed"
