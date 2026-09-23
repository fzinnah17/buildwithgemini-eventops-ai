# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Browser-level acceptance tests for EventOps AI user interface.

Directly verifies DOM hydration, eliminates placeholder states,
and ensures zero JavaScript console errors across all 4 operational tabs.
"""

import os
import time
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PORTFOLIO_DEMO_PATH = REPO_ROOT / "portfolio-demo" / "index.html"
LOCAL_SERVER_URL = os.environ.get("EVENTOPS_TEST_URL", "http://localhost:8080/")

FORBIDDEN_PLACEHOLDER_STRINGS = [
    "Loading budget items...",
    "Loading Run of Show...",
    "Loading RACI matrix...",
    "Scanning operational gates...",
    "Loading decision ledger...",
    "Loading guest journey...",
    "Loading atmosphere specifications...",
]


def _verify_page_hydrated_and_tabs(page, url: str):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    page.goto(url)
    page.wait_for_selector("#heroTitle")
    page.wait_for_function(
        "document.getElementById(\"heroTitle\").textContent !== \"Loading Event Dossier...\"",
        timeout=15000,
    )
    time.sleep(0.5)

    # 1. Assert absence of all 7 placeholder strings anywhere in DOM
    page_content = page.content()
    for forbidden in FORBIDDEN_PLACEHOLDER_STRINGS:
        assert forbidden not in page_content, f"Hydrated DOM unexpectedly contains stale placeholder: '{forbidden}'"

    # 2. Tab 1: Overview
    hero_title = page.eval_on_selector("#heroTitle", "el => el.textContent")
    assert hero_title and hero_title != "Loading Event Dossier..."
    card_allocated = page.eval_on_selector("#cardAllocated", "el => el.textContent")
    assert "$" in card_allocated

    # 3. Tab 2: Plan & Timeline
    page.click('button[data-tab="plan"]')
    time.sleep(0.3)

    budget_rows = page.eval_on_selector_all("#budgetTableBody tr", "els => els.length")
    assert budget_rows >= 1, "Budget allocations table must contain at least 1 rendered row"
    budget_cols = page.eval_on_selector("#budgetTableBody tr", "el => el.children.length")
    assert budget_cols == 5, f"Budget table row must have 5 columns, found {budget_cols}"

    ros_nodes = page.eval_on_selector_all("#runOfShowContainer .timeline-node", "els => els.length")
    assert ros_nodes >= 1, "Run of show timeline must contain at least 1 timeline node"

    raci_rows = page.eval_on_selector_all("#raciTableBody tr", "els => els.length")
    assert raci_rows >= 1, "RACI deliverables table must contain at least 1 rendered row"
    raci_cols = page.eval_on_selector("#raciTableBody tr", "el => el.children.length")
    assert raci_cols == 5, f"RACI table row must have 5 columns, found {raci_cols}"

    # 4. Tab 3: Risks & Decisions
    page.click('button[data-tab="risks"]')
    time.sleep(0.3)

    guard_rows = page.eval_on_selector_all("#guardTableBody tr", "els => els.length")
    assert guard_rows >= 1, "Guard findings table must contain at least 1 rendered row"
    guard_cols = page.eval_on_selector("#guardTableBody tr", "el => el.children.length")
    assert guard_cols == 4, f"Guard table row must have 4 columns, found {guard_cols}"

    ledger_rows = page.eval_on_selector_all("#ledgerTableBody tr", "els => els.length")
    assert ledger_rows >= 1, "Decision ledger table must contain at least 1 rendered row"
    ledger_cols = page.eval_on_selector("#ledgerTableBody tr", "el => el.children.length")
    assert ledger_cols == 6, f"Decision ledger row must have 6 columns, found {ledger_cols}"

    # 5. Tab 4: Experience & Journey
    page.click('button[data-tab="experience"]')
    time.sleep(0.3)

    journey_cards = page.eval_on_selector_all("#journeyGrid .journey-card", "els => els.length")
    assert journey_cards >= 1, "Guest journey grid must contain at least 1 touchpoint card"

    atmos_text = page.eval_on_selector("#atmosphereText", "el => el.textContent")
    assert len(atmos_text) > 20 and "Loading" not in atmos_text

    # 6. Verify zero uncaught JavaScript errors
    assert len(console_errors) == 0, f"Uncaught console errors detected: {console_errors}"


@pytest.mark.integration
def test_portfolio_demo_browser_hydration():
    """Verify standalone static portfolio demo renders cleanly in a real browser."""
    file_url = f"file://{PORTFOLIO_DEMO_PATH.resolve()}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            _verify_page_hydrated_and_tabs(page, file_url)
        finally:
            browser.close()


@pytest.mark.integration
def test_local_server_browser_hydration():
    """Verify live FastAPI / Cloud Run frontend service renders cleanly in a real browser."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            _verify_page_hydrated_and_tabs(page, LOCAL_SERVER_URL)
        finally:
            browser.close()
