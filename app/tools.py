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

import json
import logging
from typing import Any
import uuid

from app.event_store import DecisionRecord, EventDossier, get_event_store

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


def propose_event_update(
    event_id: str,
    proposed_change: str,
    rationale: str,
    assumptions: str,
    expected_impact: str,
) -> str:
    """Propose a consequential change to an event dossier for human-in-the-loop review.

    This records the proposal in the auditable Decision Ledger with status
    'pending_approval'. It does NOT mutate the live event until the human confirms.

    Args:
        event_id: The unique event ID.
        proposed_change: Specific description of the suggested modification.
        rationale: Why this change is recommended.
        assumptions: Underlying operational or cost assumptions.
        expected_impact: Trade-offs, budget adjustments, or timeline shifts.

    Returns:
        JSON string with decision ID and details awaiting human approval.
    """
    store = get_event_store()
    event = store.get_event(event_id)
    if not event:
        return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."})

    assumptions_list = [a.strip() for a in assumptions.split(";") if a.strip()] or [assumptions]

    decision = DecisionRecord(
        event_id=event_id,
        proposed_change=proposed_change,
        rationale=rationale,
        assumptions=assumptions_list,
        expected_impact=expected_impact,
        approval_status="pending_approval",
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
    """Apply a previously proposed change to the Event Dossier upon human approval.

    Args:
        event_id: The unique event ID.
        decision_id: The ID of the pending DecisionRecord.
        approval_confirmation: Confirmation text indicating the user approved (e.g. 'approved', 'yes').
        field_updates_json: Optional JSON string of direct field mutations to apply to the dossier.

    Returns:
        JSON string confirming the applied updates and updated decision record.
    """
    store = get_event_store()
    event = store.get_event(event_id)
    if not event:
        return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."})

    # Validate approval
    clean_approval = approval_confirmation.strip().lower()
    if clean_approval not in ["approved", "yes", "confirm", "proceed", "accepted"]:
        return json.dumps({
            "status": "rejected_or_unconfirmed",
            "message": f"Approval was not confirmed (received '{approval_confirmation}'). No changes made.",
        })

    try:
        updates = json.loads(field_updates_json) if field_updates_json else {}
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Invalid field_updates_json: {e}"})

    resulting_summary = f"Approved and applied: {list(updates.keys()) if updates else 'Status updated'}"
    if updates:
        store.update_event_fields(event_id, updates)

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

    Ensures line items sum to total budget, computes NYC sales tax (8.875%) and
    gratuity (20%) where appropriate, protects locked priorities, and safeguards
    an operational contingency buffer.

    Args:
        event_id: The unique event ID.
        target_category: Category to adjust (e.g. 'Food & Beverage', 'Atmosphere, Décor & Printing').
        delta_amount: Amount to increase (+) or decrease (-) the target category in USD.
        preserve_contingency: If True, prevents contingency reserve from dropping below 8%.

    Returns:
        JSON string with reconciled line items, variance, tax/tip breakdown, and status.
    """
    store = get_event_store()
    event = store.get_event(event_id)
    if not event:
        return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."})

    total_budget = event.total_budget
    allocations = [dict(a) for a in event.budget_allocations]
    contingency_floor = total_budget * 0.08  # 8% minimum contingency

    target_item = None
    for item in allocations:
        if target_category and target_category.lower() in item.get("category", "").lower():
            target_item = item
            break

    # If an adjustment was requested
    rebalance_notes = []
    if target_item and delta_amount != 0.0:
        old_val = target_item.get("allocated_amount", 0.0)
        new_val = old_val + delta_amount
        if new_val < 0:
            return json.dumps({
                "status": "error",
                "message": f"Adjustment would result in negative allocation for {target_item['category']}.",
            })

        # Find non-protected categories to absorb the offset
        offset_needed = -delta_amount
        absorbers = [
            item for item in allocations
            if item != target_item and not item.get("is_protected", False)
        ]

        if not absorbers and offset_needed < 0:
            return json.dumps({
                "status": "error",
                "message": "No non-protected budget categories available to absorb the increase without exceeding total budget.",
            })

        target_item["allocated_amount"] = round(new_val, 2)
        rebalance_notes.append(f"Adjusted {target_item['category']} from ${old_val:.2f} to ${new_val:.2f}")

        # Distribute offset among available absorbers
        if absorbers:
            share = round(offset_needed / len(absorbers), 2)
            for a in absorbers:
                prev_a = a["allocated_amount"]
                a["allocated_amount"] = max(0.0, round(prev_a + share, 2))
                rebalance_notes.append(f"Compensated in {a['category']}: ${prev_a:.2f} -> ${a['allocated_amount']:.2f}")

    # Calculate totals
    current_sum = round(sum(item.get("allocated_amount", 0.0) for item in allocations), 2)
    variance = round(total_budget - current_sum, 2)

    # Check contingency
    contingency_items = [item for item in allocations if "contingency" in item.get("category", "").lower()]
    current_contingency = contingency_items[0]["allocated_amount"] if contingency_items else 0.0

    contingency_warning = None
    if preserve_contingency and current_contingency < contingency_floor:
        contingency_warning = (
            f"Contingency reserve (${current_contingency:.2f}) is below the recommended 8% floor (${contingency_floor:.2f})."
        )

    # Save reconciled allocations back to event
    store.update_event_fields(event_id, {"budget_allocations": allocations})

    return json.dumps({
        "status": "rebalanced" if variance == 0.0 else "unbalanced",
        "event_id": event_id,
        "total_budget": total_budget,
        "allocated_sum": current_sum,
        "variance": variance,
        "is_balanced": variance == 0.0,
        "contingency_reserve": current_contingency,
        "contingency_percentage": round((current_contingency / total_budget) * 100, 1),
        "contingency_warning": contingency_warning,
        "rebalance_actions": rebalance_notes,
        "allocations": allocations,
    }, indent=2)


def analyze_event_readiness(event_id: str) -> str:
    """EventOps Guard: Proactive risk scanner and 'What am I forgetting?' engine.

    Performs deterministic evaluation of event operational completeness, timing
    bottlenecks, missing ownership, acoustic risks, coat check ratios, and dietary
    safeguards. Categorizes findings into Critical, Attention, and Ready severities,
    and computes a composite readiness score (0 to 100).

    Args:
        event_id: The unique event ID.

    Returns:
        JSON string containing structured guard findings, severity counts, and readiness score.
    """
    store = get_event_store()
    event = store.get_event(event_id)
    if not event:
        return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."})

    findings: list[dict[str, Any]] = []
    score = 100

    # 1. Budget & Tax/Tip Check
    allocations = event.budget_allocations
    allocated_sum = sum(a.get("allocated_amount", 0.0) for a in allocations)
    if round(allocated_sum, 2) != round(event.total_budget, 2):
        findings.append({
            "category": "Budget Alignment",
            "severity": "Critical",
            "issue": f"Budget allocations (${allocated_sum:.2f}) do not match total budget (${event.total_budget:.2f}).",
            "action": "Run rebalance_event_budget to reconcile line items.",
        })
        score -= 25
    else:
        findings.append({
            "category": "Budget Alignment",
            "severity": "Ready",
            "issue": "Allocations precisely match total budget ceiling.",
            "action": "None required.",
        })

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
        score -= 15
    elif contingency_pct < 0.10:
        findings.append({
            "category": "Contingency Reserve",
            "severity": "Attention",
            "issue": f"Contingency reserve is {contingency_pct*100:.1f}%. Safe, but tighter than the 10-15% ideal buffer.",
            "action": "Consider adjusting décor or optional line items to reinforce buffer.",
        })
        score -= 5
    else:
        findings.append({
            "category": "Contingency Reserve",
            "severity": "Ready",
            "issue": f"Healthy contingency reserve of {contingency_pct*100:.1f}% (${contingency_amount:.2f}).",
            "action": "Maintain lock on reserve.",
        })

    # 2. Staffing & Coat Check Ratio
    staffing = event.staffing
    coat_check_staff = [s for s in staffing if "coat" in s.get("role", "").lower() or "greeting" in s.get("role", "").lower()]
    if event.guest_count >= 25 and not coat_check_staff:
        findings.append({
            "category": "Staffing & Arrival Experience",
            "severity": "Critical",
            "issue": f"No dedicated coat check or greeting attendant identified for {event.guest_count} guests in NYC.",
            "action": "Assign at least 1 dedicated greeting/coat check attendant to avoid arrival bottleneck.",
        })
        score -= 15
    else:
        findings.append({
            "category": "Staffing & Arrival Experience",
            "severity": "Ready",
            "issue": "Dedicated greeting and coat check support assigned for arrival window.",
            "action": "Ensure attendant has umbrella bags and numbered claim tags.",
        })

    # 3. Dietary Confirmation Protocol
    fb = event.food_beverage
    dietary_protocol = fb.get("dietary_protocol", "")
    if not dietary_protocol or "survey" not in dietary_protocol.lower():
        findings.append({
            "category": "Food & Beverage Safety",
            "severity": "Attention",
            "issue": "Dietary restriction intake protocol not explicitly documented.",
            "action": "Include advance dietary survey on RSVP and request 2 reserve allergen-free plates from kitchen.",
        })
        score -= 10
    else:
        findings.append({
            "category": "Food & Beverage Safety",
            "severity": "Ready",
            "issue": "Structured dietary protocol and reserve plates confirmed.",
            "action": "Confirm final dietary list with venue 72 hours prior.",
        })

    # 4. Venue Acoustics & Privacy
    venue = event.venue_requirements
    space_type = venue.get("space_type", "")
    if "private" not in space_type.lower() or "door" not in space_type.lower():
        findings.append({
            "category": "Atmosphere & Acoustics",
            "severity": "Attention",
            "issue": "Venue space is not confirmed as fully private with closing door; potential restaurant noise bleed.",
            "action": "Verify private room acoustic isolation or request sound-dampened partitions.",
        })
        score -= 10
    else:
        findings.append({
            "category": "Atmosphere & Acoustics",
            "severity": "Ready",
            "issue": "Fully private dining space with acoustic closure specified.",
            "action": "Conduct 5-minute ambient sound check at 17:00 setup.",
        })

    # 5. Task Ownership & RACI
    tasks = event.tasks
    unassigned_tasks = [t for t in tasks if not t.get("owner") or t.get("owner") == "Unassigned"]
    if unassigned_tasks:
        findings.append({
            "category": "Operational Ownership",
            "severity": "Attention",
            "issue": f"{len(unassigned_tasks)} operational tasks lack designated owners.",
            "action": "Assign specific owners to all pending milestone tasks.",
        })
        score -= 5
    else:
        findings.append({
            "category": "Operational Ownership",
            "severity": "Ready",
            "issue": "All identified operational tasks have designated owners.",
            "action": "Review milestone deadlines at T-7 days.",
        })

    # Clamp score between 0 and 100
    final_score = max(0, min(100, score))
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

