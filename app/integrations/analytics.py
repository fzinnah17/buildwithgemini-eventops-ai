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

"""EventOps AI Analytics Service.

Provides deterministic event and portfolio telemetry aggregation across:
- Event Health (readiness, open risks, attention items, assumptions)
- Financial (budget ceiling, variance, contingency buffer, rebalance decisions)
- Governance (human approval outcomes, overrides, external action ledger)
- System / Agent (request volume, tool usage, success rate, median latency)

Enforces strict privacy filtering to prevent guest PII and credentials in telemetry.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import logging
import statistics
from typing import Any

from app.integrations.models import EventOpsTelemetryEvent

logger = logging.getLogger("eventops.analytics")

# Sensitive keys to strip from telemetry metadata
FORBIDDEN_METADATA_KEYS = {
    "email",
    "emails",
    "recipient",
    "recipients",
    "to",
    "guest_name",
    "guest_names",
    "dietary",
    "dietary_restrictions",
    "allergies",
    "accessibility",
    "token",
    "access_token",
    "client_secret",
    "authorization",
    "body",
    "raw_prompt",
}


def sanitize_telemetry_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Sanitize metadata to enforce strict privacy compliance."""
    sanitized: dict[str, Any] = {}
    for k, v in metadata.items():
        if k.lower() in FORBIDDEN_METADATA_KEYS:
            continue
        if isinstance(v, str) and "@" in v and "." in v and len(v) < 80:
            # Drop individual email strings
            continue
        if isinstance(v, (int, float, bool, str)):
            sanitized[k] = v
        elif isinstance(v, list):
            sanitized[k] = f"count:{len(v)}"
        elif isinstance(v, dict):
            sanitized[k] = f"keys:{len(v)}"
    return sanitized


class AnalyticsService:
    """Telemetry logging and deterministic operational metrics service."""

    def __init__(self, max_buffer_size: int = 1000) -> None:
        self._buffer: deque[EventOpsTelemetryEvent] = deque(maxlen=max_buffer_size)

    def record_telemetry(
        self,
        category: str,
        operation: str,
        status: str = "success",
        latency_ms: float = 0.0,
        event_id: str | None = None,
        provider: str | None = None,
        tool_name: str | None = None,
        decision_id: str | None = None,
        action_id: str | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EventOpsTelemetryEvent | None:
        """Record a telemetry event with non-blocking error handling and privacy sanitization."""
        try:
            safe_meta = sanitize_telemetry_metadata(metadata or {})
            event = EventOpsTelemetryEvent(
                event_id=event_id,
                category=category,  # type: ignore
                operation=operation,
                status=status,  # type: ignore
                latency_ms=round(latency_ms, 2),
                provider=provider,
                tool_name=tool_name,
                decision_id=decision_id,
                action_id=action_id,
                request_id=request_id,
                metadata=safe_meta,
            )
            self._buffer.append(event)
            return event
        except Exception as e:
            # Telemetry logging must NEVER break application operations
            logger.warning("Failed to record non-critical analytics telemetry: %s", str(e))
            return None

    def get_event_analytics(
        self,
        event_dossier: dict[str, Any],
        decisions: list[dict[str, Any]],
        integration_actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute comprehensive, explainable metrics for a single event."""
        event_id = event_dossier.get("event_id", "")
        total_budget = float(event_dossier.get("total_budget", 0.0))
        allocations = (
            event_dossier.get("budget_allocations")
            or event_dossier.get("allocations")
            or event_dossier.get("budget_breakdown")
            or []
        )
        allocated_sum = sum(
            float(a.get("allocated_amount") if a.get("allocated_amount") is not None else a.get("amount", 0.0))
            for a in allocations
        )
        variance = round(allocated_sum - total_budget, 2)

        contingency_items = [a for a in allocations if "contingency" in a.get("category", "").lower()]
        contingency_amt = (
            float(contingency_items[0].get("allocated_amount", contingency_items[0].get("amount", 0.0)))
            if contingency_items
            else 0.0
        )
        contingency_pct = round((contingency_amt / total_budget * 100), 1) if total_budget > 0 else 0.0

        risks = event_dossier.get("risks", [])
        critical_risks = len([r for r in risks if r.get("severity", "").lower() == "critical"])
        attention_risks = len([r for r in risks if r.get("severity", "").lower() in ("high", "attention", "medium")])
        resolved_risks = len([r for r in risks if r.get("status", "").lower() in ("resolved", "mitigated")])
        assumptions = event_dossier.get("assumptions", [])

        # Governance Metrics
        approved_decisions = len([d for d in decisions if d.get("status") == "approved"])
        rejected_decisions = len([d for d in decisions if d.get("status") == "rejected"])
        pending_decisions = len([d for d in decisions if d.get("status") in ("pending", "proposed", "pending_approval")])
        total_reviewed = approved_decisions + rejected_decisions
        approval_rate = round((approved_decisions / total_reviewed * 100), 1) if total_reviewed > 0 else None

        # Integration Actions Metrics
        completed_actions = len([a for a in integration_actions if a.get("status") == "completed"])
        pending_actions = len([a for a in integration_actions if a.get("status") == "pending_approval"])
        failed_actions = len([a for a in integration_actions if a.get("status") == "failed"])

        # Filter telemetry for this event
        event_tel = [t for t in self._buffer if t.event_id == event_id]
        total_reqs = len(event_tel)
        success_reqs = len([t for t in event_tel if t.status == "success"])
        latencies = [t.latency_ms for t in event_tel if t.latency_ms > 0]
        median_lat = round(statistics.median(latencies), 1) if latencies else 0.0

        return {
            "scope": "event",
            "event_id": event_id,
            "title": event_dossier.get("title", "Event Dossier"),
            "health": {
                "readiness_score": event_dossier.get("readiness_score"),
                "critical_risks": critical_risks,
                "attention_items": attention_risks,
                "resolved_risks": resolved_risks,
                "open_assumptions": len(assumptions),
                "guest_count": event_dossier.get("guest_count", 0),
            },
            "financial": {
                "total_budget": total_budget,
                "allocated_budget": round(allocated_sum, 2),
                "variance": variance,
                "is_zero_variance": variance == 0.0,
                "contingency_amount": contingency_amt,
                "contingency_pct": contingency_pct,
                "line_items_count": len(allocations),
            },
            "governance": {
                "pending_decisions": pending_decisions,
                "approved_decisions": approved_decisions,
                "rejected_decisions": rejected_decisions,
                "approval_rate_pct": approval_rate,
                "pending_external_actions": pending_actions,
                "completed_external_actions": completed_actions,
                "failed_external_actions": failed_actions,
            },
            "system": {
                "telemetry_events_recorded": total_reqs,
                "success_rate_pct": round((success_reqs / total_reqs * 100), 1) if total_reqs > 0 else None,
                "median_latency_ms": median_lat if latencies else None,
                "telemetry_status": "MEASURED" if total_reqs > 0 else "DEMO / NOT MEASURED",
                "recent_operations": [
                    {
                        "operation": t.operation,
                        "status": t.status,
                        "latency_ms": t.latency_ms,
                        "provider": t.provider or t.tool_name or "-",
                        "timestamp": t.timestamp,
                    }
                    for t in list(event_tel)[-5:]
                ],
            },
            "privacy_compliance": {
                "pii_filtered": True,
                "guest_details_retained": "None (Counters Only)",
                "credential_storage": "Excluded from Analytics",
            },
        }

    def get_portfolio_analytics(
        self,
        all_dossiers: list[dict[str, Any]],
        all_decisions: list[dict[str, Any]],
        all_actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute aggregated metrics across all managed events."""
        events_count = len(all_dossiers)
        scores = [d["readiness_score"] for d in all_dossiers if d.get("readiness_score") is not None]
        avg_readiness = round(sum(scores) / len(scores), 1) if scores else None

        total_portfolio_budget = sum(float(d.get("total_budget", 0.0)) for d in all_dossiers)
        total_guests = sum(int(d.get("guest_count", 0)) for d in all_dossiers)
        total_risks = sum(len([r for r in d.get("risks", []) if r.get("status", "open") == "open"]) for d in all_dossiers)

        approved = len([d for d in all_decisions if d.get("status") == "approved"])
        rejected = len([d for d in all_decisions if d.get("status") == "rejected"])
        pending = len([d for d in all_decisions if d.get("status") in ("pending", "proposed", "pending_approval")])
        total_dec = approved + rejected
        gov_rate = round((approved / total_dec * 100), 1) if total_dec > 0 else None

        tel_list = list(self._buffer)
        total_ops = len(tel_list)
        success_ops = len([t for t in tel_list if t.status == "success"])
        all_lat = [t.latency_ms for t in tel_list if t.latency_ms > 0]
        med_lat = round(statistics.median(all_lat), 1) if all_lat else None

        return {
            "scope": "portfolio",
            "summary": {
                "events_managed": events_count,
                "avg_readiness_score": avg_readiness,
                "total_portfolio_budget": round(total_portfolio_budget, 2),
                "total_guests_managed": total_guests,
                "total_risks_count": total_risks,
            },
            "governance": {
                "pending_decisions": pending,
                "approved_decisions": approved,
                "rejected_decisions": rejected,
                "portfolio_approval_rate_pct": gov_rate,
                "total_external_actions": len(all_actions),
            },
            "events_breakdown": [
                {
                    "event_id": d.get("event_id"),
                    "title": d.get("title"),
                    "readiness_score": d.get("readiness_score"),
                    "total_budget": float(d.get("total_budget", 0.0)),
                    "guest_count": int(d.get("guest_count", 0)),
                }
                for d in all_dossiers
            ],
            "system_reliability": {
                "total_operations": total_ops,
                "system_success_rate_pct": round((success_ops / total_ops * 100), 1) if total_ops > 0 else None,
                "median_latency_ms": med_lat,
                "telemetry_status": "MEASURED" if total_ops > 0 else "DEMO / NOT MEASURED",
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# Singleton service instance
analytics_service = AnalyticsService()
