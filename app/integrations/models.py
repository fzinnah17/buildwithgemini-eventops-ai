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

"""Normalized integration models, action ledger schemas, and telemetry entities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
import uuid

from pydantic import BaseModel, Field


IntegrationStatus = Literal[
    "not_connected", "connecting", "connected", "degraded", "error"
]

ActionStatus = Literal[
    "draft",
    "pending_approval",
    "approved",
    "executing",
    "completed",
    "failed",
    "rejected",
    "cancelled",
]


class IntegrationConnection(BaseModel):
    """Normalized connection status for an external provider."""

    provider: str  # "calendar", "gmail", "slack"
    display_name: str
    status: IntegrationStatus = "not_connected"
    connected_account_label: str | None = None
    scopes: list[str] = Field(default_factory=list)
    connected_at: str | None = None
    last_success_at: str | None = None
    last_error_at: str | None = None
    error_summary: str | None = None
    is_demo: bool = False


class IntegrationAction(BaseModel):
    """Auditable, human-governed external action ledger entry."""

    action_id: str = Field(default_factory=lambda: f"act_{uuid.uuid4().hex[:10]}")
    event_id: str
    provider: Literal["calendar", "gmail", "slack"]
    action_type: str  # e.g., "create_event", "sync_milestones", "save_draft", "send_email", "post_slack_message"
    target: str  # e.g. calendar id, recipient email list, or channel name
    preview: dict[str, Any] = Field(default_factory=dict)
    requested_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approved_at: str | None = None
    approved_by: str | None = None
    executed_at: str | None = None
    status: ActionStatus = "pending_approval"
    external_resource_id: str | None = None
    error_summary: str | None = None
    idempotency_key: str = Field(default_factory=lambda: uuid.uuid4().hex)
    is_demo: bool = False


class CalendarSyncEvent(BaseModel):
    """Structured calendar event representation."""

    title: str
    start_time: str
    end_time: str
    location: str
    description: str
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    calendar_event_id: str | None = None


class EmailDraft(BaseModel):
    """Safe, structured email draft entity."""

    draft_id: str = Field(default_factory=lambda: f"dft_{uuid.uuid4().hex[:10]}")
    event_id: str
    to_recipients: list[str]
    subject: str
    purpose: str
    body: str
    status: Literal["draft", "saved_to_gmail", "sent"] = "draft"
    gmail_draft_id: str | None = None
    recipient_count: int = 0
    requires_second_confirmation: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SlackMessagePayload(BaseModel):
    """Structured operational Slack message."""

    channel_id: str
    channel_name: str
    title: str
    summary: str
    recommended_action: str
    owner: str = "Event Operations Lead"
    due_date: str = "Immediate"
    deep_link: str | None = None
    formatted_text: str = ""


class EventOpsTelemetryEvent(BaseModel):
    """Append-only, privacy-preserving operational telemetry event."""

    telemetry_id: str = Field(default_factory=lambda: f"tel_{uuid.uuid4().hex[:12]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str | None = None
    category: Literal["event_health", "financial", "governance", "system"]
    operation: str
    status: Literal["success", "failure", "pending"] = "success"
    latency_ms: float = 0.0
    provider: str | None = None
    tool_name: str | None = None
    decision_id: str | None = None
    action_id: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
