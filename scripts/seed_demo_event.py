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

"""Seed script to populate Firestore with the polished demo event."""

import sys
from pathlib import Path

# Ensure app directory is on path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.event_store import DecisionRecord, EventDossier, get_event_store


def seed_demo_event():
    store = get_event_store()

    event_id = "evt_wit_manhattan_2026"
    title = "Women in Tech Leadership & Innovation Dinner"

    dossier = EventDossier(
        event_id=event_id,
        title=title,
        event_type="executive_networking_dinner",
        objective=(
            "Host an intimate, sophisticated networking dinner for 30 senior women "
            "technology leaders in Manhattan to foster authentic peer relationships, "
            "exchange engineering and product insights, and celebrate community impact "
            "in a warm, non-corporate setting."
        ),
        status="planning",
        guest_count=30,
        location="Manhattan, NY (Flatiron / Gramercy)",
        total_budget=4000.0,
        currency="USD",
        protected_priorities=[
            "Food & Beverage Quality",
            "Accessible & Inclusive Seating",
            "Warm Intimate Atmosphere",
            "Zero-Proof Beverage Excellence",
        ],
        atmosphere="Warm, candlelight-lit, sophisticated, conversational, non-corporate, relaxed elegance",
        formality="Smart Casual to Elevated Business Attire",
        guest_profile={
            "demographic": "30 Senior Women Directors, VPs, and Engineering Founders",
            "expectations": "Exceptional culinary experience, frictionless logistics, unforced conversation, privacy",
            "dietary_mix": "Estimated 20% vegetarian/vegan, 15% gluten-free, 40% zero-proof beverage preference",
        },
        guest_journey=[
            {
                "stage_number": 1,
                "stage_name": "Invitation & Framing",
                "timeline": "T-4 weeks to T-3 weeks",
                "touchpoint": "Personalized digital invitation with clear salon theme, attire guide, and dietary survey",
                "emotional_goal": "Intrigue, anticipation, and feeling valued as an invited peer",
            },
            {
                "stage_number": 2,
                "stage_name": "Pre-event Communications & Expectations",
                "timeline": "T-7 days & T-24 hours",
                "touchpoint": "Concise logistics brief: transit, exact private room entry instructions, host contact",
                "emotional_goal": "Confidence and zero arrival anxiety",
            },
            {
                "stage_number": 3,
                "stage_name": "Arrival & Transition from Street to Space",
                "timeline": "18:00 - 18:15",
                "touchpoint": "Curated street-level greeter, swift private elevator to salon, immediate warm coat check",
                "emotional_goal": "Decompression from NYC street pace into an exclusive, warm haven",
            },
            {
                "stage_number": 4,
                "stage_name": "First 15 Minutes & Welcome Reception",
                "timeline": "18:15 - 18:30",
                "touchpoint": "Signature welcoming cocktail or artisanal zero-proof elixir, gentle ambient music, effortless introductions",
                "emotional_goal": "Immediate belonging and psychological safety",
            },
            {
                "stage_number": 5,
                "stage_name": "Main Experience: Salon & Seated Dinner",
                "timeline": "18:30 - 20:30",
                "touchpoint": "3-course seasonal seated dinner, thoughtful table conversation prompts, short 5-minute host toast",
                "emotional_goal": "Intellectual stimulation, memorable culinary delight, deep connection",
            },
            {
                "stage_number": 6,
                "stage_name": "Transitions & Room Flow",
                "timeline": "20:30 - 21:00",
                "touchpoint": "Post-dinner coffee/tea salon, dessert tasting, fluid movement across tables for open mingling",
                "emotional_goal": "Dynamic connection with peers from other tables without abruptness",
            },
            {
                "stage_number": 7,
                "stage_name": "Departure & Closing Impression",
                "timeline": "21:00 - 21:30",
                "touchpoint": "Seamless coat retrieval, discreet gift (curated book or artisanal treat), personal thank you from host",
                "emotional_goal": "Warmth, gratitude, energized perspective",
            },
            {
                "stage_number": 8,
                "stage_name": "Post-Event Follow-up & Community Loop",
                "timeline": "T+24 hours",
                "touchpoint": "Opt-in guest contact roster, shared photo highlights, follow-up resource links",
                "emotional_goal": "Lasting network bonds and anticipation for future gatherings",
            },
        ],
        budget_allocations=[
            {
                "category": "Food & Beverage",
                "allocated_amount": 2200.0,
                "base_cost": 1700.0,
                "tax": 150.88,
                "gratuity": 340.0,
                "notes": "3-course dinner for 30 guests @ $56.67/head base, 8.875% NYC sales tax + 20% gratuity",
                "is_protected": True,
            },
            {
                "category": "Venue & Space Minimum",
                "allocated_amount": 1000.0,
                "base_cost": 1000.0,
                "tax": 0.0,
                "gratuity": 0.0,
                "notes": "Private dining room buyout minimum applied directly against F&B balance",
                "is_protected": False,
            },
            {
                "category": "Atmosphere, Décor & Printing",
                "allocated_amount": 250.0,
                "base_cost": 230.0,
                "tax": 20.0,
                "gratuity": 0.0,
                "notes": "Custom menu cards, tasteful seasonal bud vases, bespoke name markers",
                "is_protected": False,
            },
            {
                "category": "Staffing & Hospitality Services",
                "allocated_amount": 200.0,
                "base_cost": 200.0,
                "tax": 0.0,
                "gratuity": 0.0,
                "notes": "Dedicated coat check attendant and guest greeting host (4 hours @ $25/hr x 2)",
                "is_protected": True,
            },
            {
                "category": "Contingency Reserve",
                "allocated_amount": 350.0,
                "base_cost": 350.0,
                "tax": 0.0,
                "gratuity": 0.0,
                "notes": "8.75% operational contingency buffer for last-minute dietary adjustments or overages",
                "is_protected": True,
            },
        ],
        run_of_show=[
            {"time": "17:00", "duration_min": 60, "activity": "Host arrival, room acoustic & lighting check, floral placement", "owner": "Event Lead", "cue": "Room access confirmed"},
            {"time": "18:00", "duration_min": 30, "activity": "Guest arrival, coat check, welcome drinks & passed amuse-bouche", "owner": "Host & Greeting Staff", "cue": "Doors open, soft background jazz on"},
            {"time": "18:30", "duration_min": 15, "activity": "Transition to seated dining room, brief welcome remarks by Host", "owner": "Host", "cue": "Guests take designated seats"},
            {"time": "18:45", "duration_min": 40, "activity": "Course 1: Seasonal appetizer, table discussion prompt 1", "owner": "Venue Lead / Catering", "cue": "Plates served simultaneously"},
            {"time": "19:25", "duration_min": 50, "activity": "Course 2: Main entrée & wine/zero-proof pairings, keynote lightning share", "owner": "Catering Lead", "cue": "Table cleared, mains served"},
            {"time": "20:15", "duration_min": 30, "activity": "Course 3: Dessert & espresso, closing salon reflection", "owner": "Host", "cue": "Dessert service"},
            {"time": "20:45", "duration_min": 35, "activity": "Open mingling, coffee & tea service, table swapping", "owner": "Host", "cue": "Lounge music tempo slightly elevated"},
            {"time": "21:20", "duration_min": 10, "activity": "Closing thank you, coat retrieval, departure gift handoff", "owner": "Event Lead", "cue": "Final guest departure"},
            {"time": "21:30", "duration_min": 30, "activity": "Event wrap, final bill sign-off, room inspection", "owner": "Event Lead", "cue": "Venue walkthrough"},
        ],
        venue_requirements={
            "neighborhood": "Manhattan (Flatiron, Gramercy, or SoHo)",
            "space_type": "Fully private dining room with acoustic separation and door closure",
            "capacity": "30 seated guests plus greeting area",
            "acoustics": "Soft textiles/carpet to dampen sound; conversational ambient level < 65dB",
            "lighting": "Warm dimmable incandescent/candlelight, no harsh fluorescent overheads",
            "accessibility": "Step-free street access, accessible elevator, ADA restroom on same floor",
            "transit": "Within 3 blocks of major subway lines (N/Q/R/W, 4/5/6, or L)",
        },
        food_beverage={
            "format": "3-course seasonal prix-fixe with pre-selected protein, fish, and vegan options",
            "beverage_program": "Equal-standing wine pairing and artisanal non-alcoholic botanicals pairing",
            "dietary_protocol": "Individual guest dietary survey confirmed 72 hours prior; 2 reserve dietary plates held",
            "service_style": "Synchronized plated service for seamless dining rhythm",
        },
        accessibility={
            "physical": "Elevator access, wide aisle clearance between dining chairs (> 36 inches)",
            "sensory": "Controlled lighting, no strobe or flashing elements, managed acoustic resonance",
            "dietary_inclusivity": "Full gluten-free, vegan, kosher/halal accommodation upon advance request",
            "non_alcoholic": "Sophisticated zero-proof pairings presented with equal elegance to wines",
        },
        staffing=[
            {"role": "Event Lead & Producer", "count": 1, "responsibility": "Overall timeline, vendor oversight, guest escort"},
            {"role": "Guest Greeting & Coat Check Attendant", "count": 1, "responsibility": "Street/elevator greeting, coat check, departure gifts"},
            {"role": "Lead Server (Venue Staff)", "count": 2, "responsibility": "Course synchronization and beverage pairings"},
        ],
        vendors=[
            {"name": "Gramercy Tavern Private Dining (Candidate)", "category": "Venue & Catering", "status": "Inquiry Sent", "estimated_cost": 3200.0, "contact": "events@gramercy.mock"},
            {"name": "L'Ami Pierre Floral Atelier", "category": "Florals & Table Styling", "status": "Proposed", "estimated_cost": 180.0, "contact": "hello@lamipierre.mock"},
            {"name": "Verdant Zero-Proof Botanicals", "category": "Specialty Beverages", "status": "Confirmed", "estimated_cost": 150.0, "contact": "cheers@verdant.mock"},
        ],
        tasks=[
            {"task_id": "tsk_01", "description": "Lock private dining room contract and deposit", "owner": "Event Lead", "due_date": "2026-10-01", "status": "in_progress", "raci": "Accountable"},
            {"task_id": "tsk_02", "description": "Send invitations with dietary and accessibility survey", "owner": "Host", "due_date": "2026-10-05", "status": "pending", "raci": "Responsible"},
            {"task_id": "tsk_03", "description": "Finalize 3-course menu and zero-proof pairings", "owner": "Event Lead", "due_date": "2026-10-15", "status": "pending", "raci": "Responsible"},
            {"task_id": "tsk_04", "description": "Print custom menu cards and curated conversation prompts", "owner": "Event Lead", "due_date": "2026-10-20", "status": "pending", "raci": "Responsible"},
            {"task_id": "tsk_05", "description": "Conduct 72-hour dietary lock and final headcount review", "owner": "Event Lead", "due_date": "2026-10-22", "status": "pending", "raci": "Accountable"},
        ],
        risks=[
            {
                "risk_id": "rsk_01",
                "description": "Unaccounted dietary allergy or preference revealed on-site during dinner",
                "severity": "High",
                "likelihood": "Medium",
                "mitigation": "Advance dietary survey at RSVP + mandate venue kitchen keep 2 allergen-free vegan reserve plates.",
            },
            {
                "risk_id": "rsk_02",
                "description": "Excessive sound bleed from main dining room obstructing intimate conversation",
                "severity": "High",
                "likelihood": "Low",
                "mitigation": "Contractually require private room with solid door closure and conduct on-site sound check.",
            },
            {
                "risk_id": "rsk_03",
                "description": "NYC transit delay or sudden rain causing arrival congestion and wet garments",
                "severity": "Medium",
                "likelihood": "High",
                "mitigation": "Dedicated coat check attendant, umbrella wraps at entry, 15-minute arrival buffer built into Run of Show.",
            },
        ],
        contingencies=[
            {
                "scenario": "Guest count fluctuation between 25 and 32",
                "plan": "Venue contract includes flexible ±10% headcount adjustment cutoff at T-48 hours",
                "reserve_amount": 200.0,
            },
            {
                "scenario": "Unanticipated kitchen overtime or beverage consumption surge",
                "plan": "Draw from dedicated $350 Contingency Reserve with Host approval",
                "reserve_amount": 350.0,
            },
        ],
        assumptions=[
            "Venue food & beverage minimum is credited 100% against consumption.",
            "NYC sales tax rate is 8.875% and mandatory dining gratuity is 20%.",
            "Event does not require external audiovisual projection; acoustic conversation is primary.",
        ],
        confirmed_facts=[
            "Total allocated budget is firmly capped at $4,000.00.",
            "Expected headcount is 30 invited participants.",
            "Event format is an evening seated salon in Manhattan.",
        ],
        readiness_score=85,
    )

    store.save_event(dossier)
    print(f"Successfully seeded demo event '{event_id}' into Firestore!")

    # Seed initial decision record in ledger
    decision = DecisionRecord(
        decision_id="dec_init_001",
        event_id=event_id,
        proposed_change="Reallocate $150 from general printing to premium artisanal zero-proof beverage pairings",
        rationale="Aligns with inclusive hospitality priority; 40% of guest profile prefers elevated non-alcoholic pairings over standard soda/water.",
        assumptions=["Catering team can source botanical infusions at $5/head wholesale"],
        expected_impact="Elevates guest satisfaction and inclusivity without increasing total event budget.",
        approval_status="approved",
        approved_by="Executive Host",
        resulting_change="F&B allocation adjusted; Atmosphere/Printing reduced from $400 to $250; Zero-Proof Beverage program added.",
    )
    store.add_decision(decision)
    print(f"Successfully added initial decision '{decision.decision_id}' to Decision Ledger!")


if __name__ == "__main__":
    seed_demo_event()
