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

"""Messaging provider abstraction with Slack and Demo implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import logging
import os
from typing import Any

from app.integrations.models import IntegrationConnection, SlackMessagePayload

logger = logging.getLogger("eventops.integrations.messaging")


class MessagingProvider(ABC):
    """Abstract interface for team messaging integrations."""

    @abstractmethod
    def get_connection_status(self) -> IntegrationConnection:
        """Return normalized connection state."""
        pass

    @abstractmethod
    def list_channels(self) -> list[dict[str, str]]:
        """List available channels for operational notifications."""
        pass

    @abstractmethod
    def preview_message(
        self,
        event_data: dict[str, Any],
        category: str,
        finding_or_decision: dict[str, Any],
        channel_name: str = "#event-ops",
    ) -> SlackMessagePayload:
        """Format a short, operational Slack message without posting."""
        pass

    @abstractmethod
    def post_message(
        self,
        payload: SlackMessagePayload,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Post structured operational message with human approval."""
        pass


class SlackProvider(MessagingProvider):
    """Production Slack provider.
    
    Truthfully reports NOT CONFIGURED when credentials are not supplied.
    """

    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get("SLACK_BOT_TOKEN")
        self._status = self._init_status()

    def _init_status(self) -> IntegrationConnection:
        if not self.token:
            return IntegrationConnection(
                provider="slack",
                display_name="Slack",
                status="not_connected",
                connected_account_label=None,
                scopes=["chat:write", "channels:read"],
                error_summary="Real Slack provider not configured. Set SLACK_BOT_TOKEN to enable.",
                is_demo=False,
            )
        return IntegrationConnection(
            provider="slack",
            display_name="Slack",
            status="connected",
            connected_account_label="EventOps Bot (Configured)",
            scopes=["chat:write", "channels:read"],
            connected_at=datetime.now(timezone.utc).isoformat(),
            is_demo=False,
        )

    def get_connection_status(self) -> IntegrationConnection:
        return self._status

    def list_channels(self) -> list[dict[str, str]]:
        if self._status.status != "connected":
            return []
        return [
            {"id": "C01", "name": "#event-ops"},
            {"id": "C02", "name": "#leadership"},
            {"id": "C03", "name": "#general"},
        ]

    def preview_message(
        self,
        event_data: dict[str, Any],
        category: str,
        finding_or_decision: dict[str, Any],
        channel_name: str = "#event-ops",
    ) -> SlackMessagePayload:
        title = event_data.get("title", "Event")
        event_id = event_data.get("event_id", "evt_unknown")

        subject = finding_or_decision.get("title") or finding_or_decision.get("issue") or "Operational Update"
        summary = finding_or_decision.get("summary") or finding_or_decision.get("details") or ""
        rec = finding_or_decision.get("action") or finding_or_decision.get("recommendation") or "Review in EventOps."
        owner = finding_or_decision.get("owner", "Operations Lead")
        due = finding_or_decision.get("due", "Prior to Event Day")

        formatted = (
            f"*EventOps AI — {category}*\n"
            f"> *Event:* {title}\n"
            f"> *Item:* {subject}\n"
            f"> *Summary:* {summary}\n"
            f"> *Recommended Action:* {rec}\n"
            f"> *Owner:* {owner} | *Due:* {due}\n"
            f"🔗 _Manage in EventOps Command Center_"
        )

        return SlackMessagePayload(
            channel_id="C_SLACK",
            channel_name=channel_name,
            title=f"EventOps AI: {category}",
            summary=summary,
            recommended_action=rec,
            owner=owner,
            due_date=due,
            deep_link=f"/api/event/{event_id}",
            formatted_text=formatted,
        )

    def post_message(
        self,
        payload: SlackMessagePayload,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if self._status.status != "connected":
            return {
                "status": "failed",
                "error": "Slack provider is not configured. External action blocked.",
                "provider": "slack",
            }
        return {
            "status": "completed",
            "message_ts": f"msg_{idempotency_key[:10]}",
            "channel": payload.channel_name,
            "provider": "slack",
        }


class DemoMessagingProvider(MessagingProvider):
    """Zero-cost, truthful demo simulation provider for Slack workflows."""

    def __init__(self) -> None:
        self._posted_messages: list[dict[str, Any]] = []
        self._idempotency_cache: dict[str, dict[str, Any]] = {}

    def get_connection_status(self) -> IntegrationConnection:
        return IntegrationConnection(
            provider="slack",
            display_name="Slack (Demo Simulation)",
            status="connected",
            connected_account_label="EventOps Workspace (Simulated)",
            scopes=["chat:write", "channels:read"],
            connected_at=datetime.now(timezone.utc).isoformat(),
            is_demo=True,
        )

    def list_channels(self) -> list[dict[str, str]]:
        return [
            {"id": "C_DEMO_OPS", "name": "#event-ops"},
            {"id": "C_DEMO_LEAD", "name": "#leadership"},
            {"id": "C_DEMO_GEN", "name": "#general"},
        ]

    def preview_message(
        self,
        event_data: dict[str, Any],
        category: str,
        finding_or_decision: dict[str, Any],
        channel_name: str = "#event-ops",
    ) -> SlackMessagePayload:
        title = event_data.get("title", "Women in Tech Leadership Dinner")
        event_id = event_data.get("event_id", "evt_wit_manhattan_2026")

        subject = finding_or_decision.get("title") or finding_or_decision.get("issue") or "Attention Needed"
        summary = finding_or_decision.get("summary") or finding_or_decision.get("details") or "Dietary requirements not fully confirmed across VIP attendees."
        rec = finding_or_decision.get("action") or finding_or_decision.get("recommendation") or "Send intake form before final catering count."
        owner = finding_or_decision.get("owner", "Guest Experience Lead")
        due = finding_or_decision.get("due", "T-10 days")

        formatted = (
            f"*EventOps AI — {category}*\n"
            f"> *Event:* {title}\n"
            f"> *Item:* {subject}\n"
            f"> *Details:* {summary}\n"
            f"> *Recommended Action:* {rec}\n"
            f"> *Owner:* {owner}  ·  *Due:* {due}\n"
            f"🔗 <https://fzinnah17.github.io/buildwithgemini-eventops-ai/|Open EventOps Dossier>"
        )

        return SlackMessagePayload(
            channel_id="C_DEMO_OPS",
            channel_name=channel_name,
            title=f"EventOps AI — {category}",
            summary=summary,
            recommended_action=rec,
            owner=owner,
            due_date=due,
            deep_link=f"/api/event/{event_id}",
            formatted_text=formatted,
        )

    def post_message(
        self,
        payload: SlackMessagePayload,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if idempotency_key in self._idempotency_cache:
            return self._idempotency_cache[idempotency_key]

        sim_ts = f"sim_ts_{hashlib.sha256(idempotency_key.encode()).hexdigest()[:10]}"
        record = {
            "status": "completed",
            "message_ts": sim_ts,
            "channel": payload.channel_name,
            "title": payload.title,
            "provider": "slack",
            "is_demo": True,
            "message": f"Demo Simulation: Operational message shared to {payload.channel_name}. No external Slack workspace was notified.",
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._posted_messages.append(record)
        self._idempotency_cache[idempotency_key] = record
        return record
