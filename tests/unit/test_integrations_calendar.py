"""Unit tests for Calendar integrations and tools."""

import json
import pytest
from app.integrations.calendar import GoogleCalendarProvider, DemoCalendarProvider
from app.tools import preview_calendar_event, create_calendar_event
from app.event_store import get_event_store, EventDossier


def test_google_calendar_not_configured_when_no_credentials(monkeypatch):
    monkeypatch.delenv("GOOGLE_CALENDAR_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    provider = GoogleCalendarProvider()
    status = provider.get_connection_status()
    assert status.status == "not_connected"
    assert status.provider == "calendar"
    assert "not configured" in (status.error_summary or "").lower()


def test_demo_calendar_provider_crud_and_idempotency():
    provider = DemoCalendarProvider()
    status = provider.get_connection_status()
    assert status.status == "connected"
    assert status.is_demo is True

    event_data = {
        "event_id": "evt_test_cal",
        "title": "Executive Tasting Dinner",
        "description": "Formal dinner with keynote",
        "date": "2026-10-15",
        "start_time": "18:00",
        "end_time": "21:00",
        "location": "Manhattan, NY",
    }

    preview = provider.preview_event(event_data, mode="main")
    assert preview["is_demo"] is True
    assert preview["main_event"]["summary"] == "Executive Tasting Dinner"

    created = provider.create_event(event_data, idempotency_key="idem_cal_123")
    assert created["status"] == "completed"
    assert created["is_demo"] is True
    assert "gcal_sim_" in created["calendar_event_id"]

    # Idempotent call with same key returns identical calendar_event_id
    repeated = provider.create_event(event_data, idempotency_key="idem_cal_123")
    assert repeated["calendar_event_id"] == created["calendar_event_id"]

    # Sync event check
    sync_res = provider.sync_event(event_data, existing_sync=created)
    assert sync_res["in_sync"] is True


def test_calendar_tool_governance_workflow():
    store = get_event_store()
    event = store.get_event("evt_wit_manhattan_2026")
    if not event:
        store.create_event(EventDossier(
            event_id="evt_wit_manhattan_2026",
            title="Women in Tech Leadership Dinner",
            location="Private Dining Room, Midtown Manhattan",
            total_budget=4000.0,
            guest_count=28
        ))

    # Preview calendar event (proposes action in pending_approval)
    preview_json = preview_calendar_event("evt_wit_manhattan_2026", milestones_only=False)
    preview = json.loads(preview_json)
    assert preview["status"] == "pending_approval"
    action_id = preview["action_id"]

    # Verify action was recorded in event store
    action = store.get_integration_action("evt_wit_manhattan_2026", action_id)
    assert action is not None
    assert action.provider == "calendar"
    assert action.status == "pending_approval"

    # Attempting to execute unapproved action should be blocked
    blocked_json = create_calendar_event(
        event_id="evt_wit_manhattan_2026",
        action_id=action_id
    )
    blocked = json.loads(blocked_json)
    assert blocked["status"] == "blocked"

    # Approve action
    store.update_integration_action("evt_wit_manhattan_2026", action_id, "approved", approved_by="Director")

    # Retry creation with approved action_id succeeds
    approved_json = create_calendar_event(
        event_id="evt_wit_manhattan_2026",
        action_id=action_id
    )
    approved_res = json.loads(approved_json)
    assert approved_res["status"] == "completed"

    updated_action = store.get_integration_action("evt_wit_manhattan_2026", action_id)
    assert updated_action.status == "completed"
