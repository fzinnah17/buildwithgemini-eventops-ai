"""Unit tests for Slack messaging integration and structured payload delivery."""

import json
import pytest
from app.integrations.messaging import SlackProvider, DemoMessagingProvider
from app.integrations.models import SlackMessagePayload
from app.tools import preview_slack_message, post_slack_message
from app.event_store import get_event_store, EventDossier


def test_slack_not_configured_when_no_credentials(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    provider = SlackProvider()
    status = provider.get_connection_status()
    assert status.status == "not_connected"
    assert status.provider == "slack"
    assert "not configured" in (status.error_summary or "").lower()


def test_demo_messaging_provider_posting_and_idempotency():
    provider = DemoMessagingProvider()
    status = provider.get_connection_status()
    assert status.status == "connected"
    assert status.is_demo is True

    event_data = {
        "event_id": "evt_slack_01",
        "title": "Women in Tech Leadership Dinner",
    }

    finding = {
        "title": "Readiness Score Alert",
        "summary": "Readiness score increased to 95/100 after contingency allocation.",
        "action": "Review updated ledger",
        "owner": "Director",
        "due": "Immediate",
    }

    preview = provider.preview_message(
        event_data=event_data,
        category="Readiness Alert",
        finding_or_decision=finding,
        channel_name="#event-ops"
    )
    assert preview.channel_name == "#event-ops"
    assert "EventOps AI" in preview.title

    result = provider.post_message(preview, idempotency_key="slack_msg_001")
    assert result["status"] == "completed"
    assert result["channel"] == "#event-ops"
    assert "sim_ts_" in result["message_ts"]

    # Duplicate submission returns cached record
    dup = provider.post_message(preview, idempotency_key="slack_msg_001")
    assert dup["message_ts"] == result["message_ts"]


def test_slack_tools_preview_and_governance():
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

    # Preview creates action in pending_approval
    preview_json = preview_slack_message(
        event_id="evt_wit_manhattan_2026",
        category="Risk Assessment",
        item_title="AV Latency Risk",
        item_summary="Backup projector reserved",
        recommended_action="Confirm HDMI tester on site",
        channel="#event-ops"
    )
    preview = json.loads(preview_json)
    assert preview["status"] == "pending_approval"
    action_id = preview["action_id"]

    # Post without approved action should be blocked
    blocked_json = post_slack_message(
        event_id="evt_wit_manhattan_2026",
        action_id=action_id
    )
    blocked = json.loads(blocked_json)
    assert blocked["status"] == "blocked"

    # Approve action
    store.update_integration_action("evt_wit_manhattan_2026", action_id, "approved", approved_by="Director")

    # Post with approved action
    executed_json = post_slack_message(
        event_id="evt_wit_manhattan_2026",
        action_id=action_id
    )
    executed = json.loads(executed_json)
    assert executed["status"] == "completed"
