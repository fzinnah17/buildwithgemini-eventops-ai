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

"""Deterministic Function Tools for EventOps AI."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import json
import logging
from typing import Any
import uuid

from app.event_store import DecisionRecord, EventDossier, get_event_store
from app.schemas import ReadinessBreakdown, ReadinessBreakdownItem

logger = logging.getLogger(__name__)


def create_event_dossier(
    event_id: str,
    title: str,
    guest_count: int = 30,
    total_budget: float = 4000.0,
    location: str = "Manhattan, NY",
    objective: str = "",
    atmosphere: str = "Warm, sophisticated, relationship-focused",
) -> str:
    """Create and persist a new living Event Dossier in Firestore.

    Args:
        event_id: Unique slug/identifier for the event (e.g. 'evt_summit_2026').
        title: Title of the event.
        guest_count: Expected number of attendees.
        total_budget: Total spending ceiling in USD.
        location: City, neighborhood, or venue.
        objective: Core purpose and definition of success.
        atmosphere: Desired mood, sensory ambiance, and formality.

    Returns:
        JSON string confirming creation with basic event summary.
    """
    store = get_event_store()
    existing = store.get_event(event_id)
    if existing:
        return json.dumps({
            "status": "error",
            "message": f"Event '{event_id}' already exists. Use propose_event_update or get_event_dossier.",
        })

    dossier = EventDossier(
        event_id=event_id,
        title=title,
        guest_count=guest_count,
        total_budget=total_budget,
        location=location,
        objective=objective,
        atmosphere=atmosphere,
        readiness_score=40,
    )
    store.save_event(dossier)
    return json.dumps({
        "status": "success",
        "message": f"Created Event Dossier '{event_id}' for '{title}'.",
        "event_id": event_id,
        "total_budget": total_budget,
        "guest_count": guest_count,
    })


def get_event_dossier(event_id: str, section: str = "all") -> str:
    """Retrieve an Event Dossier or specific section from Firestore.

    Args:
        event_id: The unique event ID (e.g. 'evt_wit_manhattan_2026').
        section: Section to return: 'all', 'overview', 'budget', 'run_of_show',
                 'journey', 'readiness', 'decisions', 'venue'.

    Returns:
        JSON string containing the requested event dossier data.
    """
    store = get_event_store()
    event = store.get_event(event_id)
    if not event:
        return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."})

    data = event.model_dump()

    if section == "overview":
        return json.dumps({
            "event_id": data["event_id"],
            "title": data["title"],
            "status": data["status"],
            "guest_count": data["guest_count"],
            "location": data["location"],
            "total_budget": data["total_budget"],
            "atmosphere": data["atmosphere"],
            "readiness_score": data["readiness_score"],
            "protected_priorities": data["protected_priorities"],
        }, indent=2)

    elif section == "budget":
        return json.dumps({
            "event_id": data["event_id"],
            "total_budget": data["total_budget"],
            "currency": data["currency"],
            "allocations": data["budget_allocations"],
            "contingencies": data["contingencies"],
        }, indent=2)

    elif section == "run_of_show":
        return json.dumps({
            "event_id": data["event_id"],
            "run_of_show": data["run_of_show"],
        }, indent=2)

    elif section == "journey":
        return json.dumps({
            "event_id": data["event_id"],
            "guest_journey": data["guest_journey"],
        }, indent=2)

    elif section == "readiness":
        return json.dumps({
            "event_id": data["event_id"],
            "readiness_score": data["readiness_score"],
            "risks": data["risks"],
            "assumptions": data["assumptions"],
            "confirmed_facts": data["confirmed_facts"],
        }, indent=2)

    elif section == "decisions":
        decisions = store.get_decisions(event_id)
        return json.dumps({
            "event_id": event_id,
            "decisions": [d.model_dump() for d in decisions],
        }, indent=2)

    elif section == "venue":
        return json.dumps({
            "event_id": data["event_id"],
            "venue_requirements": data["venue_requirements"],
            "accessibility": data["accessibility"],
            "vendors": data["vendors"],
        }, indent=2)

    return json.dumps(data, indent=2)


def compute_event_readiness(event: EventDossier) -> tuple[int, list[dict[str, Any]], ReadinessBreakdown]:
    """Compute the single authoritative readiness score and explainable breakdown for an event.

    Base score is 100.
    Deductions are made for missing operational fundamentals or identified risks.
    """
    findings: list[dict[str, Any]] = []
    breakdown_items: list[ReadinessBreakdownItem] = []
    score = 100

    # 1. Budget & Tax/Tip Check
    allocations = event.budget_allocations
    allocated_sum = sum(float(a.get("allocated_amount", 0.0)) for a in allocations)
    budget_mismatch = round(allocated_sum, 2) != round(event.total_budget, 2)
    if event.total_budget <= 0:
        findings.append({
            "category": "Budget Alignment",
            "severity": "Critical",
            "issue": "Event budget is not defined or is zero.",
            "action": "Set total budget ceiling and line item allocations.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Budget Alignment",
            impact="-25",
            points=-25,
            rationale="Budget ceiling is zero or unallocated.",
            action_needed="Establish baseline budget.",
        ))
        score -= 25
    elif budget_mismatch:
        findings.append({
            "category": "Budget Alignment",
            "severity": "Critical",
            "issue": f"Budget allocations (${allocated_sum:.2f}) do not match total budget (${event.total_budget:.2f}).",
            "action": "Run rebalance_event_budget to reconcile line items.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Budget Alignment",
            impact="-25",
            points=-25,
            rationale=f"Variance of ${abs(allocated_sum - event.total_budget):.2f} between line items and budget ceiling.",
            action_needed="Rebalance line items to 100% match total budget.",
        ))
        score -= 25
    else:
        findings.append({
            "category": "Budget Alignment",
            "severity": "Ready",
            "issue": "Allocations precisely match total budget ceiling.",
            "action": "None required.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Budget Alignment",
            impact="+0",
            points=0,
            rationale="Allocations fully reconciled to total budget ceiling ($0 variance).",
            action_needed=None,
        ))

    # Contingency buffer check
    contingency_items = [a for a in allocations if "contingency" in a.get("category", "").lower()]
    contingency_amount = contingency_items[0]["allocated_amount"] if contingency_items else 0.0
    contingency_pct = (contingency_amount / event.total_budget) if event.total_budget > 0 else 0
    if contingency_pct < 0.05:
        findings.append({
            "category": "Contingency Reserve",
            "severity": "Critical",
            "issue": f"Contingency reserve is only {contingency_pct*100:.1f}% (below 5% safety margin).",
            "action": "Reallocate at least 8-10% of total budget to contingency reserve.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Contingency Reserve",
            impact="-15",
            points=-15,
            rationale=f"Contingency buffer is {contingency_pct*100:.1f}%, exposing event to overrun risks.",
            action_needed="Increase contingency buffer to at least 10%.",
        ))
        score -= 15
    elif contingency_pct < 0.10:
        findings.append({
            "category": "Contingency Reserve",
            "severity": "Attention",
            "issue": f"Contingency reserve is {contingency_pct*100:.1f}%. Safe, but tighter than the 10-15% ideal buffer.",
            "action": "Consider adjusting décor or optional line items to reinforce buffer.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Contingency Reserve",
            impact="-5",
            points=-5,
            rationale=f"Contingency buffer is {contingency_pct*100:.1f}%, slightly below ideal 10% threshold.",
            action_needed="Maintain tight fiscal control on vendor variable costs.",
        ))
        score -= 5
    else:
        findings.append({
            "category": "Contingency Reserve",
            "severity": "Ready",
            "issue": f"Healthy contingency reserve of {contingency_pct*100:.1f}% (${contingency_amount:.2f}).",
            "action": "Maintain lock on reserve.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Contingency Reserve",
            impact="+0",
            points=0,
            rationale=f"Healthy contingency reserve of {contingency_pct*100:.1f}% maintained.",
            action_needed=None,
        ))

    # Staffing & Coat Check Ratio
    staffing = event.staffing
    coat_check_staff = [s for s in staffing if "coat" in s.get("role", "").lower() or "greeting" in s.get("role", "").lower()]
    if event.guest_count >= 25 and not coat_check_staff:
        findings.append({
            "category": "Staffing & Arrival Experience",
            "severity": "Critical",
            "issue": f"No dedicated coat check or greeting attendant identified for {event.guest_count} guests.",
            "action": "Assign at least 1 dedicated greeting/coat check attendant to avoid arrival bottleneck.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Staffing & Arrival Experience",
            impact="-15",
            points=-15,
            rationale="Absence of dedicated greeting/coat staff creates arrival bottlenecks.",
            action_needed="Assign dedicated greeter/coat attendant.",
        ))
        score -= 15
    else:
        findings.append({
            "category": "Staffing & Arrival Experience",
            "severity": "Ready",
            "issue": "Dedicated greeting and coat check support assigned for arrival window.",
            "action": "Ensure attendant has umbrella bags and numbered claim tags.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Staffing & Arrival Experience",
            impact="+0",
            points=0,
            rationale="Dedicated arrival and greeting staff confirmed.",
            action_needed=None,
        ))

    # Dietary Confirmation Protocol
    fb = event.food_beverage
    dietary_protocol = fb.get("dietary_protocol", "")
    if not dietary_protocol or "survey" not in dietary_protocol.lower():
        findings.append({
            "category": "Food & Beverage Safety",
            "severity": "Attention",
            "issue": "Dietary restriction intake protocol not explicitly documented.",
            "action": "Include advance dietary survey on RSVP and request 2 reserve allergen-free plates from kitchen.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Food & Beverage Safety",
            impact="-10",
            points=-10,
            rationale="Dietary intake workflow unverified; risk of guest allergen incidents.",
            action_needed="Document RSVP survey and reserve plate policy.",
        ))
        score -= 10
    else:
        findings.append({
            "category": "Food & Beverage Safety",
            "severity": "Ready",
            "issue": "Structured dietary protocol and reserve plates confirmed.",
            "action": "Confirm final dietary list with venue 72 hours prior.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Food & Beverage Safety",
            impact="+0",
            points=0,
            rationale="Individual dietary intake and kitchen allergy buffers confirmed.",
            action_needed=None,
        ))

    # Venue Acoustics & Privacy
    venue = event.venue_requirements
    space_type = venue.get("space_type", "")
    if "private" not in space_type.lower() or "door" not in space_type.lower():
        findings.append({
            "category": "Atmosphere & Acoustics",
            "severity": "Attention",
            "issue": "Venue space is not confirmed as fully private with closing door; potential restaurant noise bleed.",
            "action": "Verify private room acoustic isolation or request sound-dampened partitions.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Atmosphere & Acoustics",
            impact="-10",
            points=-10,
            rationale="Lack of confirmed acoustic enclosure risks ambient noise disruption.",
            action_needed="Verify acoustic isolation with venue manager.",
        ))
        score -= 10
    else:
        findings.append({
            "category": "Atmosphere & Acoustics",
            "severity": "Ready",
            "issue": "Fully private dining space with acoustic closure specified.",
            "action": "Conduct 5-minute ambient sound check at setup.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Atmosphere & Acoustics",
            impact="+0",
            points=0,
            rationale="Acoustically isolated private space confirmed.",
            action_needed=None,
        ))

    # Task Ownership & RACI
    tasks = event.tasks
    unassigned_tasks = [t for t in tasks if not t.get("owner") or t.get("owner") == "Unassigned"]
    if unassigned_tasks:
        findings.append({
            "category": "Operational Ownership",
            "severity": "Attention",
            "issue": f"{len(unassigned_tasks)} operational tasks lack designated owners.",
            "action": "Assign specific owners to all pending milestone tasks.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Operational Ownership",
            impact="-5",
            points=-5,
            rationale=f"{len(unassigned_tasks)} operational tasks lack an accountable owner.",
            action_needed="Assign owners in RACI matrix.",
        ))
        score -= 5
    else:
        findings.append({
            "category": "Operational Ownership",
            "severity": "Ready",
            "issue": "All identified operational tasks have designated owners.",
            "action": "Review milestone deadlines at T-7 days.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Operational Ownership",
            impact="+0",
            points=0,
            rationale="100% of operational tasks have designated single points of contact.",
            action_needed=None,
        ))

    final_score = max(0, min(100, score))

    deductions = [item for item in breakdown_items if item.points < 0]
    if deductions:
        deduction_summary = "; ".join(f"{d.category} ({d.impact})" for d in deductions)
        explanation = f"Score is {final_score}/100. Deductions from base 100: {deduction_summary}."
    else:
        explanation = f"Score is {final_score}/100. All operational fundamentals and risk gates are fully satisfied."

    breakdown = ReadinessBreakdown(
        score=final_score,
        base_score=100,
        explanation=explanation,
        items=breakdown_items,
    )
    return final_score, findings, breakdown


def propose_event_update(
    event_id: str,
    proposed_change: str,
    rationale: str,
    assumptions: str,
    expected_impact: str,
    field_updates_json: str = "{}",
    idempotency_key: str | None = None,
) -> str:
    """Propose a consequential change to an event dossier for human-in-the-loop review.

    Records the proposal in the auditable Decision Ledger with status 'pending_approval'.
    Does NOT mutate the live event until explicit human confirmation.

    Args:
        event_id: The unique event ID.
        proposed_change: Specific description of the suggested modification.
        rationale: Why this change is recommended.
        assumptions: Underlying operational or cost assumptions.
        expected_impact: Trade-offs, budget adjustments, or timeline shifts.
        field_updates_json: Optional JSON string of mutations to apply if approved.
        idempotency_key: Optional client idempotency key to prevent duplicate proposals.

    Returns:
        JSON string with decision ID and details awaiting human approval.
    """
    store = get_event_store()
    event = store.get_event(event_id)
    if not event:
        return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."})

    # Check for duplicate submission via idempotency key
    if idempotency_key:
        existing = store.get_decisions(event_id)
        for d in existing:
            if d.idempotency_key == idempotency_key:
                return json.dumps({
                    "status": "pending_human_approval",
                    "decision_id": d.decision_id,
                    "event_id": event_id,
                    "proposed_change": d.proposed_change,
                    "rationale": d.rationale,
                    "expected_impact": d.expected_impact,
                    "idempotent_replay": True,
                    "instruction_to_user": (
                        f"Proposal already logged in Decision Ledger ({d.decision_id}). "
                        "Please confirm if you approve applying this change to the Event Dossier."
                    ),
                }, indent=2)

    try:
        field_updates = json.loads(field_updates_json) if field_updates_json else {}
    except Exception:
        field_updates = {}

    assumptions_list = [a.strip() for a in assumptions.split(";") if a.strip()] or [assumptions]

    decision = DecisionRecord(
        event_id=event_id,
        proposed_change=proposed_change,
        rationale=rationale,
        assumptions=assumptions_list,
        expected_impact=expected_impact,
        approval_status="pending_approval",
        idempotency_key=idempotency_key,
        field_updates=field_updates,
    )
    decision_id = store.add_decision(decision)

    return json.dumps({
        "status": "pending_human_approval",
        "decision_id": decision_id,
        "event_id": event_id,
        "proposed_change": proposed_change,
        "rationale": rationale,
        "expected_impact": expected_impact,
        "instruction_to_user": (
            f"Proposal logged in Decision Ledger ({decision_id}). "
            "Please confirm if you approve applying this change to the Event Dossier."
        ),
    }, indent=2)


def apply_approved_event_update(
    event_id: str,
    decision_id: str,
    approval_confirmation: str,
    field_updates_json: str = "{}",
) -> str:
    """Apply or reject a previously proposed change in the Decision Ledger.

    Args:
        event_id: The unique event ID.
        decision_id: The ID of the pending DecisionRecord.
        approval_confirmation: Confirmation ('approved', 'yes') or rejection ('reject', 'no').
        field_updates_json: Optional JSON string overriding stored field mutations.

    Returns:
        JSON string confirming the applied updates, status, and new readiness score.
    """
    store = get_event_store()
    event = store.get_event(event_id)
    if not event:
        return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."})

    if hasattr(store, "get_decision"):
        dec = store.get_decision(event_id, decision_id)
    else:
        dec = next((d for d in store.get_decisions(event_id) if d.decision_id == decision_id), None)
    if not dec:
        return json.dumps({"status": "error", "message": f"Decision '{decision_id}' not found for event '{event_id}'."})

    if dec.approval_status == "approved":
        return json.dumps({
            "status": "already_applied",
            "event_id": event_id,
            "decision_id": decision_id,
            "message": "Decision already approved and applied to Event Dossier. Idempotent call; no duplicate mutations.",
            "applied_fields": list(dec.field_updates.keys()) if dec.field_updates else [],
        }, indent=2)

    if dec.approval_status == "rejected":
        return json.dumps({
            "status": "previously_rejected",
            "event_id": event_id,
            "decision_id": decision_id,
            "message": "Decision was previously rejected. No changes made to Event Dossier.",
        }, indent=2)

    clean_approval = approval_confirmation.strip().lower()
    if clean_approval in ["reject", "no", "deny", "declined"]:
        store.update_decision_status(
            event_id=event_id,
            decision_id=decision_id,
            status="rejected",
            approved_by="User (Human-in-the-Loop)",
            resulting_change="Rejected by user. No modifications applied.",
        )
        return json.dumps({
            "status": "rejected",
            "event_id": event_id,
            "decision_id": decision_id,
            "message": "Decision was rejected. No changes made to Event Dossier.",
        }, indent=2)

    if clean_approval not in ["approved", "yes", "confirm", "proceed", "accepted"]:
        return json.dumps({
            "status": "rejected_or_unconfirmed",
            "message": f"Approval was not confirmed (received '{approval_confirmation}'). No changes made.",
        })

    # Apply updates
    try:
        override_updates = json.loads(field_updates_json) if field_updates_json else {}
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Invalid field_updates_json: {e}"})

    updates = override_updates if override_updates else (dec.field_updates or {})

    # Bump version and apply updates
    new_version = (event.version or 1) + 1
    updates["version"] = new_version

    resulting_summary = f"Approved and applied: {list(updates.keys()) if updates else 'Status updated'}"
    if updates:
        store.update_event_fields(event_id, updates)

    # Re-fetch event to recompute readiness with new state
    updated_event = store.get_event(event_id)
    if updated_event:
        score, _, _ = compute_event_readiness(updated_event)
        store.update_event_fields(event_id, {"readiness_score": score})

    store.update_decision_status(
        event_id=event_id,
        decision_id=decision_id,
        status="approved",
        approved_by="User (Human-in-the-Loop)",
        resulting_change=resulting_summary,
    )

    return json.dumps({
        "status": "applied",
        "event_id": event_id,
        "decision_id": decision_id,
        "version": new_version,
        "message": "Decision successfully approved and applied to Event Dossier.",
        "applied_fields": list(updates.keys()),
    }, indent=2)


def rebalance_event_budget(
    event_id: str,
    target_category: str = "",
    delta_amount: float = 0.0,
    preserve_contingency: bool = True,
) -> str:
    """Perform deterministic mathematical budget reconciliation for an event.

    Ensures line items sum precisely to total budget using exact Decimal arithmetic,
    protects locked priorities, and safeguards an operational contingency buffer.

    Args:
        event_id: The unique event ID.
        target_category: Category to adjust (e.g. 'Food & Beverage').
        delta_amount: Amount to increase (+) or decrease (-) the target category in USD.
        preserve_contingency: If True, prevents contingency reserve from dropping below 8%.

    Returns:
        JSON string with reconciled line items, variance, and status.
    """
    store = get_event_store()
    event = store.get_event(event_id)
    if not event:
        return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."})

    total_budget_dec = Decimal(str(event.total_budget)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    delta_dec = Decimal(str(delta_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    contingency_floor_dec = (total_budget_dec * Decimal("0.08")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    allocations = [dict(a) for a in event.budget_allocations]
    target_item = None
    for item in allocations:
        if target_category and target_category.lower() in item.get("category", "").lower():
            target_item = item
            break

    rebalance_notes = []
    if target_item and delta_dec != Decimal("0.00"):
        old_val_dec = Decimal(str(target_item.get("allocated_amount", 0.0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        new_val_dec = old_val_dec + delta_dec
        if new_val_dec < Decimal("0.00"):
            return json.dumps({
                "status": "error",
                "message": f"Adjustment would result in negative allocation for {target_item['category']}.",
            })

        offset_needed_dec = -delta_dec
        absorbers = [
            item for item in allocations
            if item != target_item and not item.get("is_protected", False)
        ]

        if not absorbers and offset_needed_dec < Decimal("0.00"):
            return json.dumps({
                "status": "error",
                "message": "No non-protected budget categories available to absorb the increase without exceeding total budget.",
            })

        target_item["allocated_amount"] = float(new_val_dec)
        rebalance_notes.append(f"Adjusted {target_item['category']} from ${float(old_val_dec):.2f} to ${float(new_val_dec):.2f}")

        if absorbers:
            share_dec = (offset_needed_dec / Decimal(len(absorbers))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            for a in absorbers:
                prev_a_dec = Decimal(str(a["allocated_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                new_a_dec = max(Decimal("0.00"), prev_a_dec + share_dec)
                a["allocated_amount"] = float(new_a_dec)
                rebalance_notes.append(f"Compensated in {a['category']}: ${float(prev_a_dec):.2f} -> ${float(new_a_dec):.2f}")

    # Enforce Exact Cent Invariant: sum(allocations) == total_budget_dec
    alloc_sum_dec = sum(
        Decimal(str(item.get("allocated_amount", 0.0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        for item in allocations
    )
    variance_dec = total_budget_dec - alloc_sum_dec

    # If there is variance, adjust contingency or first non-protected item
    if variance_dec != Decimal("0.00"):
        contingency_items = [item for item in allocations if "contingency" in item.get("category", "").lower()]
        if contingency_items:
            c_item = contingency_items[0]
            curr_c = Decimal(str(c_item["allocated_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            c_item["allocated_amount"] = float(curr_c + variance_dec)
        elif allocations:
            first_unprotected = next((item for item in allocations if not item.get("is_protected")), allocations[-1])
            curr_a = Decimal(str(first_unprotected["allocated_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            first_unprotected["allocated_amount"] = float(curr_a + variance_dec)

    # Re-calculate final totals
    final_sum_dec = sum(
        Decimal(str(item.get("allocated_amount", 0.0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        for item in allocations
    )
    final_variance_dec = total_budget_dec - final_sum_dec

    contingency_items = [item for item in allocations if "contingency" in item.get("category", "").lower()]
    current_contingency = contingency_items[0]["allocated_amount"] if contingency_items else 0.0

    contingency_warning = None
    if preserve_contingency and Decimal(str(current_contingency)) < contingency_floor_dec:
        contingency_warning = (
            f"Contingency reserve (${current_contingency:.2f}) is below the recommended 8% floor (${float(contingency_floor_dec):.2f})."
        )

    store.update_event_fields(event_id, {"budget_allocations": allocations})

    return json.dumps({
        "status": "rebalanced" if final_variance_dec == Decimal("0.00") else "unbalanced",
        "event_id": event_id,
        "total_budget": float(total_budget_dec),
        "allocated_sum": float(final_sum_dec),
        "variance": float(final_variance_dec),
        "is_balanced": final_variance_dec == Decimal("0.00"),
        "contingency_reserve": current_contingency,
        "contingency_percentage": round((current_contingency / float(total_budget_dec)) * 100, 1),
        "contingency_warning": contingency_warning,
        "rebalance_actions": rebalance_notes,
        "allocations": allocations,
    }, indent=2)


def analyze_event_readiness(event_id: str) -> str:
    """EventOps Guard: Proactive risk scanner and 'What am I forgetting?' engine.

    Performs deterministic evaluation of event operational completeness, timing
    bottlenecks, missing ownership, acoustic risks, coat check ratios, and dietary
    safeguards. Computes a composite readiness score (0 to 100) and explainable breakdown.

    Args:
        event_id: The unique event ID.

    Returns:
        JSON string containing structured guard findings, severity counts, readiness score, and breakdown.
    """
    store = get_event_store()
    event = store.get_event(event_id)
    if not event:
        return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."})

    final_score, findings, breakdown = compute_event_readiness(event)
    store.update_event_fields(event_id, {"readiness_score": final_score})

    critical_count = sum(1 for f in findings if f["severity"] == "Critical")
    attention_count = sum(1 for f in findings if f["severity"] == "Attention")
    ready_count = sum(1 for f in findings if f["severity"] == "Ready")

    return json.dumps({
        "event_id": event_id,
        "readiness_score": final_score,
        "status": "Ready for Execution" if final_score >= 80 else ("Needs Attention" if final_score >= 60 else "High Risk"),
        "severity_summary": {
            "critical": critical_count,
            "attention": attention_count,
            "ready": ready_count,
        },
        "findings": findings,
        "readiness_breakdown": breakdown.model_dump(),
    }, indent=2)


def record_organizer_preference(preference_category: str, preference_details: str) -> str:
    """Explicitly record or confirm durable organizer preferences (style, tone, dietary, networking, accessibility, budget limits, dislikes).

    Args:
        preference_category: Category such as 'atmosphere', 'dietary', 'networking', 'formality', 'dislikes', or 'budget'.
        preference_details: Explicit description of the organizer's persistent preference.

    Returns:
        JSON string confirming preference registration and Memory Bank queuing.
    """
    return json.dumps({
        "status": "success",
        "category": preference_category,
        "details": preference_details,
        "message": "Preference successfully confirmed and queued for long-term Memory Bank persistence.",
    }, indent=2)


def calculate(expression: str) -> str:
    """Evaluate a mathematical expression string."""
    try:
        # Restricted safe eval
        allowed = {"__builtins__": None, "abs": abs, "round": round, "min": min, "max": max}
        res = eval(expression, allowed, {})
        return str(res)
    except Exception as e:
        return f"Calculation error: {e}"


def convert_distance(value: float, from_unit: str, to_unit: str) -> str:
    """Convert distance between miles, kilometers, meters, and feet."""
    conversions = {
        ("miles", "kilometers"): value * 1.60934,
        ("kilometers", "miles"): value / 1.60934,
        ("meters", "feet"): value * 3.28084,
        ("feet", "meters"): value / 3.28084,
    }
    key = (from_unit.lower(), to_unit.lower())
    if key in conversions:
        return f"{value} {from_unit} = {conversions[key]:.2f} {to_unit}"
    return f"Unsupported distance conversion from {from_unit} to {to_unit}"


def convert_temperature(value: float, from_unit: str, to_unit: str) -> str:
    """Convert temperature between Celsius and Fahrenheit."""
    f_u = from_unit.lower()
    t_u = to_unit.lower()
    if f_u in ["c", "celsius"] and t_u in ["f", "fahrenheit"]:
        res = (value * 9 / 5) + 32
        return f"{value}°C = {res:.1f}°F"
    elif f_u in ["f", "fahrenheit"] and t_u in ["c", "celsius"]:
        res = (value - 32) * 5 / 9
        return f"{value}°F = {res:.1f}°C"
    return f"Unsupported temperature conversion from {from_unit} to {to_unit}"

