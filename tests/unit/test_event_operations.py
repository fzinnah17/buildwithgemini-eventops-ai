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

"""Comprehensive Unit Tests for EventOps AI domain logic, schemas, and deterministic tools."""

import json
import pytest

from app.event_store import DecisionRecord, EventDossier
from app.rag_tool import consult_operations_playbook
from app.tools import (
    analyze_event_readiness,
    apply_approved_event_update,
    create_event_dossier,
    get_event_dossier,
    propose_event_update,
    rebalance_event_budget,
)


class DummyEventStore:
    """Mock store for testing tools in isolation."""

    def __init__(self):
        self.events = {}
        self.decisions = {}

    def save_event(self, event: EventDossier):
        self.events[event.event_id] = event
        return event.event_id

    def get_event(self, event_id: str):
        return self.events.get(event_id)

    def update_event_fields(self, event_id: str, updates: dict):
        if event_id in self.events:
            for k, v in updates.items():
                setattr(self.events[event_id], k, v)
            return True
        return False

    def add_decision(self, decision: DecisionRecord):
        self.decisions.setdefault(decision.event_id, []).append(decision)
        return decision.decision_id

    def get_decisions(self, event_id: str):
        return self.decisions.get(event_id, [])

    def update_decision_status(self, event_id: str, decision_id: str, status: str, approved_by=None, resulting_change=None):
        for d in self.decisions.get(event_id, []):
            if d.decision_id == decision_id:
                d.approval_status = status
                d.approved_by = approved_by
                d.resulting_change = resulting_change
                return True
        return False


@pytest.fixture
def mock_store(monkeypatch):
    store = DummyEventStore()
    monkeypatch.setattr("app.tools.get_event_store", lambda: store)
    return store


def test_event_dossier_schema_validation():
    """Point 2: Verify full schema validation and default fields."""
    dossier = EventDossier(
        event_id="test_evt_01",
        title="Test Executive Dinner",
        total_budget=5000.0,
        guest_count=25,
    )
    assert dossier.event_id == "test_evt_01"
    assert dossier.currency == "USD"
    assert dossier.readiness_score == 0
    assert isinstance(dossier.guest_journey, list)
    assert isinstance(dossier.budget_allocations, list)


def test_decision_record_schema():
    """Point 4 & 6: Verify decision ledger record structure and pending status."""
    decision = DecisionRecord(
        event_id="test_evt_01",
        proposed_change="Increase dessert budget by $200",
        rationale="Guest request",
        expected_impact="Reduces contingency buffer",
    )
    assert decision.approval_status == "pending_approval"
    assert decision.approved_by is None
    assert decision.decision_id.startswith("dec_")


def test_create_and_get_event_dossier(mock_store):
    """Point 1: Test creating and retrieving event dossier."""
    res_str = create_event_dossier(
        event_id="evt_unit_01",
        title="Leadership Summit Dinner",
        guest_count=20,
        total_budget=3000.0,
    )
    res = json.loads(res_str)
    assert res["status"] == "success"
    assert res["event_id"] == "evt_unit_01"

    # Fetch overview section
    ov_str = get_event_dossier("evt_unit_01", section="overview")
    ov = json.loads(ov_str)
    assert ov["event_id"] == "evt_unit_01"
    assert ov["total_budget"] == 3000.0


def test_propose_event_update_hitl(mock_store):
    """Point 5 & 6: Consequential change proposal enters pending_approval."""
    create_event_dossier("evt_unit_02", "Annual Gala", 30, 4000.0)

    prop_str = propose_event_update(
        event_id="evt_unit_02",
        proposed_change="Add live cellist for cocktail hour (+$300)",
        rationale="Enhances arrival atmosphere",
        assumptions="Performer available for 1 hour",
        expected_impact="Contingency drops from $400 to $100",
    )
    prop = json.loads(prop_str)
    assert prop["status"] == "pending_human_approval"
    assert "decision_id" in prop
    dec_id = prop["decision_id"]

    # Verify stored decision is pending
    decisions = mock_store.get_decisions("evt_unit_02")
    assert len(decisions) == 1
    assert decisions[0].decision_id == dec_id
    assert decisions[0].approval_status == "pending_approval"


def test_apply_approved_event_update_rejection(mock_store):
    """Point 7: Rejection or unconfirmed response blocks change execution."""
    create_event_dossier("evt_unit_03", "Investor Dinner", 15, 2500.0)
    prop = json.loads(propose_event_update("evt_unit_03", "Upgrade wine", "Better vintage", "", "Higher cost"))

    # Attempt to apply with negative / unconfirmed confirmation
    res_str = apply_approved_event_update(
        event_id="evt_unit_03",
        decision_id=prop["decision_id"],
        approval_confirmation="no, do not proceed",
        field_updates_json=json.dumps({"total_budget": 3000.0}),
    )
    res = json.loads(res_str)
    assert res["status"] == "rejected_or_unconfirmed"
    assert mock_store.get_event("evt_unit_03").total_budget == 2500.0


def test_apply_approved_event_update_success(mock_store):
    """Point 8: Human confirmation approves decision and applies updates."""
    create_event_dossier("evt_unit_04", "Product Launch Dinner", 30, 4000.0)
    prop = json.loads(propose_event_update("evt_unit_04", "Expand headcount", "Add 5 guests", "", "Higher F&B"))

    res_str = apply_approved_event_update(
        event_id="evt_unit_04",
        decision_id=prop["decision_id"],
        approval_confirmation="approved",
        field_updates_json=json.dumps({"guest_count": 35}),
    )
    res = json.loads(res_str)
    assert res["status"] == "applied"
    assert mock_store.get_event("evt_unit_04").guest_count == 35

    # Check decision record updated
    dec = mock_store.get_decisions("evt_unit_04")[0]
    assert dec.approval_status == "approved"
    assert "User" in dec.approved_by


def test_rebalance_event_budget_arithmetic(mock_store):
    """Point 9 & 10: Deterministic arithmetic and preservation of protected lines."""
    dossier = EventDossier(
        event_id="evt_budget_01",
        title="Budget Test Event",
        total_budget=4000.0,
        budget_allocations=[
            {"category": "Food & Beverage", "allocated_amount": 2000.0, "is_protected": True},
            {"category": "Venue Space", "allocated_amount": 1000.0, "is_protected": False},
            {"category": "Decor & Printing", "allocated_amount": 500.0, "is_protected": False},
            {"category": "Contingency Reserve", "allocated_amount": 500.0, "is_protected": True},
        ],
    )
    mock_store.save_event(dossier)

    # Increase Venue by $200
    res_str = rebalance_event_budget(
        event_id="evt_budget_01",
        target_category="Venue Space",
        delta_amount=200.0,
        preserve_contingency=True,
    )
    res = json.loads(res_str)
    assert res["is_balanced"] is True
    assert res["allocated_sum"] == 4000.0

    # Ensure protected Food & Beverage was NOT modified
    allocs = {a["category"]: a["allocated_amount"] for a in res["allocations"]}
    assert allocs["Food & Beverage"] == 2000.0
    assert allocs["Venue Space"] == 1200.0
    # Non-protected Decor & Printing should have absorbed the $200 offset
    assert allocs["Decor & Printing"] == 300.0


def test_eventops_guard_readiness_scan(mock_store):
    """Point 11 & 12: Readiness score computation and severity classification."""
    # Test event with deliberate missing coat check and tight contingency
    dossier = EventDossier(
        event_id="evt_guard_01",
        title="Guard Risk Event",
        guest_count=35,
        total_budget=4000.0,
        budget_allocations=[
            {"category": "Food & Beverage", "allocated_amount": 3900.0},
            {"category": "Contingency Reserve", "allocated_amount": 100.0},  # 2.5% -> Critical (<5%)
        ],
        staffing=[],  # 35 guests with NO coat check -> Critical
        food_beverage={"dietary_protocol": "Standard catering"},  # No survey -> Attention
        venue_requirements={"space_type": "Shared dining area"},  # Not private -> Attention
        tasks=[{"task_id": "t1", "description": "Buy wine", "owner": "Unassigned"}],  # Unassigned -> Attention
    )
    mock_store.save_event(dossier)

    scan_str = analyze_event_readiness("evt_guard_01")
    scan = json.loads(scan_str)

    assert scan["event_id"] == "evt_guard_01"
    assert scan["severity_summary"]["critical"] >= 2  # contingency (<5%) + coat check
    assert scan["severity_summary"]["attention"] >= 3  # dietary, venue acoustics, unassigned tasks
    assert scan["readiness_score"] < 60
    assert scan["status"] == "High Risk"


def test_consult_operations_playbook_grounding():
    """Point 14: Operations Playbook grounded retrieval returns relevant guidelines."""
    res = consult_operations_playbook("arrival decompression buffer and coat check")
    assert "PLAYBOOK" in res
    assert "coat check" in res.lower()
