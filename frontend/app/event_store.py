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

"""Firestore persistence, schemas, and in-memory test store for EventOps AI."""

from __future__ import annotations

import datetime
import json
import logging
import os
from typing import Any
import uuid

from google.cloud import firestore
from pydantic import BaseModel, Field

from app.integrations.models import IntegrationAction

logger = logging.getLogger(__name__)

# Firestore project configuration (supports local and cross-project deployment)
FIRESTORE_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-a69f0245a9b4")


def is_in_memory_mode() -> bool:
    """Determine if in-memory store should be used instead of live Firestore."""
    env = os.environ.get("EVENTOPS_ENV", "").lower()
    if env in ("test", "ci", "demo"):
        return True
    if os.environ.get("EVENTOPS_FORCE_DEMO", "").lower() in ("true", "1"):
        return True
    if os.environ.get("EVENTOPS_USE_IN_MEMORY_STORE", "").lower() in ("true", "1"):
        return True
    return False


def _load_in_memory_fixtures() -> tuple[dict[str, EventDossier], dict[str, list[DecisionRecord]]]:
    """Load preserved events and decisions from backups/firestore if available."""
    events: dict[str, EventDossier] = {}
    decisions: dict[str, list[DecisionRecord]] = {}

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    events_path = os.path.join(base_dir, "backups", "firestore", "events.json")
    decisions_path = os.path.join(base_dir, "backups", "firestore", "decisions.json")

    if os.path.exists(events_path):
        try:
            with open(events_path, "r", encoding="utf-8") as f:
                items = json.load(f)
                for it in items:
                    ev = EventDossier.model_validate(it)
                    events[ev.event_id] = ev
        except Exception as e:
            logger.debug("Could not load events fixture: %s", e)

    if os.path.exists(decisions_path):
        try:
            with open(decisions_path, "r", encoding="utf-8") as f:
                items = json.load(f)
                for it in items:
                    dec = DecisionRecord.model_validate(it)
                    decisions.setdefault(dec.event_id, []).append(dec)
        except Exception as e:
            logger.debug("Could not load decisions fixture: %s", e)

    # Ensure seeded demo event exists even if files cannot be read
    if "evt_wit_manhattan_2026" not in events:
        events["evt_wit_manhattan_2026"] = EventDossier(
            event_id="evt_wit_manhattan_2026",
            title="Women in Tech Leadership Dinner",
            location="Private Dining Room, Midtown Manhattan",
            total_budget=4000.0,
            guest_count=30,
            protected_priorities=["Food & Beverage Quality"],
            budget_allocations=[
                {"category": "Venue & Private Dining", "allocated_amount": 1600.0, "is_protected": True},
                {"category": "Curated Chef Tasting Menu", "allocated_amount": 1400.0, "is_protected": False},
                {"category": "Print, Menus & Place Cards", "allocated_amount": 250.0, "is_protected": False},
                {"category": "Staffing & Dedicated Sommelier", "allocated_amount": 350.0, "is_protected": False},
                {"category": "Contingency Reserve", "allocated_amount": 400.0, "is_protected": True},
            ],
            readiness_score=95,
        )

    return events, decisions


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


class InMemoryEventStore:
    """Cloud-independent in-memory event store for testing, CI, and credential-free execution."""

    def __init__(self, seed: bool = True):
        self.events: dict[str, EventDossier] = {}
        self.decisions: dict[str, list[DecisionRecord]] = {}
        self.integration_actions: dict[str, dict[str, IntegrationAction]] = {}
        if seed:
            self._seed()

    def _seed(self):
        evs, decs = _load_in_memory_fixtures()
        self.events.update(evs)
        self.decisions.update(decs)

    def save_event(self, event: EventDossier) -> str:
        """Create or completely overwrite an event document."""
        event.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.events[event.event_id] = event
        logger.info("Saved event %s to InMemoryEventStore", event.event_id)
        return event.event_id

    def create_event(self, event: EventDossier) -> str:
        """Create a new event document in in-memory store."""
        return self.save_event(event)

    def get_event(self, event_id: str) -> EventDossier | None:
        """Fetch an event document from in-memory store."""
        return self.events.get(event_id)

    def update_event_fields(self, event_id: str, updates: dict[str, Any]) -> bool:
        """Partially update specific fields in an event document."""
        if event_id not in self.events:
            return False
        ev = self.events[event_id]
        updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        curr_dict = ev.model_dump()
        curr_dict.update(updates)
        self.events[event_id] = EventDossier.model_validate(curr_dict)
        logger.info("Updated fields on event %s: %s", event_id, list(updates.keys()))
        return True

    def list_events(self, limit: int = 20) -> list[dict[str, Any]]:
        """List summary info for stored events."""
        results = []
        for ev in list(self.events.values())[:limit]:
            results.append({
                "event_id": ev.event_id,
                "title": ev.title,
                "status": ev.status,
                "guest_count": ev.guest_count,
                "total_budget": ev.total_budget,
                "readiness_score": ev.readiness_score,
            })
        return results

    def add_decision(self, decision: DecisionRecord) -> str:
        """Add a decision record into the event's decision store."""
        self.decisions.setdefault(decision.event_id, []).append(decision)
        logger.info("Recorded decision %s for event %s", decision.decision_id, decision.event_id)
        return decision.decision_id

    def get_decisions(self, event_id: str) -> list[DecisionRecord]:
        """Fetch all decisions in chronological order for an event."""
        decs = self.decisions.get(event_id, [])
        return sorted(decs, key=lambda d: d.timestamp)

    def get_decision(self, event_id: str, decision_id: str) -> DecisionRecord | None:
        """Fetch a single decision record by ID."""
        for d in self.decisions.get(event_id, []):
            if d.decision_id == decision_id:
                return d
        return None

    def update_decision_status(
        self,
        event_id: str,
        decision_id: str,
        status: str,
        approved_by: str | None = None,
        resulting_change: str | None = None,
    ) -> bool:
        """Update approval status and resulting change on a decision."""
        for d in self.decisions.get(event_id, []):
            if d.decision_id == decision_id:
                d.approval_status = status
                if approved_by is not None:
                    d.approved_by = approved_by
                if resulting_change is not None:
                    d.resulting_change = resulting_change
                return True
        return False

    def add_integration_action(self, action: IntegrationAction) -> str:
        """Add an integration action record into the in-memory store."""
        self.integration_actions.setdefault(action.event_id, {})[action.action_id] = action
        logger.info(
            "Recorded integration action %s (%s) for event %s",
            action.action_id,
            action.action_type,
            action.event_id,
        )
        return action.action_id

    def get_integration_actions(self, event_id: str) -> list[IntegrationAction]:
        """Fetch all integration actions for an event in chronological order."""
        acts = list(self.integration_actions.get(event_id, {}).values())
        return sorted(acts, key=lambda a: a.requested_at)

    def get_integration_action(self, event_id: str, action_id: str) -> IntegrationAction | None:
        """Fetch a single integration action by ID."""
        return self.integration_actions.get(event_id, {}).get(action_id)

    def update_integration_action(
        self,
        event_id: str,
        action_id: str,
        status: str,
        approved_at: str | None = None,
        approved_by: str | None = None,
        executed_at: str | None = None,
        external_resource_id: str | None = None,
        error_summary: str | None = None,
    ) -> bool:
        """Update status and metadata on an integration action."""
        act = self.get_integration_action(event_id, action_id)
        if not act:
            return False
        act.status = status
        if approved_at is not None:
            act.approved_at = approved_at
        if approved_by is not None:
            act.approved_by = approved_by
        if executed_at is not None:
            act.executed_at = executed_at
        if external_resource_id is not None:
            act.external_resource_id = external_resource_id
        if error_summary is not None:
            act.error_summary = error_summary
        return True


class EventStore:
    """Manages persistent Firestore access for events and decisions, with graceful in-memory fallback."""

    def __init__(self, project_id: str = FIRESTORE_PROJECT_ID):
        self.project_id = project_id
        self._db: firestore.Client | None = None
        self._use_fallback: bool = is_in_memory_mode()
        self._fallback_store: InMemoryEventStore | None = None

    @property
    def fallback(self) -> InMemoryEventStore:
        if self._fallback_store is None:
            self._fallback_store = InMemoryEventStore()
        return self._fallback_store

    @property
    def db(self) -> firestore.Client | None:
        if self._use_fallback:
            return None
        if self._db is None:
            try:
                self._db = firestore.Client(project=self.project_id)
            except Exception as e:
                logger.info("Firestore unavailable (%s); falling back to InMemoryEventStore.", e)
                self._use_fallback = True
                return None
        return self._db

    def save_event(self, event: EventDossier) -> str:
        """Create or completely overwrite an event document."""
        if self._use_fallback or self.db is None:
            return self.fallback.save_event(event)
        try:
            event.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            doc_ref = self.db.collection("events").document(event.event_id)
            doc_ref.set(event.model_dump())
            logger.info("Saved event %s to Firestore", event.event_id)
            return event.event_id
        except Exception as e:
            logger.info("Firestore save_event error (%s); falling back to in-memory store.", e)
            self._use_fallback = True
            return self.fallback.save_event(event)

    def create_event(self, event: EventDossier) -> str:
        """Create a new event document in Firestore."""
        return self.save_event(event)

    def get_event(self, event_id: str) -> EventDossier | None:
        """Fetch an event document from Firestore."""
        if self._use_fallback or self.db is None:
            return self.fallback.get_event(event_id)
        try:
            doc_ref = self.db.collection("events").document(event_id)
            snapshot = doc_ref.get()
            if not snapshot.exists:
                return None
            data = snapshot.to_dict()
            return EventDossier.model_validate(data)
        except Exception as e:
            logger.info("Firestore get_event error (%s); falling back to in-memory store.", e)
            self._use_fallback = True
            return self.fallback.get_event(event_id)

    def update_event_fields(self, event_id: str, updates: dict[str, Any]) -> bool:
        """Partially update specific fields in an event document."""
        if self._use_fallback or self.db is None:
            return self.fallback.update_event_fields(event_id, updates)
        try:
            updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            doc_ref = self.db.collection("events").document(event_id)
            doc_ref.update(updates)
            logger.info("Updated fields on event %s: %s", event_id, list(updates.keys()))
            return True
        except Exception as e:
            logger.info("Firestore update_event_fields error (%s); falling back to in-memory store.", e)
            self._use_fallback = True
            return self.fallback.update_event_fields(event_id, updates)

    def list_events(self, limit: int = 20) -> list[dict[str, Any]]:
        """List summary info for stored events."""
        if self._use_fallback or self.db is None:
            return self.fallback.list_events(limit)
        try:
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
        except Exception as e:
            logger.info("Firestore list_events error (%s); falling back to in-memory store.", e)
            self._use_fallback = True
            return self.fallback.list_events(limit)

    def add_decision(self, decision: DecisionRecord) -> str:
        """Add a decision record into the event's decision subcollection."""
        if self._use_fallback or self.db is None:
            return self.fallback.add_decision(decision)
        try:
            doc_ref = (
                self.db.collection("events")
                .document(decision.event_id)
                .collection("decisions")
                .document(decision.decision_id)
            )
            doc_ref.set(decision.model_dump())
            logger.info("Recorded decision %s for event %s", decision.decision_id, decision.event_id)
            return decision.decision_id
        except Exception as e:
            logger.info("Firestore add_decision error (%s); falling back to in-memory store.", e)
            self._use_fallback = True
            return self.fallback.add_decision(decision)

    def get_decisions(self, event_id: str) -> list[DecisionRecord]:
        """Fetch all decisions in chronological order for an event."""
        if self._use_fallback or self.db is None:
            return self.fallback.get_decisions(event_id)
        try:
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
        except Exception as e:
            logger.info("Firestore get_decisions error (%s); falling back to in-memory store.", e)
            self._use_fallback = True
            return self.fallback.get_decisions(event_id)

    def get_decision(self, event_id: str, decision_id: str) -> DecisionRecord | None:
        """Fetch a single decision record by ID."""
        if self._use_fallback or self.db is None:
            return self.fallback.get_decision(event_id, decision_id)
        try:
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
        except Exception as e:
            logger.info("Firestore get_decision error (%s); falling back to in-memory store.", e)
            self._use_fallback = True
            return self.fallback.get_decision(event_id, decision_id)

    def update_decision_status(
        self,
        event_id: str,
        decision_id: str,
        status: str,
        approved_by: str | None = None,
        resulting_change: str | None = None,
    ) -> bool:
        """Update approval status and resulting change on a decision."""
        if self._use_fallback or self.db is None:
            return self.fallback.update_decision_status(
                event_id, decision_id, status, approved_by, resulting_change
            )
        try:
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
        except Exception as e:
            logger.info("Firestore update_decision_status error (%s); falling back to in-memory store.", e)
            self._use_fallback = True
            return self.fallback.update_decision_status(
                event_id, decision_id, status, approved_by, resulting_change
            )

    def add_integration_action(self, action: IntegrationAction) -> str:
        """Add an integration action record into the event's integration_actions subcollection."""
        if self._use_fallback or self.db is None:
            return self.fallback.add_integration_action(action)
        try:
            doc_ref = (
                self.db.collection("events")
                .document(action.event_id)
                .collection("integration_actions")
                .document(action.action_id)
            )
            doc_ref.set(action.model_dump())
            logger.info(
                "Recorded integration action %s (%s) for event %s",
                action.action_id,
                action.action_type,
                action.event_id,
            )
            return action.action_id
        except Exception as e:
            logger.info("Firestore add_integration_action error (%s); falling back to in-memory store.", e)
            self._use_fallback = True
            return self.fallback.add_integration_action(action)

    def get_integration_actions(self, event_id: str) -> list[IntegrationAction]:
        """Fetch all integration actions for an event in chronological order."""
        if self._use_fallback or self.db is None:
            return self.fallback.get_integration_actions(event_id)
        try:
            docs = (
                self.db.collection("events")
                .document(event_id)
                .collection("integration_actions")
                .order_by("requested_at")
                .stream()
            )
            actions = []
            for doc in docs:
                actions.append(IntegrationAction.model_validate(doc.to_dict()))
            return actions
        except Exception as e:
            logger.info("Firestore get_integration_actions error (%s); falling back to in-memory store.", e)
            self._use_fallback = True
            return self.fallback.get_integration_actions(event_id)

    def get_integration_action(self, event_id: str, action_id: str) -> IntegrationAction | None:
        """Fetch a single integration action by ID."""
        if self._use_fallback or self.db is None:
            return self.fallback.get_integration_action(event_id, action_id)
        try:
            doc_ref = (
                self.db.collection("events")
                .document(event_id)
                .collection("integration_actions")
                .document(action_id)
            )
            snap = doc_ref.get()
            if not snap.exists:
                return None
            return IntegrationAction.model_validate(snap.to_dict())
        except Exception as e:
            logger.info("Firestore get_integration_action error (%s); falling back to in-memory store.", e)
            self._use_fallback = True
            return self.fallback.get_integration_action(event_id, action_id)

    def update_integration_action(
        self,
        event_id: str,
        action_id: str,
        status: str,
        approved_at: str | None = None,
        approved_by: str | None = None,
        executed_at: str | None = None,
        external_resource_id: str | None = None,
        error_summary: str | None = None,
    ) -> bool:
        """Update status and metadata on an integration action."""
        if self._use_fallback or self.db is None:
            return self.fallback.update_integration_action(
                event_id,
                action_id,
                status,
                approved_at=approved_at,
                approved_by=approved_by,
                executed_at=executed_at,
                external_resource_id=external_resource_id,
                error_summary=error_summary,
            )
        try:
            doc_ref = (
                self.db.collection("events")
                .document(event_id)
                .collection("integration_actions")
                .document(action_id)
            )
            updates: dict[str, Any] = {"status": status}
            if approved_at is not None:
                updates["approved_at"] = approved_at
            if approved_by is not None:
                updates["approved_by"] = approved_by
            if executed_at is not None:
                updates["executed_at"] = executed_at
            if external_resource_id is not None:
                updates["external_resource_id"] = external_resource_id
            if error_summary is not None:
                updates["error_summary"] = error_summary
            doc_ref.update(updates)
            return True
        except Exception as e:
            logger.info("Firestore update_integration_action error (%s); falling back to in-memory store.", e)
            self._use_fallback = True
            return self.fallback.update_integration_action(
                event_id,
                action_id,
                status,
                approved_at=approved_at,
                approved_by=approved_by,
                executed_at=executed_at,
                external_resource_id=external_resource_id,
                error_summary=error_summary,
            )


# Default singleton instance for tool usage
_global_event_store: EventStore | InMemoryEventStore | None = None


def get_event_store() -> EventStore | InMemoryEventStore:
    """Return singleton instance of EventStore or InMemoryEventStore."""
    global _global_event_store
    if _global_event_store is None:
        if is_in_memory_mode():
            _global_event_store = InMemoryEventStore()
        else:
            try:
                store = EventStore()
                if store.db is None or store._use_fallback:
                    _global_event_store = InMemoryEventStore()
                else:
                    _global_event_store = store
            except Exception as e:
                logger.info("Firestore unavailable (%s); using InMemoryEventStore.", e)
                _global_event_store = InMemoryEventStore()
    return _global_event_store


def reset_event_store(store: EventStore | InMemoryEventStore | None = None) -> None:
    """Reset the global event store singleton (useful for testing and test isolation)."""
    global _global_event_store
    _global_event_store = store
