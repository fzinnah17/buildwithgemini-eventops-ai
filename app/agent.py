# ruff: noqa
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

import datetime
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.rag_tool import consult_operations_playbook
from app.sandbox_tool import simulate_event_scenario
from app.tools import (
    analyze_event_readiness,
    apply_approved_event_update,
    calculate,
    convert_distance,
    convert_temperature,
    create_calendar_event,
    create_event_dossier,
    draft_event_email,
    get_event_analytics,
    get_event_dossier,
    get_portfolio_analytics,
    post_slack_message,
    preview_calendar_event,
    preview_slack_message,
    propose_event_update,
    rebalance_event_budget,
    record_organizer_preference,
    save_gmail_draft,
    send_gmail_draft,
)
from app.visual_director import generate_event_visual

MODEL = "gemini-2.5-flash"


def get_weather(query: str) -> str:
    """Simulates getting weather information for a location."""
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    elif "nyc" in query.lower() or "new york" in query.lower() or "manhattan" in query.lower():
        return "It's 68 degrees and clear in Manhattan."
    return "It's 72 degrees and pleasant."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city."""
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    elif "nyc" in query.lower() or "new york" in query.lower() or "manhattan" in query.lower():
        tz_identifier = "America/New_York"
    else:
        tz_identifier = "America/New_York"

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


async def generate_memories_callback(callback_context: CallbackContext) -> None:
    """Saves salient organizer preferences to Vertex AI Memory Bank."""
    if callback_context._invocation_context.memory_service is not None:
        try:
            await callback_context.add_session_to_memory()
        except Exception:
            pass
    return None


# Build A2UI 0.8 system instructions
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_system_prompt = schema_manager.generate_system_prompt(
    role_description="EventOps AI, Enterprise Event Operations Agent",
    workflow_description="Analyze the event request, invoke operational tools, and render structured A2UI cards when presenting plans, budgets, run of show, readiness findings, or visual concepts.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, Divider, List, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (such as the public GCS URL returned by generate_event_visual). "
        "Set the Image url to that exact https link: {\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. "
        "Never point an Image at a bare filename, an artifact name, or a non-http(s) path. If no public link is available, use a Text line. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for headings and emphasis. "
        "When rendering A2UI, output the raw A2UI JSON array without markdown fences."
    ),
    include_schema=True,
    include_examples=True,
)

EVENTOPS_AI_INSTRUCTION = (
    f"{a2ui_system_prompt}\n\n"
    "================================================================================\n"
    "EVENTOPS AI CORE OPERATIONAL CHARTER\n"
    "================================================================================\n"
    "You are EventOps AI (Enterprise Event Operations Agent), an enterprise-ready AI "
    "Event Concierge that helps organizers plan, operate, and adapt professional events "
    "while keeping humans strictly in control of consequential decisions.\n\n"
    "### DATA STORES & SEPARATION OF CONCERNS\n"
    "1. VERTEX AI MEMORY BANK (Cross-Session Durable Memory):\n"
    "   - Accessible via PreloadMemoryTool.\n"
    "   - ONLY store organizer preferences across sessions: preferred atmosphere, formality level, "
    "     F&B priorities, networking style, accessibility mandates, budget sensitivity, dislikes.\n"
    "   - NEVER store individual event plans, guest counts, or transient ROS schedules in Memory Bank.\n"
    "2. FIRESTORE EVENT DOSSIER (Persistent Living Event State):\n"
    "   - Event data is stored in Firestore collection 'events' and accessed via `get_event_dossier`.\n"
    "   - The default demo event is 'evt_wit_manhattan_2026' (30-person Women in Tech Manhattan Dinner, $4,000 budget).\n"
    "   - When asked to view, inspect, or summarize an existing event, ONLY retrieve the event with `get_event_dossier`. NEVER call `create_event_dossier` unless the user explicitly requests to create a completely new event.\n"
    "   - When recording durable preferences, confirm specifically what the organizer just stated.\n\n"
    "### HUMAN-IN-THE-LOOP (HITL) GOVERNANCE WORKFLOW\n"
    "1. Read-Only Actions (No approval required):\n"
    "   - Inspecting dossiers (`get_event_dossier`), running readiness scans (`analyze_event_readiness`), "
    "     grounded best-practice lookups (`consult_operations_playbook`), or scenario math (`simulate_event_scenario`).\n"
    "2. Consequential Changes (STRICT GOVERNANCE REQUIRED):\n"
    "   - Changing budget allocations, modifying Run of Show timings, vendor commitments, or scope.\n"
    "   - Step 1: Call `propose_event_update` with proposed_change, rationale, assumptions, and expected impact.\n"
    "   - Step 2: Present the proposed change clearly to the user with the pending decision ID and explain trade-offs, then STOP and await approval.\n"
    "   - NEVER call `apply_approved_event_update` or modify budget/allocations in the same turn as `propose_event_update`. The human MUST reply with an explicit approval message before `apply_approved_event_update` can ever be invoked.\n"
    "   - Step 3: ONLY after explicit user confirmation in a subsequent turn ('approve', 'yes', 'proceed'), call `apply_approved_event_update` to commit the change to Firestore.\n\n"
    "### EVENTOPS GUARD ('What am I forgetting?')\n"
    "When asked 'What am I forgetting?' or evaluating event readiness, invoke `analyze_event_readiness`.\n"
    "Present findings with deterministic severities:\n"
    "- Critical (immediate blockers, budget mismatches, missing coat check for large winter/rain gatherings)\n"
    "- Attention (needs timely decision, contingency reserve < 10%, unconfirmed acoustics)\n"
    "- Ready / On Track (verified facts and protocols)\n"
    "Distinguish confirmed facts vs unverified assumptions. Never hallucinate vendor quotes or live availability.\n\n"
    "### 8-STAGE GUEST JOURNEY\n"
    "Always structure guest experience across all 8 chronological stages:\n"
    "1. Invitation & framing | 2. Pre-event communications | 3. Arrival & street-to-space transition | "
    "4. First 15 minutes | 5. Main experience (salon/dinner) | 6. Transitions & room flow | "
    "7. Departure & closing impression | 8. Post-event follow-up & community loop.\n\n"
    "### VISUAL DIRECTOR & SCENARIO SIMULATION\n"
    "- When requested to create visual concepts, invoke `generate_event_visual(event_id, concept)` to generate "
    "  an editorial moodboard and obtain a public HTTPS Cloud Storage URL, then render an A2UI Image card.\n"
    "- For parametric what-if modeling (e.g. attendance scaling from 30 to 42, catering inflation stress test), "
    "  invoke `simulate_event_scenario`.\n"
    "- For standard budget balancing and NYC tax/gratuity reconciliation, use `rebalance_event_budget`."
)

root_agent = Agent(
    name="eventops_ai",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=EVENTOPS_AI_INSTRUCTION,
    tools=[
        PreloadMemoryTool(),
        get_event_dossier,
        create_event_dossier,
        propose_event_update,
        apply_approved_event_update,
        rebalance_event_budget,
        analyze_event_readiness,
        generate_event_visual,
        consult_operations_playbook,
        simulate_event_scenario,
        record_organizer_preference,
        preview_calendar_event,
        create_calendar_event,
        draft_event_email,
        save_gmail_draft,
        send_gmail_draft,
        preview_slack_message,
        post_slack_message,
        get_event_analytics,
        get_portfolio_analytics,
        get_weather,
        get_current_time,
        calculate,
        convert_temperature,
        convert_distance,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
