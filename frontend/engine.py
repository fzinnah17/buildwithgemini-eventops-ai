"""Deterministic Event Operations Calculation Engine for Frontend Proxy.

Provides exact Decimal cents arithmetic for budget rebalancing,
and authoritative readiness score computation with explainable breakdowns.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from schemas import ReadinessBreakdown, ReadinessBreakdownItem


def compute_event_readiness(event_data: dict[str, Any]) -> tuple[int, list[dict[str, Any]], ReadinessBreakdown]:
    """Authoritative deterministic readiness score and explainable breakdown calculation.

    Base score: 100.
    Deductions for identified risk gates or missing fundamentals.
    """
    findings: list[dict[str, Any]] = []
    breakdown_items: list[ReadinessBreakdownItem] = []
    score = 100

    total_budget = float(event_data.get("total_budget", 0.0))
    allocations = event_data.get("budget_allocations") or event_data.get("budget_breakdown") or []
    allocated_sum = sum(float(a.get("allocated_amount", 0.0)) for a in allocations)

    # 1. Budget Alignment Check
    budget_mismatch = round(allocated_sum, 2) != round(total_budget, 2)
    if total_budget <= 0:
        findings.append({
            "category": "Budget Alignment",
            "severity": "Critical",
            "issue": "Event budget ceiling is not defined or is zero.",
            "action": "Set total budget ceiling and line item allocations.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Budget Alignment",
            impact="-25",
            points=-25,
            rationale="Budget ceiling is zero or unallocated.",
            action_needed="Establish baseline budget ceiling.",
        ))
        score -= 25
    elif budget_mismatch:
        variance = abs(allocated_sum - total_budget)
        findings.append({
            "category": "Budget Alignment",
            "severity": "Critical",
            "issue": f"Budget allocations (${allocated_sum:,.2f}) do not match total budget (${total_budget:,.2f}).",
            "action": "Run rebalance_event_budget to reconcile line items.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Budget Alignment",
            impact="-25",
            points=-25,
            rationale=f"Variance of ${variance:,.2f} between line items and total budget ceiling.",
            action_needed="Rebalance line items to 100% match total budget.",
        ))
        score -= 25
    else:
        findings.append({
            "category": "Budget Alignment",
            "severity": "Ready",
            "issue": f"Allocations precisely match total budget ceiling (${total_budget:,.2f}).",
            "action": "None required.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Budget Alignment",
            impact="+0",
            points=0,
            rationale="Allocations fully reconciled to total budget ceiling ($0 variance).",
            action_needed=None,
        ))

    # 2. Contingency Buffer Check
    contingency_items = [a for a in allocations if "contingency" in a.get("category", "").lower()]
    contingency_amount = float(contingency_items[0]["allocated_amount"]) if contingency_items else 0.0
    contingency_pct = (contingency_amount / total_budget) if total_budget > 0 else 0.0

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
            "issue": f"Contingency reserve is {contingency_pct*100:.1f}%. Safe, but tighter than 10% ideal threshold.",
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
            "issue": f"Healthy contingency reserve of {contingency_pct*100:.1f}% (${contingency_amount:,.2f}).",
            "action": "Maintain lock on reserve.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Contingency Reserve",
            impact="+0",
            points=0,
            rationale=f"Healthy contingency reserve of {contingency_pct*100:.1f}% maintained.",
            action_needed=None,
        ))

    # 3. Staffing & Arrival Flow Check
    guest_count = int(event_data.get("guest_count", 0))
    staffing = event_data.get("staffing") or []
    coat_check = [s for s in staffing if "coat" in s.get("role", "").lower() or "greeting" in s.get("role", "").lower()]
    if guest_count >= 25 and not coat_check:
        findings.append({
            "category": "Staffing & Arrival Experience",
            "severity": "Critical",
            "issue": f"No dedicated coat check or greeting attendant identified for {guest_count} guests.",
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
            "issue": f"Dedicated arrival and greeting support confirmed for {guest_count} guests.",
            "action": "Ensure attendant has umbrella bags and numbered claim tags.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Staffing & Arrival Experience",
            impact="+0",
            points=0,
            rationale="Dedicated arrival and greeting staff confirmed.",
            action_needed=None,
        ))

    # 4. Dietary & Allergen Safety Protocol
    fb = event_data.get("food_beverage") or {}
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

    # 5. Acoustic Isolation & Space Type
    venue = event_data.get("venue_requirements") or {}
    space_type = venue.get("space_type", "")
    if "private" not in space_type.lower() or "door" not in space_type.lower():
        findings.append({
            "category": "Atmosphere & Acoustics",
            "severity": "Attention",
            "issue": "Venue space is not confirmed as fully private with closing door; potential ambient noise bleed.",
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

    # 6. Task Ownership (RACI) Check
    tasks = event_data.get("tasks") or []
    unassigned = [t for t in tasks if not t.get("owner") or t.get("owner") == "Unassigned"]
    if unassigned:
        findings.append({
            "category": "Operational Ownership",
            "severity": "Attention",
            "issue": f"{len(unassigned)} operational tasks lack designated owners.",
            "action": "Assign specific owners to all pending milestone tasks.",
        })
        breakdown_items.append(ReadinessBreakdownItem(
            category="Operational Ownership",
            impact="-5",
            points=-5,
            rationale=f"{len(unassigned)} operational tasks lack an accountable owner.",
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


def rebalance_budget_allocations(
    total_budget: float,
    allocations: list[dict[str, Any]],
    target_category: str = "",
    delta_amount: float = 0.0,
) -> tuple[list[dict[str, Any]], float, list[str]]:
    """Exact Decimal rebalance enforcing sum(allocations) == total_budget with 0 variance."""
    total_dec = Decimal(str(total_budget)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    delta_dec = Decimal(str(delta_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    items = [dict(a) for a in allocations]
    target_item = None
    for it in items:
        if target_category and target_category.lower() in it.get("category", "").lower():
            target_item = it
            break

    actions = []
    if target_item and delta_dec != Decimal("0.00"):
        old_val_dec = Decimal(str(target_item.get("allocated_amount", 0.0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        new_val_dec = max(Decimal("0.00"), old_val_dec + delta_dec)
        target_item["allocated_amount"] = float(new_val_dec)
        actions.append(f"Adjusted {target_item['category']}: ${float(old_val_dec):.2f} -> ${float(new_val_dec):.2f}")

        offset_dec = -(new_val_dec - old_val_dec)
        absorbers = [it for it in items if it != target_item and not it.get("is_protected", False)]
        if absorbers:
            share_dec = (offset_dec / Decimal(len(absorbers))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            for a in absorbers:
                prev_a_dec = Decimal(str(a["allocated_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                new_a_dec = max(Decimal("0.00"), prev_a_dec + share_dec)
                a["allocated_amount"] = float(new_a_dec)
                actions.append(f"Compensated {a['category']}: ${float(prev_a_dec):.2f} -> ${float(new_a_dec):.2f}")

    # Enforce Exact Cent Balance Invariant
    alloc_sum_dec = sum(
        Decimal(str(it.get("allocated_amount", 0.0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        for it in items
    )
    variance_dec = total_dec - alloc_sum_dec
    if variance_dec != Decimal("0.00"):
        contingency_items = [it for it in items if "contingency" in it.get("category", "").lower()]
        if contingency_items:
            c_item = contingency_items[0]
            curr_c = Decimal(str(c_item["allocated_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            c_item["allocated_amount"] = float(curr_c + variance_dec)
        elif items:
            first_unprotected = next((it for it in items if not it.get("is_protected")), items[-1])
            curr_a = Decimal(str(first_unprotected["allocated_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            first_unprotected["allocated_amount"] = float(curr_a + variance_dec)

    final_sum_dec = sum(
        Decimal(str(it.get("allocated_amount", 0.0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        for it in items
    )
    final_variance = float(total_dec - final_sum_dec)
    return items, final_variance, actions
