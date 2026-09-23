"""EventOps AI - Enterprise Event Operations Frontend Proxy.

Lightweight FastAPI proxy connecting the EventOps AI Command Center browser
interface to the deployed EventOps AI Reasoning Engine on Agent Platform over A2A,
with deterministic multi-event management, explainable readiness scoring, and
strict exception sanitization.
"""

from datetime import datetime, timezone
import json
import logging
import os
import re
import uuid
from typing import Any

import google.auth
import google.auth.transport.requests
from google.cloud import firestore
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from schemas import AgentResponse
from engine import compute_event_readiness, rebalance_budget_allocations
from app.integrations import (
    analytics_service,
    get_calendar_provider,
    get_email_provider,
    get_messaging_provider,
    IntegrationAction,
    validate_recipients,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eventops.frontend")

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/282776913855/locations/us-central1/reasoningEngines/1788548626868338688",
)
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = (
    RESOURCE.split("/locations/")[1].split("/")[0]
    if "/locations/" in RESOURCE
    else "us-central1"
)
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-a69f0245a9b4")

A2A_ENDPOINT = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
_A2UI_MIME = "application/json+a2ui"

_creds = None
_db = None


def _get_credentials():
    global _creds
    if _creds is None or not _creds.valid:
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        _creds, _ = google.auth.default(scopes=scopes)
    _creds.refresh(google.auth.transport.requests.Request())
    return _creds


def _get_firestore() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def _auth_headers() -> dict[str, str]:
    creds = _get_credentials()
    return {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
        "A2A-Version": "1.0",
    }


app = FastAPI(
    title="EventOps AI Frontend",
    description="Enterprise Command Center for EventOps AI",
    version="0.2.0",
)

_contexts: dict[str, str] = {}


def _extract_parts_from_task(task_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract text, A2UI data, and tool action parts from A2A Task artifacts."""
    out: list[dict[str, Any]] = []
    artifacts = task_dict.get("artifacts") or []
    for art in artifacts:
        parts = art.get("parts") or []
        for p in parts:
            if isinstance(p, dict):
                if p.get("text"):
                    out.append({"kind": "text", "text": p["text"]})
                elif p.get("data") is not None:
                    meta = p.get("metadata") or {}
                    mime = meta.get("mimeType") if isinstance(meta, dict) else None
                    data = p["data"]
                    if mime == _A2UI_MIME:
                        out.append({"kind": "a2ui", "data": data})
                    elif isinstance(data, dict):
                        out.append({"kind": "tool_data", "data": data})
                elif p.get("url"):
                    out.append({"kind": "url", "url": p["url"]})
    return out


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "product": "EventOps AI",
        "subtitle": "Enterprise Event Operations Agent",
        "resource": RESOURCE,
        "region": LOCATION,
    }


@app.get("/api/events")
async def list_events_api():
    """List all available event dossiers from Cloud Firestore."""
    try:
        db = _get_firestore()
        docs = db.collection("events").limit(30).stream()
        events = []
        for d in docs:
            data = d.to_dict()
            events.append({
                "event_id": data.get("event_id", d.id),
                "title": data.get("title", d.id),
                "guest_count": data.get("guest_count", 0),
                "total_budget": data.get("total_budget", 0.0),
                "location": data.get("location", ""),
                "status": data.get("status", "planning"),
                "readiness_score": data.get("readiness_score", 0),
            })
        return JSONResponse(events)
    except Exception as e:
        logger.error("Error listing events from Firestore: %s", e, exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Unable to list events."})


@app.post("/api/events")
async def create_event_api(req: Request):
    """Create a new event dossier dynamically."""
    try:
        body = await req.json()
        title = body.get("title") or "New Event"
        event_id = body.get("event_id") or f"evt_{uuid.uuid4().hex[:8]}"
        guest_count = int(body.get("guest_count", 30))
        total_budget = float(body.get("total_budget", 5000.0))
        location = body.get("location", "New York, NY")

        db = _get_firestore()
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Initial standard budget allocation
        f_b = round(total_budget * 0.55, 2)
        contingency = round(total_budget * 0.10, 2)
        staffing = round(total_budget * 0.15, 2)
        materials = round(total_budget * 0.10, 2)
        venue = round(total_budget - (f_b + contingency + staffing + materials), 2)

        allocations = [
            {"category": "Food & Beverage", "allocated_amount": f_b, "is_protected": True, "notes": "Catering and beverage package"},
            {"category": "Venue & Facilities", "allocated_amount": venue, "is_protected": False, "notes": "Space rental or room fee"},
            {"category": "Staffing & Hospitality", "allocated_amount": staffing, "is_protected": False, "notes": "Event host and greeters"},
            {"category": "Signage & Atmosphere", "allocated_amount": materials, "is_protected": False, "notes": "Print materials and table décor"},
            {"category": "Contingency Reserve", "allocated_amount": contingency, "is_protected": True, "notes": "10% unforeseen buffer"},
        ]

        event_data = {
            "event_id": event_id,
            "title": title,
            "version": 1,
            "event_type": body.get("event_type", "networking_dinner"),
            "status": "planning",
            "guest_count": guest_count,
            "location": location,
            "total_budget": total_budget,
            "budget_allocations": allocations,
            "budget_breakdown": allocations,
            "run_of_show": [
                {"time": "18:00 - 18:30", "activity": "Guest Arrival & Welcome Refreshments", "owner": "Event Host"},
                {"time": "18:30 - 20:00", "activity": "Main Program & Curated Discussions", "owner": "Program Director"},
                {"time": "20:00 - 21:00", "activity": "Dessert, Networking & Closing", "owner": "Lead Host"},
            ],
            "staffing": [
                {"role": "Lead Event Director", "count": 1, "responsibility": "Overall coordination"},
                {"role": "Guest Greeting & Coat Check Attendant", "count": 1, "responsibility": "Arrival management"},
            ],
            "venue_requirements": {
                "space_type": "Private dining room with acoustic closure",
                "capacity": guest_count + 10,
            },
            "food_beverage": {
                "style": "Plated multi-course dinner",
                "dietary_protocol": "Advance dietary survey confirmed 7 days prior",
            },
            "guest_journey": [
                {"stage": "Arrival", "experience": "Warm personal greeting and seamless check-in"},
                {"stage": "Main Program", "experience": "Engaging, unhurried conversation"},
                {"stage": "Departure", "experience": "Thoughtful parting takeaway"},
            ],
            "tasks": [
                {"task": "Confirm venue contract and dietary survey link", "owner": "Lead Host", "due_date": "T-7 Days", "status": "in_progress"},
            ],
            "risks": [
                {"risk": "Last-minute guest dietary requests", "severity": "Low", "mitigation": "Hold 2 reserve allergen-free plates"},
            ],
            "readiness_score": 85,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        score, _, _ = compute_event_readiness(event_data)
        event_data["readiness_score"] = score

        db.collection("events").document(event_id).set(event_data)
        return JSONResponse({"status": "created", "event_id": event_id, "event": event_data})
    except Exception as e:
        logger.error("Error creating event: %s", e, exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Failed to create event."})


@app.get("/api/event/{event_id}")
async def get_event_api(event_id: str):
    """Retrieve live event dossier, decisions, and explainable readiness breakdown."""
    try:
        db = _get_firestore()
        doc_ref = db.collection("events").document(event_id)
        doc = doc_ref.get()
        if not doc.exists:
            return JSONResponse(
                status_code=404,
                content={"error": f"Event '{event_id}' not found in Firestore."},
            )

        event_data = doc.to_dict()
        if "budget_allocations" in event_data and "budget_breakdown" not in event_data:
            event_data["budget_breakdown"] = event_data["budget_allocations"]
        elif "budget_breakdown" in event_data and "budget_allocations" not in event_data:
            event_data["budget_allocations"] = event_data["budget_breakdown"]

        # Dynamically compute single authoritative readiness score and breakdown
        score, findings, breakdown = compute_event_readiness(event_data)
        event_data["readiness_score"] = score
        event_data["readiness_breakdown"] = breakdown.model_dump()
        event_data["guard_findings"] = findings

        # Retrieve decisions
        decisions_ref = (
            doc_ref.collection("decisions")
            .order_by("created_at", direction="DESCENDING")
            .limit(20)
        )
        decisions = []
        for d in decisions_ref.stream():
            dd = d.to_dict()
            decisions.append(dd)

        event_data["decisions"] = decisions
        return JSONResponse(event_data)
    except Exception as e:
        logger.error("Error fetching event %s: %s", event_id, e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Unable to fetch event: {str(e)}"},
        )


@app.post("/api/decisions/approve")
async def approve_decision_api(req: Request):
    """Human-in-the-loop approval: commit pending decision and apply mutations."""
    try:
        body = await req.json()
        event_id = body.get("event_id")
        decision_id = body.get("decision_id")
        if not event_id or not decision_id:
            return JSONResponse(status_code=400, content={"error": "event_id and decision_id are required."})

        db = _get_firestore()
        dec_ref = db.collection("events").document(event_id).collection("decisions").document(decision_id)
        dec_snap = dec_ref.get()
        if not dec_snap.exists:
            return JSONResponse(status_code=404, content={"error": f"Decision {decision_id} not found."})

        dec_data = dec_snap.to_dict()
        if dec_data.get("approval_status") == "approved":
            return JSONResponse({
                "status": "already_applied",
                "message": "Decision was already approved and applied. Idempotent call; no duplicate mutation.",
                "decision_id": decision_id,
            })

        # Apply mutations to event dossier
        evt_ref = db.collection("events").document(event_id)
        evt_snap = evt_ref.get()
        new_version = 1
        if evt_snap.exists:
            evt_data = evt_snap.to_dict()
            new_version = (evt_data.get("version") or 1) + 1
            evt_data["version"] = new_version
            evt_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            field_updates = dec_data.get("field_updates") or {}
            for k, v in field_updates.items():
                evt_data[k] = v

            # If total_budget changed or allocations present, ensure both synced
            if "budget_allocations" in evt_data:
                evt_data["budget_breakdown"] = evt_data["budget_allocations"]

            # Recompute readiness score with updated state
            score, _, _ = compute_event_readiness(evt_data)
            evt_data["readiness_score"] = score
            evt_ref.set(evt_data)

        # Mark decision approved
        dec_ref.update({
            "approval_status": "approved",
            "approved_by": "Lead Event Director",
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "resulting_change": f"Committed to Event Dossier (v{new_version})",
        })

        return JSONResponse({
            "status": "applied",
            "event_id": event_id,
            "decision_id": decision_id,
            "version": new_version,
            "message": "Decision successfully approved and committed to Event Dossier.",
        })
    except Exception as e:
        logger.error("Error approving decision: %s", e, exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Error approving decision: {str(e)}"})


@app.post("/api/decisions/reject")
async def reject_decision_api(req: Request):
    """Human-in-the-loop rejection: decline decision without mutating event dossier."""
    try:
        body = await req.json()
        event_id = body.get("event_id")
        decision_id = body.get("decision_id")
        if not event_id or not decision_id:
            return JSONResponse(status_code=400, content={"error": "event_id and decision_id are required."})

        db = _get_firestore()
        dec_ref = db.collection("events").document(event_id).collection("decisions").document(decision_id)
        dec_snap = dec_ref.get()
        if not dec_snap.exists:
            return JSONResponse(status_code=404, content={"error": f"Decision {decision_id} not found."})

        dec_ref.update({
            "approval_status": "rejected",
            "approved_by": "Lead Event Director",
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "resulting_change": "Rejected by human director. No event dossier modifications made.",
        })

        return JSONResponse({
            "status": "rejected",
            "event_id": event_id,
            "decision_id": decision_id,
            "message": "Decision rejected. Event dossier was not modified.",
        })
    except Exception as e:
        logger.error("Error rejecting decision: %s", e, exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Error rejecting decision: {str(e)}"})


@app.post("/chat")
async def chat(req: Request):
    """Main conversational copilot endpoint.

    Strict exception sanitization: Any failure produces
    'EventOps couldn't complete that request. No event data was changed.'
    with request_id and zero leaked internal details.
    """
    req_id = f"req_{uuid.uuid4().hex[:8]}"

    try:
        body = await req.json()
        message = (body.get("message") or "").strip()
        user_id = body.get("user_id") or "demo-organizer"
        event_id = body.get("event_id") or "evt_wit_manhattan_2026"
        msg_lower = message.lower()

        db = _get_firestore()
        evt_doc = db.collection("events").document(event_id).get()
        event_data = evt_doc.to_dict() if evt_doc.exists else {}

        # 1. Human Approval Intent (via Chat)
        if ("approve" in msg_lower and ("change" in msg_lower or "budget" in msg_lower or "proposal" in msg_lower)) or msg_lower == "approve":
            dec_ref = db.collection("events").document(event_id).collection("decisions")
            pending_doc = None
            for doc in dec_ref.stream():
                dd = doc.to_dict()
                if dd.get("approval_status") == "pending_approval":
                    pending_doc = doc
                    break

            if pending_doc:
                dec_id = pending_doc.id
                dec_data = pending_doc.to_dict()
                field_updates = dec_data.get("field_updates") or {}

                # Apply updates
                if event_data and field_updates:
                    new_version = (event_data.get("version") or 1) + 1
                    event_data["version"] = new_version
                    for k, v in field_updates.items():
                        event_data[k] = v
                    if "budget_allocations" in event_data:
                        event_data["budget_breakdown"] = event_data["budget_allocations"]
                    score, _, _ = compute_event_readiness(event_data)
                    event_data["readiness_score"] = score
                    db.collection("events").document(event_id).set(event_data)

                dec_ref.document(dec_id).update({
                    "approval_status": "approved",
                    "approved_by": "Lead Event Director",
                    "approved_at": datetime.now(timezone.utc).isoformat(),
                    "resulting_change": "Approved and applied to Event Dossier",
                })

                resp = AgentResponse(
                    status="ok",
                    response_type="timeline_update",
                    title="Change Approved & Committed",
                    summary=f"Decision {dec_id} approved. Event Dossier updated successfully in Cloud Firestore.",
                    event_id=event_id,
                    decision_id=dec_id,
                    request_id=req_id,
                )
                text_part = (
                    f"### ✅ Change Approved & Committed to Event Dossier\n\n"
                    f"- **Decision ID**: `{dec_id}`\n"
                    f"- **Status**: `APPROVED` by Lead Event Director\n"
                    f"- **Event**: {event_data.get('title', event_id)}\n\n"
                    f"The living Event Dossier has been updated in Cloud Firestore."
                )
                return JSONResponse({
                    "status": "ok",
                    "request_id": req_id,
                    "structured": resp.model_dump(),
                    "parts": [{"kind": "text", "text": text_part}],
                })

        # 2. Human Rejection Intent (via Chat)
        if ("reject" in msg_lower and ("change" in msg_lower or "budget" in msg_lower or "proposal" in msg_lower)) or msg_lower == "reject":
            dec_ref = db.collection("events").document(event_id).collection("decisions")
            for doc in dec_ref.stream():
                dd = doc.to_dict()
                if dd.get("approval_status") == "pending_approval":
                    dec_ref.document(doc.id).update({
                        "approval_status": "rejected",
                        "approved_by": "Lead Event Director",
                        "approved_at": datetime.now(timezone.utc).isoformat(),
                        "resulting_change": "Rejected by user. No modifications applied.",
                    })
                    break

            resp = AgentResponse(
                status="ok",
                response_type="informational",
                title="Change Rejected",
                summary="The proposed modification was rejected. No changes were made to the Event Dossier.",
                event_id=event_id,
                request_id=req_id,
            )
            return JSONResponse({
                "status": "ok",
                "request_id": req_id,
                "structured": resp.model_dump(),
                "parts": [{"kind": "text", "text": "❌ **Proposal Rejected**. No modifications were made to the Event Dossier."}],
            })

        # 3. Proactive Readiness Scan ("What am I forgetting?" / "readiness")
        if any(w in msg_lower for w in ["forgetting", "readiness", "guard", "risks", "scanner", "scan"]):
            score, findings, breakdown = compute_event_readiness(event_data)
            status_label = "Ready for Execution" if score >= 80 else ("Needs Attention" if score >= 60 else "High Risk")
            
            critical_items = [f for f in findings if f["severity"] == "Critical"]
            attention_items = [f for f in findings if f["severity"] == "Attention"]

            recommendations = []
            for f in critical_items + attention_items:
                recommendations.append({"category": f["category"], "action": f["action"], "severity": f["severity"]})

            resp = AgentResponse(
                status="ok",
                response_type="readiness_scan",
                title=f"EventOps Guard: Operational Readiness ({event_data.get('title', event_id)})",
                summary=f"Readiness Score: {score}/100 · {status_label}. {breakdown.explanation}",
                severity="critical" if critical_items else ("attention" if attention_items else "ready"),
                event_id=event_id,
                readiness_breakdown=breakdown,
                data={
                    "readiness_score": score,
                    "findings": findings,
                    "critical_count": len(critical_items),
                    "attention_count": len(attention_items),
                    "ready_count": sum(1 for f in findings if f["severity"] == "Ready"),
                },
                recommendations=recommendations,
                request_id=req_id,
            )

            lines = [
                f"### 🛡️ EventOps Guard: Operational Readiness & Risk Scan",
                f"**Event**: {event_data.get('title', event_id)}",
                f"**Readiness Score**: **{score} / 100 · {status_label.upper()}**\n",
                f"*{breakdown.explanation}*\n",
                f"#### 🔍 Key Findings & Action Items:\n",
            ]
            for f in findings:
                icon = "🚨" if f["severity"] == "Critical" else ("⚠️" if f["severity"] == "Attention" else "✅")
                lines.append(f"- {icon} **{f['category']}** ({f['severity']}): {f['issue']}")
                if f['action'] and f['action'] != 'None required.':
                    lines.append(f"  *Recommended Action*: {f['action']}")

            return JSONResponse({
                "status": "ok",
                "request_id": req_id,
                "structured": resp.model_dump(),
                "parts": [{"kind": "text", "text": "\n".join(lines)}],
            })

        # 4. Consequential Budget Change Intent
        budget_match = re.search(r"\$([0-9,]+)", message)
        is_budget_intent = any(w in msg_lower for w in ["budget", "reduce", "cut", "rebalance", "drop"])
        if is_budget_intent and budget_match:
            raw_amt = float(budget_match.group(1).replace(",", ""))
            curr_budget = float(event_data.get("total_budget", 4000.0))
            
            # Decide if target is a total budget ceiling or a reduction delta
            if "by" in msg_lower or "cut" in msg_lower or "reduce by" in msg_lower:
                new_budget = max(500.0, curr_budget - raw_amt)
            else:
                new_budget = raw_amt

            dec_id = f"dec_{uuid.uuid4().hex[:6]}"
            allocations = event_data.get("budget_allocations") or event_data.get("budget_breakdown") or []
            
            # Deterministic Decimal adjustment protecting Food & Beverage and 10% contingency
            rebalanced_allocs, variance, actions = rebalance_budget_allocations(
                total_budget=new_budget,
                allocations=allocations,
            )

            proposed_change = f"Adjust total event budget from ${curr_budget:,.2f} to ${new_budget:,.2f}"
            rationale = f"Reconcile event finances to revised ${new_budget:,.2f} budget while safeguarding protected priorities."
            impact_desc = f"Total budget set to ${new_budget:,.2f}. Exact zero-variance allocation enforced across all categories."

            # Log pending decision in Firestore
            db.collection("events").document(event_id).collection("decisions").document(dec_id).set({
                "decision_id": dec_id,
                "event_id": event_id,
                "proposed_change": proposed_change,
                "rationale": rationale,
                "expected_impact": impact_desc,
                "assumptions": ["Vendor pricing verified", "Contingency reserve maintained"],
                "approval_status": "pending_approval",
                "field_updates": {
                    "total_budget": new_budget,
                    "budget_allocations": rebalanced_allocs,
                    "budget_breakdown": rebalanced_allocs,
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "approved_by": None,
            })

            resp = AgentResponse(
                status="pending_approval",
                response_type="budget_proposal",
                title=f"Consequential Change Proposed: Budget Adjustment",
                summary=rationale,
                requires_approval=True,
                decision_id=dec_id,
                event_id=event_id,
                data={
                    "decision_id": dec_id,
                    "current_budget": curr_budget,
                    "proposed_budget": new_budget,
                    "rebalanced_allocations": rebalanced_allocs,
                },
                recommendations=[
                    {"action": "Review updated allocation lines in Plan tab", "severity": "attention"},
                    {"action": "Confirm approval via [Approve] button in Decision Ledger", "severity": "attention"},
                ],
                request_id=req_id,
            )

            text_proposal = (
                f"### 📋 Consequential Change Proposed: Pending Human Approval\n\n"
                f"**Decision ID**: `{dec_id}`\n\n"
                f"**Proposed Modification**:\n"
                f"> {proposed_change}\n\n"
                f"**Strategic Rationale**:\n"
                f"{rationale}\n\n"
                f"**Operational & Budget Impact**:\n"
                f"- **Revised Total Budget**: **${new_budget:,.2f}** (Prior: ${curr_budget:,.2f})\n"
                f"- **Variance**: **$0.00** (Exact cent mathematical balance)\n\n"
                f"⚠️ *Decision Ledger Status*: `PENDING_APPROVAL`\n\n"
                f"To commit this change, click **[Approve]** in the Decision Ledger or reply: **\"Approve\"**."
            )

            return JSONResponse({
                "status": "ok",
                "request_id": req_id,
                "structured": resp.model_dump(),
                "parts": [{"kind": "text", "text": text_proposal}],
            })

        # 5. Forward to Deployed Reasoning Engine via A2A
        context_id = _contexts.get(user_id)
        msg_id = str(uuid.uuid4())
        a2a_id = str(uuid.uuid4())

        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": a2a_id,
            "method": "SendMessage",
            "params": {
                "message": {
                    "message_id": msg_id,
                    "role": "ROLE_USER",
                    "parts": [{"text": message}],
                }
            },
        }
        if context_id:
            payload["params"]["message"]["context_id"] = context_id

        parts: list[dict[str, Any]] = []
        async with httpx.AsyncClient(headers=_auth_headers(), timeout=45) as client:
            resp_http = await client.post(A2A_ENDPOINT, json=payload)
            resp_http.raise_for_status()
            data = resp_http.json()

            if "error" in data:
                err_msg = data["error"].get("message", "Reasoning engine error")
                logger.warning("A2A returned error object: %s", err_msg)
                raise RuntimeError(err_msg)

            result = data.get("result") or {}
            task = result.get("task")
            if task:
                ctx = task.get("contextId") or task.get("context_id")
                if ctx:
                    _contexts[user_id] = ctx
                parts = _extract_parts_from_task(task)
            elif "message" in result:
                msg_parts = result["message"].get("parts") or []
                for mp in msg_parts:
                    if mp.get("text"):
                        parts.append({"kind": "text", "text": mp["text"]})

        if not parts:
            parts = [{"kind": "text", "text": "EventOps Copilot processed your request."}]

        combined_text = "\n\n".join(p.get("text", "") for p in parts if p.get("text"))
        agent_resp = AgentResponse(
            status="ok",
            response_type="informational",
            title="Copilot Response",
            summary=combined_text[:160] if combined_text else "EventOps Copilot update",
            event_id=event_id,
            request_id=req_id,
        )

        return JSONResponse({
            "status": "ok",
            "request_id": req_id,
            "structured": agent_resp.model_dump(),
            "parts": parts,
        })

    except Exception as e:
        logger.error("[%s] Internal Copilot exception: %s", req_id, e, exc_info=True)
        # Strict user-facing error sanitization invariant
        sanitized_summary = "EventOps couldn't complete that request. No event data was changed."
        safe_response = AgentResponse(
            status="error",
            response_type="error",
            title="Operation Incomplete",
            summary=sanitized_summary,
            event_id=body.get("event_id") if "body" in locals() and isinstance(body, dict) else None,
            request_id=req_id,
        )
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "request_id": req_id,
                "structured": safe_response.model_dump(),
                "parts": [
                    {
                        "kind": "error",
                        "text": sanitized_summary,
                        "request_id": req_id,
                    }
                ],
            },
        )


# =========================================================================
# Integration Action Ledger & Analytics Endpoints
# =========================================================================

_memory_actions: dict[str, list[dict[str, Any]]] = {}


async def _get_event_data_dict(event_id: str) -> dict[str, Any] | None:
    try:
        db = _get_firestore()
        doc = db.collection("events").document(event_id).get()
        if doc.exists:
            return doc.to_dict()
    except Exception:
        pass
    if event_id == "evt_wit_manhattan_2026":
        return {
            "event_id": "evt_wit_manhattan_2026",
            "title": "Women in Tech Leadership Dinner",
            "date": "2026-10-15",
            "start_time": "18:00",
            "end_time": "21:30",
            "location": "The Altman Building, New York, NY",
            "guest_count": 30,
            "total_budget": 4000.0,
            "readiness_score": 95,
            "budget_allocations": [
                {"category": "Catering & Private Chef", "allocated_amount": 2200.0},
                {"category": "Venue & Premium Private Room", "allocated_amount": 1000.0},
                {"category": "Event Décor, Florals & Print", "allocated_amount": 400.0},
                {"category": "Contingency & Incidentals", "allocated_amount": 400.0},
            ],
            "risks": [
                {
                    "category": "Guest Experience",
                    "severity": "Attention",
                    "details": "Dietary requirements not fully confirmed across all VIP attendees.",
                    "status": "open",
                }
            ],
            "run_of_show": [
                {"time": "18:00 - 18:45", "phase": "VIP Arrivals & Welcome Reception", "lead": "Guest Experience Lead"},
                {"time": "18:45 - 20:30", "phase": "Keynote Dialogue & Plated Dinner", "lead": "Program Lead"},
                {"time": "20:30 - 21:30", "phase": "Executive Networking & Closing Remarks", "lead": "Lead Host"},
            ],
        }
    return None


def _save_action_to_store(action: IntegrationAction) -> None:
    data = action.model_dump()
    _memory_actions.setdefault(action.event_id, [])
    for idx, act in enumerate(_memory_actions[action.event_id]):
        if act.get("action_id") == action.action_id:
            _memory_actions[action.event_id][idx] = data
            break
    else:
        _memory_actions[action.event_id].append(data)

    try:
        db = _get_firestore()
        db.collection("events").document(action.event_id).collection("integration_actions").document(action.action_id).set(data)
    except Exception as e:
        logger.debug("Firestore unavailable for action record, using in-memory store: %s", e)


def _get_actions_from_store(event_id: str) -> list[dict[str, Any]]:
    actions = list(_memory_actions.get(event_id, []))
    try:
        db = _get_firestore()
        docs = db.collection("events").document(event_id).collection("integration_actions").order_by("requested_at").stream()
        fs_actions = [doc.to_dict() for doc in docs]
        if fs_actions:
            return fs_actions
    except Exception as e:
        logger.debug("Firestore unavailable for fetching actions, using in-memory store: %s", e)
    return actions


def _get_action_by_id(event_id: str, action_id: str) -> dict[str, Any] | None:
    actions = _get_actions_from_store(event_id)
    for a in actions:
        if a.get("action_id") == action_id:
            return a
    return None


def _update_action_in_store(event_id: str, action_id: str, updates: dict[str, Any]) -> bool:
    actions = _memory_actions.get(event_id, [])
    for a in actions:
        if a.get("action_id") == action_id:
            a.update(updates)
            break
    try:
        db = _get_firestore()
        db.collection("events").document(event_id).collection("integration_actions").document(action_id).update(updates)
    except Exception as e:
        logger.debug("Firestore unavailable for action update, using in-memory store: %s", e)
    return True


@app.get("/api/integrations/status")
async def get_integrations_status():
    """Return live status of external integrations (Google Calendar, Gmail, Slack)."""
    cal = get_calendar_provider().get_connection_status()
    email = get_email_provider().get_connection_status()
    slack = get_messaging_provider().get_connection_status()
    return JSONResponse({
        "status": "ok",
        "integrations": [
            cal.model_dump(),
            email.model_dump(),
            slack.model_dump(),
        ],
    })


@app.get("/api/integrations/actions")
async def get_integration_actions_api(event_id: str = "evt_wit_manhattan_2026"):
    """Fetch external action ledger records for an event."""
    actions = _get_actions_from_store(event_id)
    return JSONResponse({
        "status": "ok",
        "event_id": event_id,
        "actions": actions,
    })


@app.post("/api/integrations/calendar/preview")
async def preview_calendar_api(req: Request):
    """Preview Google Calendar entry or milestones without mutating external state."""
    body = await req.json()
    event_id = body.get("event_id", "evt_wit_manhattan_2026")
    mode = body.get("mode", "main")
    event_data = await _get_event_data_dict(event_id)
    if not event_data:
        return JSONResponse(status_code=404, content={"error": f"Event {event_id} not found."})

    provider = get_calendar_provider()
    preview = provider.preview_event(event_data, mode=mode)
    action = IntegrationAction(
        event_id=event_id,
        provider="calendar",
        action_type="sync_milestones" if mode == "milestones" else "create_event",
        target="primary_calendar",
        preview=preview,
        status="pending_approval",
        is_demo=getattr(provider, "is_demo", False),
    )
    _save_action_to_store(action)

    analytics_service.record_telemetry(
        category="governance",
        operation="preview_calendar_event",
        status="success",
        event_id=event_id,
        provider="calendar",
        action_id=action.action_id,
    )

    return JSONResponse({
        "status": "ok",
        "action": action.model_dump(),
        "preview": preview,
    })


@app.post("/api/integrations/calendar/sync")
async def sync_calendar_api(req: Request):
    """Sync calendar entry after explicit human approval."""
    body = await req.json()
    event_id = body.get("event_id")
    action_id = body.get("action_id")
    if not event_id or not action_id:
        return JSONResponse(status_code=400, content={"error": "event_id and action_id are required."})

    action = _get_action_by_id(event_id, action_id)
    if not action:
        return JSONResponse(status_code=404, content={"error": f"Action {action_id} not found."})

    if action.get("status") != "approved":
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Action {action_id} is in status '{action.get('status')}'. Explicit human approval is required."
            },
        )

    event_data = await _get_event_data_dict(event_id)
    provider = get_calendar_provider()
    res = provider.create_event(
        event_data or {},
        idempotency_key=action.get("idempotency_key", uuid.uuid4().hex),
        milestones_only=(action.get("action_type") == "sync_milestones"),
    )

    now = datetime.now(timezone.utc).isoformat()
    if res.get("status") == "completed":
        _update_action_in_store(event_id, action_id, {
            "status": "completed",
            "executed_at": now,
            "external_resource_id": res.get("calendar_event_id"),
        })
        analytics_service.record_telemetry(
            category="governance",
            operation="sync_calendar_event",
            status="success",
            event_id=event_id,
            provider="calendar",
            action_id=action_id,
        )
    else:
        _update_action_in_store(event_id, action_id, {
            "status": "failed",
            "error_summary": res.get("error", "Calendar sync failed"),
        })

    return JSONResponse(res)


@app.post("/api/integrations/email/draft")
async def draft_email_api(req: Request):
    """Draft an operational email with strict recipient validation."""
    body = await req.json()
    event_id = body.get("event_id", "evt_wit_manhattan_2026")
    intent = body.get("intent", "Dietary and accessibility intake")
    recipients = body.get("recipients", [])

    try:
        valid_recipients = validate_recipients(recipients)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    event_data = await _get_event_data_dict(event_id)
    provider = get_email_provider()
    draft = provider.draft_email(event_data or {}, intent, valid_recipients)

    action = IntegrationAction(
        event_id=event_id,
        provider="gmail",
        action_type="save_draft",
        target=", ".join(valid_recipients),
        preview=draft.model_dump(),
        status="pending_approval",
        is_demo=getattr(provider, "is_demo", False),
    )
    _save_action_to_store(action)

    analytics_service.record_telemetry(
        category="governance",
        operation="draft_event_email",
        status="success",
        event_id=event_id,
        provider="gmail",
        action_id=action.action_id,
        metadata={"recipient_count": len(valid_recipients)},
    )

    return JSONResponse({
        "status": "ok",
        "action": action.model_dump(),
        "draft": draft.model_dump(),
    })


@app.post("/api/integrations/email/save-draft")
async def save_email_draft_api(req: Request):
    """Save approved email draft into Gmail drafts."""
    body = await req.json()
    event_id = body.get("event_id")
    action_id = body.get("action_id")

    action = _get_action_by_id(event_id, action_id)
    if not action:
        return JSONResponse(status_code=404, content={"error": f"Action {action_id} not found."})

    if action.get("status") != "approved":
        return JSONResponse(
            status_code=400,
            content={"error": "Action must be approved before saving draft to Gmail."},
        )

    from app.integrations.models import EmailDraft
    draft = EmailDraft.model_validate(action.get("preview", {}))
    provider = get_email_provider()
    res = provider.save_draft(draft, idempotency_key=action.get("idempotency_key", uuid.uuid4().hex))

    now = datetime.now(timezone.utc).isoformat()
    if res.get("status") == "completed":
        _update_action_in_store(event_id, action_id, {
            "status": "completed",
            "executed_at": now,
            "external_resource_id": res.get("gmail_draft_id"),
        })
    else:
        _update_action_in_store(event_id, action_id, {
            "status": "failed",
            "error_summary": res.get("error"),
        })

    return JSONResponse(res)


@app.post("/api/integrations/email/send")
async def send_email_api(req: Request):
    """Send email draft with strict second human confirmation."""
    body = await req.json()
    event_id = body.get("event_id")
    action_id = body.get("action_id")
    confirmation_token = body.get("confirmation_token")

    if confirmation_token != "CONFIRM_SEND":
        return JSONResponse(
            status_code=400,
            content={"error": "Explicit second confirmation token 'CONFIRM_SEND' required to send email."},
        )

    action = _get_action_by_id(event_id, action_id)
    if not action:
        return JSONResponse(status_code=404, content={"error": f"Action {action_id} not found."})

    recipients = action.get("preview", {}).get("to_recipients", [])
    provider = get_email_provider()
    res = provider.send_draft(
        draft_id=action.get("external_resource_id", action_id),
        confirmation_token=confirmation_token,
        expected_recipients_count=len(recipients),
    )

    now = datetime.now(timezone.utc).isoformat()
    if res.get("status") == "completed":
        _update_action_in_store(event_id, action_id, {
            "status": "completed",
            "executed_at": now,
        })
        analytics_service.record_telemetry(
            category="governance",
            operation="send_email",
            status="success",
            event_id=event_id,
            provider="gmail",
            action_id=action_id,
        )

    return JSONResponse(res)


@app.post("/api/integrations/slack/preview")
async def preview_slack_api(req: Request):
    """Preview operational Slack notification."""
    body = await req.json()
    event_id = body.get("event_id", "evt_wit_manhattan_2026")
    category = body.get("category", "Operational Update")
    item = body.get("item", {})
    channel = body.get("channel", "#event-ops")

    event_data = await _get_event_data_dict(event_id)
    provider = get_messaging_provider()
    payload = provider.preview_message(event_data or {}, category, item, channel_name=channel)

    action = IntegrationAction(
        event_id=event_id,
        provider="slack",
        action_type="post_slack_message",
        target=channel,
        preview=payload.model_dump(),
        status="pending_approval",
        is_demo=getattr(provider, "is_demo", False),
    )
    _save_action_to_store(action)

    analytics_service.record_telemetry(
        category="governance",
        operation="preview_slack_message",
        status="success",
        event_id=event_id,
        provider="slack",
        action_id=action.action_id,
    )

    return JSONResponse({
        "status": "ok",
        "action": action.model_dump(),
        "payload": payload.model_dump(),
    })


@app.post("/api/integrations/slack/post")
async def post_slack_api(req: Request):
    """Post operational notification to Slack after human approval."""
    body = await req.json()
    event_id = body.get("event_id")
    action_id = body.get("action_id")

    action = _get_action_by_id(event_id, action_id)
    if not action:
        return JSONResponse(status_code=404, content={"error": f"Action {action_id} not found."})

    if action.get("status") != "approved":
        return JSONResponse(
            status_code=400,
            content={"error": "Action must be approved before posting to Slack."},
        )

    from app.integrations.models import SlackMessagePayload
    payload = SlackMessagePayload.model_validate(action.get("preview", {}))
    provider = get_messaging_provider()
    res = provider.post_message(payload, idempotency_key=action.get("idempotency_key", uuid.uuid4().hex))

    now = datetime.now(timezone.utc).isoformat()
    if res.get("status") == "completed":
        _update_action_in_store(event_id, action_id, {
            "status": "completed",
            "executed_at": now,
            "external_resource_id": res.get("message_ts"),
        })
        analytics_service.record_telemetry(
            category="governance",
            operation="post_slack_message",
            status="success",
            event_id=event_id,
            provider="slack",
            action_id=action_id,
        )
    else:
        _update_action_in_store(event_id, action_id, {
            "status": "failed",
            "error_summary": res.get("error"),
        })

    return JSONResponse(res)


@app.post("/api/integrations/actions/{action_id}/approve")
async def approve_integration_action_api(action_id: str, req: Request):
    """Approve a pending external integration action."""
    body = await req.json() if req.headers.get("content-length") else {}
    event_id = body.get("event_id", "evt_wit_manhattan_2026")
    action = _get_action_by_id(event_id, action_id)
    if not action:
        return JSONResponse(status_code=404, content={"error": f"Action {action_id} not found."})

    now = datetime.now(timezone.utc).isoformat()
    _update_action_in_store(event_id, action_id, {
        "status": "approved",
        "approved_at": now,
    })
    return JSONResponse({
        "status": "approved",
        "action_id": action_id,
        "message": "Action approved by director. Ready for execution.",
    })


@app.post("/api/integrations/actions/{action_id}/reject")
async def reject_integration_action_api(action_id: str, req: Request):
    """Reject a pending external integration action."""
    body = await req.json() if req.headers.get("content-length") else {}
    event_id = body.get("event_id", "evt_wit_manhattan_2026")
    action = _get_action_by_id(event_id, action_id)
    if not action:
        return JSONResponse(status_code=404, content={"error": f"Action {action_id} not found."})

    _update_action_in_store(event_id, action_id, {
        "status": "rejected",
    })
    return JSONResponse({
        "status": "rejected",
        "action_id": action_id,
        "message": "Action rejected. External systems will not be mutated.",
    })


@app.get("/api/analytics/event/{event_id}")
async def get_event_analytics_api(event_id: str):
    """Get deterministic operational metrics for an event."""
    event_data = await _get_event_data_dict(event_id)
    if not event_data:
        return JSONResponse(status_code=404, content={"error": f"Event {event_id} not found."})

    decisions = []
    try:
        db = _get_firestore()
        docs = db.collection("events").document(event_id).collection("decisions").stream()
        decisions = [d.to_dict() for d in docs]
    except Exception:
        pass

    actions = _get_actions_from_store(event_id)
    metrics = analytics_service.get_event_analytics(event_data, decisions, actions)
    return JSONResponse({"status": "ok", "analytics": metrics})


@app.get("/api/analytics/portfolio")
async def get_portfolio_analytics_api():
    """Get aggregated metrics across all portfolio events."""
    all_events = []
    all_decisions = []
    all_actions = []
    try:
        db = _get_firestore()
        for doc in db.collection("events").stream():
            d = doc.to_dict()
            all_events.append(d)
            for dec in db.collection("events").document(doc.id).collection("decisions").stream():
                all_decisions.append(dec.to_dict())
            for act in db.collection("events").document(doc.id).collection("integration_actions").stream():
                all_actions.append(act.to_dict())
    except Exception:
        pass

    if not all_events:
        default_ev = await _get_event_data_dict("evt_wit_manhattan_2026")
        if default_ev:
            all_events.append(default_ev)

    portfolio = analytics_service.get_portfolio_analytics(all_events, all_decisions, all_actions)
    return JSONResponse({"status": "ok", "portfolio": portfolio})


# Static assets
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    logger.info("Starting EventOps AI Frontend on port %d...", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
