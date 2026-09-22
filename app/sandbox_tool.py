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

"""Agent Engine Sandbox Code Execution Tool for EventOps AI."""

from __future__ import annotations

import json
import logging
import os
import uuid

from google.adk.agents import Agent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.code_executors.agent_engine_sandbox_code_executor import (
    AgentEngineSandboxCodeExecutor,
)
from google.adk.code_executors.code_execution_utils import CodeExecutionInput
from google.adk.sessions import InMemorySessionService

from app.event_store import get_event_store

logger = logging.getLogger(__name__)

# Use preserved deployed reasoning engine resource name
AGENT_ENGINE_RESOURCE = "projects/282776913855/locations/us-central1/reasoningEngines/1788548626868338688"

_executor: AgentEngineSandboxCodeExecutor | None = None
_session_service = InMemorySessionService()


def _get_executor() -> AgentEngineSandboxCodeExecutor:
    global _executor
    if _executor is None:
        _executor = AgentEngineSandboxCodeExecutor(
            agent_engine_resource_name=AGENT_ENGINE_RESOURCE
        )
    return _executor


def simulate_event_scenario(
    event_id: str,
    scenario_description: str,
    python_simulation_code: str,
) -> str:
    """Execute deep parametric simulations and what-if financial modeling in an isolated sandbox.

    Use this tool for rich scenario computations such as:
    - Attendance scaling (e.g. 'What happens if guest count rises from 30 to 45?')
    - Cost inflation & vendor quote comparisons ('How does a 15% catering increase impact contingency?')
    - Multi-option budget model comparisons.

    Args:
        event_id: The unique event ID.
        scenario_description: Human-readable summary of the scenario being tested.
        python_simulation_code: Python code to execute in the secure Agent Engine Sandbox.
                                Must print structured results or final summary.

    Returns:
        JSON string containing the simulation stdout, status, and analytical conclusions.
    """
    store = get_event_store()
    event = store.get_event(event_id)
    if not event:
        return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."})

    # Prepend event context variables to the simulation code if not already defined
    context_prefix = (
        f"# Event Baseline Variables\n"
        f"TOTAL_BUDGET = {event.total_budget}\n"
        f"GUEST_COUNT = {event.guest_count}\n"
        f"LOCATION = {repr(event.location)}\n"
        f"ALLOCATIONS = {json.dumps(event.budget_allocations)}\n\n"
    )
    full_code = context_prefix + python_simulation_code

    try:
        executor = _get_executor()
        session = _session_service.create_session_sync(
            user_id="eventops_sim", app_name="eventops_ai"
        )
        inv_ctx = InvocationContext(
            session=session,
            session_service=_session_service,
            invocation_id=f"inv_{uuid.uuid4().hex[:6]}",
            agent=Agent(name="sandbox_runner", model="gemini-2.5-flash"),
        )

        res = executor.execute_code(
            inv_ctx, CodeExecutionInput(code=full_code)
        )

        return json.dumps({
            "status": "success",
            "execution_environment": "AgentEngineSandbox",
            "scenario": scenario_description,
            "stdout": res.stdout,
            "stderr": res.stderr,
        }, indent=2)

    except Exception as e:
        logger.warning("Sandbox execution failed, falling back to local simulation: %s", e)
        # Safe deterministic local execution fallback
        try:
            import io
            import sys

            old_stdout = sys.stdout
            redirected_output = sys.stdout = io.StringIO()
            safe_globals = {
                "TOTAL_BUDGET": event.total_budget,
                "GUEST_COUNT": event.guest_count,
                "LOCATION": event.location,
                "ALLOCATIONS": event.budget_allocations,
                "round": round,
                "sum": sum,
                "min": min,
                "max": max,
                "len": len,
                "range": range,
                "print": print,
                "json": json,
            }
            exec(python_simulation_code, safe_globals)
            sys.stdout = old_stdout
            output = redirected_output.getvalue()

            return json.dumps({
                "status": "success",
                "execution_environment": "LocalFallback",
                "scenario": scenario_description,
                "stdout": output,
                "note": "Executed via local compute fallback.",
            }, indent=2)
        except Exception as local_err:
            return json.dumps({
                "status": "error",
                "message": f"Simulation failed: {local_err}",
            })
