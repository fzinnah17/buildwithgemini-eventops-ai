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

"""Pydantic schemas for EventOps AI structured response contract."""

from __future__ import annotations

from typing import Any
import uuid

from pydantic import BaseModel, Field


class ReadinessBreakdownItem(BaseModel):
    category: str
    impact: str  # e.g. "+15", "-10"
    points: int
    rationale: str
    action_needed: str | None = None


class ReadinessBreakdown(BaseModel):
    score: int
    base_score: int = 100
    explanation: str
    items: list[ReadinessBreakdownItem] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """Structured, strongly-typed contract for EventOps agent responses."""

    status: str = "ok"  # "ok", "error", "pending_approval"
    response_type: str = "informational"  # "informational", "readiness_scan", "budget_proposal", "timeline_update", "risk_mitigation", "error"
    title: str
    summary: str
    severity: str | None = None  # "critical", "attention", "ready"
    data: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    decision_id: str | None = None
    event_id: str | None = None
    readiness_breakdown: ReadinessBreakdown | None = None
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:8]}")
