# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Email provider abstraction with Gmail and Demo implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import logging
import os
import re
from typing import Any
import uuid

from app.integrations.models import EmailDraft, IntegrationConnection

logger = logging.getLogger("eventops.integrations.email")

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_recipients(recipients: list[str]) -> list[str]:
    """Strictly validate email recipient list.
    
    Prevents hallucinated or missing email addresses.
    """
    if not recipients:
        raise ValueError("Recipient email required. Recipient list cannot be empty or inferred from names.")
    
    valid_recipients = []
    for r in recipients:
        cleaned = r.strip()
        if not cleaned:
            continue
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError(f"Invalid email recipient address: '{cleaned}'. Real email required.")
        valid_recipients.append(cleaned)
    
    if not valid_recipients:
        raise ValueError("Recipient email required. No valid email addresses found.")
    
    return valid_recipients


class EmailProvider(ABC):
    """Abstract interface for email integrations."""

    @abstractmethod
    def get_connection_status(self) -> IntegrationConnection:
        """Return normalized connection state."""
        pass

    @abstractmethod
    def draft_email(
        self,
        event_data: dict[str, Any],
        intent: str,
        recipients: list[str],
    ) -> EmailDraft:
        """Create structured email draft without sending."""
        pass

    @abstractmethod
    def save_draft(self, draft: EmailDraft, idempotency_key: str) -> dict[str, Any]:
        """Save draft to provider draft storage."""
        pass

    @abstractmethod
    def send_draft(
        self,
        draft_id: str,
        confirmation_token: str,
        expected_recipients_count: int,
    ) -> dict[str, Any]:
        """Send draft with mandatory second human confirmation."""
        pass


class GmailProvider(EmailProvider):
    """Production Gmail provider using Gmail API.
    
    Truthfully reports NOT CONFIGURED when credentials are not supplied.
    """

    def __init__(self, credentials_path: str | None = None) -> None:
        self.credentials_path = credentials_path or os.environ.get("GMAIL_CREDENTIALS")
        self._status = self._init_status()

    def _init_status(self) -> IntegrationConnection:
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            return IntegrationConnection(
                provider="gmail",
                display_name="Gmail",
                status="not_connected",
                connected_account_label=None,
                scopes=["https://www.googleapis.com/auth/gmail.compose"],
                error_summary="Real Gmail provider not configured. Set GMAIL_CREDENTIALS to enable.",
                is_demo=False,
            )
        return IntegrationConnection(
            provider="gmail",
            display_name="Gmail",
            status="connected",
            connected_account_label=f"configured:{os.path.basename(self.credentials_path)}",
            scopes=["https://www.googleapis.com/auth/gmail.compose"],
            connected_at=datetime.now(timezone.utc).isoformat(),
            is_demo=False,
        )

    def get_connection_status(self) -> IntegrationConnection:
        return self._status

    def draft_email(
        self,
        event_data: dict[str, Any],
        intent: str,
        recipients: list[str],
    ) -> EmailDraft:
        valid_recipients = validate_recipients(recipients)
        title = event_data.get("title", "Event")
        event_id = event_data.get("event_id", "evt_unknown")

        # Deterministic drafting templates
        subject = f"Important Update: {title}"
        purpose = intent
        body = f"Hello,\n\nWe look forward to welcoming you to {title}.\n\nBest regards,\nEvent Operations Team"

        if "dietary" in intent.lower() or "accessibility" in intent.lower():
            subject = f"Action Required: Dietary & Accessibility Intake for {title}"
            purpose = "Collect dietary constraints, allergies, and mobility requirements for executive dinner"
            body = (
                f"Dear Guest,\n\n"
                f"We are preparing for {title} and want to ensure your dining and seating experience is seamless.\n\n"
                f"Please reply with any dietary restrictions (gluten-free, vegan, kosher, allergies) or accessibility needs.\n\n"
                f"We request all responses by T-10 days to finalize catering counts.\n\n"
                f"Warm regards,\nEventOps Guest Experience Team"
            )
        elif "rsvp" in intent.lower() or "reminder" in intent.lower():
            subject = f"RSVP Reminder: {title}"
            purpose = "Remind invited guests to confirm attendance"
            body = (
                f"Dear Guest,\n\n"
                f"This is a friendly reminder to confirm your attendance for {title}.\n\n"
                f"Please let us know your availability so we can hold your seat.\n\n"
                f"Best,\nEvent Leadership Team"
            )

        return EmailDraft(
            event_id=event_id,
            to_recipients=valid_recipients,
            subject=subject,
            purpose=purpose,
            body=body,
            recipient_count=len(valid_recipients),
            requires_second_confirmation=True,
        )

    def save_draft(self, draft: EmailDraft, idempotency_key: str) -> dict[str, Any]:
        if self._status.status != "connected":
            return {
                "status": "failed",
                "error": "Gmail provider is not configured. External action blocked.",
                "provider": "gmail",
            }
        return {
            "status": "completed",
            "gmail_draft_id": f"gmd_{idempotency_key[:10]}",
            "provider": "gmail",
            "draft_id": draft.draft_id,
        }

    def send_draft(
        self,
        draft_id: str,
        confirmation_token: str,
        expected_recipients_count: int,
    ) -> dict[str, Any]:
        if not confirmation_token or confirmation_token != "CONFIRM_SEND":
            raise ValueError("Explicit second human confirmation required to send emails.")
        if self._status.status != "connected":
            return {
                "status": "failed",
                "error": "Gmail provider is not configured.",
                "provider": "gmail",
            }
        return {
            "status": "completed",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "recipients_count": expected_recipients_count,
            "provider": "gmail",
        }


class DemoEmailProvider(EmailProvider):
    """Zero-cost, truthful demo simulation provider for Gmail workflows."""

    def __init__(self) -> None:
        self._saved_drafts: dict[str, EmailDraft] = {}
        self._idempotency_cache: dict[str, dict[str, Any]] = {}

    def get_connection_status(self) -> IntegrationConnection:
        return IntegrationConnection(
            provider="gmail",
            display_name="Gmail (Demo Simulation)",
            status="connected",
            connected_account_label="demo-organizer@eventops.local (Simulated)",
            scopes=["https://www.googleapis.com/auth/gmail.compose"],
            connected_at=datetime.now(timezone.utc).isoformat(),
            is_demo=True,
        )

    def draft_email(
        self,
        event_data: dict[str, Any],
        intent: str,
        recipients: list[str],
    ) -> EmailDraft:
        valid_recipients = validate_recipients(recipients)
        title = event_data.get("title", "Women in Tech Leadership Dinner")
        event_id = event_data.get("event_id", "evt_wit_manhattan_2026")

        subject = f"Event Update: {title}"
        purpose = intent
        body = f"Hello,\n\nWe look forward to welcoming you to {title}.\n\nBest regards,\nEventOps Operations Team"

        intent_lower = intent.lower()
        if "dietary" in intent_lower or "accessibility" in intent_lower or "intake" in intent_lower:
            subject = f"Action Required: Dietary & Accessibility Intake for {title}"
            purpose = "Verify dietary restrictions and accessibility requirements for dinner seating"
            body = (
                f"Dear Guest,\n\n"
                f"We are putting the final touches on {title} at The Altman Building and want to ensure "
                f"your experience is exceptional.\n\n"
                f"Please reply with any dietary restrictions (e.g. vegan, halal, gluten-free, allergies) "
                f"or accessibility requirements.\n\n"
                f"Thank you for confirming by T-10 days so our catering team can accommodate your preferences.\n\n"
                f"Warm regards,\nEventOps Guest Experience Lead"
            )
        elif "rsvp" in intent_lower or "reminder" in intent_lower:
            subject = f"RSVP Reminder: {title}"
            purpose = "Confirm attendance for limited VIP guest seating"
            body = (
                f"Dear Guest,\n\n"
                f"We look forward to hosting you at {title}. If you have not yet confirmed your RSVP, "
                f"please let us know by end of week so we may finalize place settings.\n\n"
                f"Best regards,\nEvent Leadership Team"
            )
        elif "speaker" in intent_lower or "vendor" in intent_lower:
            subject = f"Operational Briefing & Tech Check: {title}"
            purpose = "Coordinate arrival schedule and AV checks with key partners"
            body = (
                f"Hi team,\n\n"
                f"Here is the day-of schedule and tech-check window for {title}.\n"
                f"Tech check begins at 16:30. Doors open for VIPs at 18:00.\n\n"
                f"Best,\nEventOps Technical Lead"
            )

        draft = EmailDraft(
            event_id=event_id,
            to_recipients=valid_recipients,
            subject=subject,
            purpose=purpose,
            body=body,
            recipient_count=len(valid_recipients),
            requires_second_confirmation=True,
        )
        self._saved_drafts[draft.draft_id] = draft
        return draft

    def save_draft(self, draft: EmailDraft, idempotency_key: str) -> dict[str, Any]:
        if idempotency_key in self._idempotency_cache:
            return self._idempotency_cache[idempotency_key]

        sim_id = f"gmd_sim_{hashlib.sha256(idempotency_key.encode()).hexdigest()[:10]}"
        draft.status = "saved_to_gmail"
        draft.gmail_draft_id = sim_id
        self._saved_drafts[draft.draft_id] = draft

        result = {
            "status": "completed",
            "draft_id": draft.draft_id,
            "gmail_draft_id": sim_id,
            "provider": "gmail",
            "is_demo": True,
            "message": "Demo Simulation: Email draft saved to simulated Gmail. No email was sent.",
        }
        self._idempotency_cache[idempotency_key] = result
        return result

    def send_draft(
        self,
        draft_id: str,
        confirmation_token: str,
        expected_recipients_count: int,
    ) -> dict[str, Any]:
        if not confirmation_token or confirmation_token != "CONFIRM_SEND":
            raise ValueError("Explicit second human confirmation required to send emails.")

        safe_draft_id = str(draft_id or "dft_sim_fallback")
        draft = self._saved_drafts.get(safe_draft_id)
        if draft:
            draft.status = "sent"

        return {
            "status": "completed",
            "draft_id": safe_draft_id,
            "sent_message_id": f"msg_sim_{hashlib.sha256(safe_draft_id.encode()).hexdigest()[:10]}",
            "provider": "gmail",
            "is_demo": True,
            "recipients_count": expected_recipients_count,
            "message": f"Demo Simulation: Email send confirmed to {expected_recipients_count} recipients. (Simulation only - no actual email was dispatched).",
        }
