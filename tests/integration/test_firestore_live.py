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

"""Live integration tests for EventOps AI Firestore persistence and Cloud Storage assets."""

import pytest
from app.event_store import get_event_store
from app.tools import get_event_dossier, analyze_event_readiness


@pytest.mark.asyncio
async def test_live_firestore_seeded_event():
    """Verify seeded demo event exists in native Firestore with full schema."""
    store = get_event_store()
    event = store.get_event("evt_wit_manhattan_2026")
    assert event is not None
    assert event.event_id == "evt_wit_manhattan_2026"
    assert "Women in Tech" in event.title
    assert event.guest_count == 30
    assert event.total_budget == 4000.0
    assert len(event.guest_journey) == 8
    assert len(event.budget_allocations) == 5
    assert len(event.run_of_show) >= 8
    assert "Food & Beverage Quality" in event.protected_priorities


@pytest.mark.asyncio
async def test_live_firestore_decision_ledger():
    """Verify decision ledger subcollection on seeded event."""
    store = get_event_store()
    decisions = store.get_decisions("evt_wit_manhattan_2026")
    assert len(decisions) >= 1
    init_dec = decisions[0]
    assert init_dec.event_id == "evt_wit_manhattan_2026"
    assert init_dec.approval_status == "approved"
    assert "zero-proof" in init_dec.proposed_change.lower()


@pytest.mark.asyncio
async def test_live_eventops_guard_readiness():
    """Verify EventOps Guard readiness scan against live seeded event."""
    res_str = analyze_event_readiness("evt_wit_manhattan_2026")
    import json
    res = json.loads(res_str)
    assert res["event_id"] == "evt_wit_manhattan_2026"
    assert res["readiness_score"] >= 80
    assert res["status"] == "Ready for Execution"
    assert res["severity_summary"]["critical"] == 0
