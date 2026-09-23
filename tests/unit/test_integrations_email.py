"""Unit tests for Email / Gmail integrations, recipient validation, and draft governance."""

import json
import pytest
from app.integrations.email import validate_recipients, GmailProvider, DemoEmailProvider
from app.integrations.models import EmailDraft
from app.tools import draft_event_email, save_gmail_draft, send_gmail_draft
from app.event_store import get_event_store, EventDossier


def test_validate_recipients_regex():
    valid = validate_recipients(["organizer@eventops.ai", "guest.vip+dinner@domain.co.uk"])
    assert len(valid) == 2

    with pytest.raises(ValueError, match="Invalid email recipient address"):
        validate_recipients(["valid@corp.com", "not-an-email"])

    with pytest.raises(ValueError, match="Recipient email required"):
        validate_recipients([])


def test_gmail_not_configured_when_no_credentials(monkeypatch):
    monkeypatch.delenv("GMAIL_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    provider = GmailProvider()
    status = provider.get_connection_status()
    assert status.status == "not_connected"
    assert status.provider == "gmail"
    assert "not configured" in (status.error_summary or "").lower()


def test_demo_email_provider_draft_first_and_two_step_send():
    provider = DemoEmailProvider()
    status = provider.get_connection_status()
    assert status.status == "connected"
    assert status.is_demo is True

    event_data = {
        "event_id": "evt_email_test",
        "title": "Women in Tech Dinner",
        "location": "New York, NY",
    }

    draft = provider.draft_email(
        event_data=event_data,
        intent="dietary_intake",
        recipients=["vip@example.com"]
    )
    assert draft.status == "draft"
    assert draft.requires_second_confirmation is True
    assert "dft_" in draft.draft_id

    # Save draft
    saved = provider.save_draft(draft, idempotency_key="email_idem_001")
    assert saved["status"] == "completed"
    assert saved["is_demo"] is True
    assert "gmd_sim_" in saved["gmail_draft_id"]

    # Attempting to send without token must raise ValueError
    with pytest.raises(ValueError, match="Explicit second human confirmation required"):
        provider.send_draft(
            draft_id=saved["gmail_draft_id"],
            confirmation_token="WRONG_TOKEN",
            expected_recipients_count=1
        )

    # Sending with CONFIRM_SEND succeeds
    sent = provider.send_draft(
        draft_id=saved["gmail_draft_id"],
        confirmation_token="CONFIRM_SEND",
        expected_recipients_count=1
    )
    assert sent["status"] == "completed"
    assert "msg_sim_" in sent["sent_message_id"]


def test_email_tools_draft_and_governed_send():
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

    # Draft tool (generation only, proposes action in pending_approval)
    draft_res_json = draft_event_email(
        event_id="evt_wit_manhattan_2026",
        intent="dietary_intake",
        recipients=["attendee@example.com"]
    )
    draft_res = json.loads(draft_res_json)
    assert draft_res["status"] == "pending_approval"
    action_id = draft_res["action_id"]
    assert draft_res["draft"]["to_recipients"] == ["attendee@example.com"]

    # Executing save without approval should be blocked
    blocked_json = save_gmail_draft(
        event_id="evt_wit_manhattan_2026",
        action_id=action_id
    )
    blocked = json.loads(blocked_json)
    assert blocked["status"] == "blocked"

    # Approving the action
    store.update_integration_action("evt_wit_manhattan_2026", action_id, "approved", approved_by="Director")

    # Save draft executed
    save_exec_json = save_gmail_draft(
        event_id="evt_wit_manhattan_2026",
        action_id=action_id
    )
    save_exec = json.loads(save_exec_json)
    assert save_exec["status"] == "completed"

    # Send without token fails
    fail_send_json = send_gmail_draft(
        event_id="evt_wit_manhattan_2026",
        action_id=action_id,
        confirmation_token="INVALID"
    )
    fail_send = json.loads(fail_send_json)
    assert fail_send["status"] == "blocked"

    # Send with token succeeds
    ok_send_json = send_gmail_draft(
        event_id="evt_wit_manhattan_2026",
        action_id=action_id,
        confirmation_token="CONFIRM_SEND"
    )
    ok_send = json.loads(ok_send_json)
    assert ok_send["status"] == "completed"
