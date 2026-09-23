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

"""Firestore persistence and data schemas for EventOps AI."""

from __future__ import annotations

import datetime
import logging
from typing import Any
import uuid

from google.cloud import firestore
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Firestore project configuration (supports local and cross-project deployment)
FIRESTORE_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-a69f0245a9b4")


class DecisionRecord(BaseModel):
    """Decision ledger record for human-in-the-loop governance."""

    decision_id: str = Field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:8]}")
    event_id: str
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    proposed_change: str
    rationale: str
    assumptions: list[str] = Field(default_factory=list)
    expected_impact: str
    approval_status: str = "pending_approval"  # "pending_approval", "approved", "rejected"
    approved_by: str | None = None
    resulting_change: str | None = None
    idempotency_key: str | None = None
    field_updates: dict[str, Any] = Field(default_factory=dict)


class EventDossier(BaseModel):
    """Living, structured Event Dossier for EventOps AI."""

    event_id: str
    title: str
    version: int = 1
    event_type: str = "networking_dinner"
    objective: str = ""
    status: str = "planning"  # "planning", "confirmed", "in_progress", "completed"
    guest_count: int = 30
    location: str = "Manhattan, NY"
    total_budget: float = 4000.0
    currency: str = "USD"
    protected_priorities: list[str] = Field(default_factory=list)
    atmosphere: str = ""
    formality: str = ""
    guest_profile: dict[str, Any] = Field(default_factory=dict)
    guest_journey: list[dict[str, Any]] = Field(default_factory=list)
    budget_allocations: list[dict[str, Any]] = Field(default_factory=list)
    run_of_show: list[dict[str, Any]] = Field(default_factory=list)
    venue_requirements: dict[str, Any] = Field(default_factory=dict)
    food_beverage: dict[str, Any] = Field(default_factory=dict)
    accessibility: dict[str, Any] = Field(default_factory=dict)
    staffing: list[dict[str, Any]] = Field(default_factory=list)
    vendors: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    contingencies: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confirmed_facts: list[str] = Field(default_factory=list)
    readiness_score: int = 0  # 0 to 100
    visual_assets: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class EventStore:
    """Manages persistent Firestore access for events and decisions."""

    def __init__(self, project_id: str = FIRESTORE_PROJECT_ID):
        self.project_id = project_id
        self._db: firestore.Client | None = None

    @property
    def db(self) -> firestore.Client:
        if self._db is None:
            self._db = firestore.Client(project=self.project_id)
        return self._db

    def save_event(self, event: EventDossier) -> str:
        """Create or completely overwrite an event document."""
        event.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        doc_ref = self.db.collection("events").document(event.event_id)
        doc_ref.set(event.model_dump())
        logger.info("Saved event %s to Firestore", event.event_id)
        return event.event_id

    def get_event(self, event_id: str) -> EventDossier | None:
        """Fetch an event document from Firestore."""
        doc_ref = self.db.collection("events").document(event_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict()
        return EventDossier.model_validate(data)

    def update_event_fields(self, event_id: str, updates: dict[str, Any]) -> bool:
        """Partially update specific fields in an event document."""
        updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        doc_ref = self.db.collection("events").document(event_id)
        doc_ref.update(updates)
        logger.info("Updated fields on event %s: %s", event_id, list(updates.keys()))
        return True

    def list_events(self, limit: int = 20) -> list[dict[str, Any]]:
        """List summary info for stored events."""
        docs = self.db.collection("events").limit(limit).stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            results.append({
                "event_id": data.get("event_id", doc.id),
                "title": data.get("title", "Untitled"),
                "status": data.get("status", "planning"),
                "guest_count": data.get("guest_count", 0),
                "total_budget": data.get("total_budget", 0.0),
                "readiness_score": data.get("readiness_score", 0),
            })
        return results

    def add_decision(self, decision: DecisionRecord) -> str:
        """Add a decision record into the event's decision subcollection."""
        doc_ref = (
            self.db.collection("events")
            .document(decision.event_id)
            .collection("decisions")
            .document(decision.decision_id)
        )
        doc_ref.set(decision.model_dump())
        logger.info("Recorded decision %s for event %s", decision.decision_id, decision.event_id)
        return decision.decision_id

    def get_decisions(self, event_id: str) -> list[DecisionRecord]:
        """Fetch all decisions in chronological order for an event."""
        docs = (
            self.db.collection("events")
            .document(event_id)
            .collection("decisions")
            .order_by("timestamp")
            .stream()
        )
        decisions = []
        for doc in docs:
            decisions.append(DecisionRecord.model_validate(doc.to_dict()))
        return decisions

    def get_decision(self, event_id: str, decision_id: str) -> DecisionRecord | None:
        """Fetch a single decision record by ID."""
        doc_ref = (
            self.db.collection("events")
            .document(event_id)
            .collection("decisions")
            .document(decision_id)
        )
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return DecisionRecord.model_validate(snap.to_dict())

    def update_decision_status(
        self,
        event_id: str,
        decision_id: str,
        status: str,
        approved_by: str | None = None,
        resulting_change: str | None = None,
    ) -> bool:
        """Update approval status and resulting change on a decision."""
        doc_ref = (
            self.db.collection("events")
            .document(event_id)
            .collection("decisions")
            .document(decision_id)
        )
        updates: dict[str, Any] = {"approval_status": status}
        if approved_by is not None:
            updates["approved_by"] = approved_by
        if resulting_change is not None:
            updates["resulting_change"] = resulting_change
        doc_ref.update(updates)
        return True


# Default singleton instance for tool usage
_global_event_store: EventStore | None = None


def get_event_store() -> EventStore:
    """Return singleton instance of EventStore."""
    global _global_event_store
    if _global_event_store is None:
        _global_event_store = EventStore()
    return _global_event_store
