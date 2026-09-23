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


def _verify_staffing_ratio_and_overview_attention(page, url: str):
    import re

    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    page.goto(url)
    page.wait_for_selector("#eventSelector")
    page.wait_for_function(
        "document.getElementById(\"heroTitle\").textContent !== \"Loading Event Dossier...\"",
        timeout=15000,
    )
    time.sleep(0.5)

    # 1. Switch to evt_design_summit_2026
    page.select_option("#eventSelector", "evt_design_summit_2026")
    time.sleep(0.5)

    # Assertion 1: Staffing ratio for evt_design_summit_2026 is populated (approx 1 : 10.6)
    staff_ratio = page.eval_on_selector("#cardStaffRatio", "el => el.textContent").strip()
    assert staff_ratio != "-", f"Staffing ratio must not remain '-': {staff_ratio}"
    assert "10.6" in staff_ratio, f"Expected 1 : 10.6, got {staff_ratio}"

    # Verify cardStaffCount element exists and is populated
    staff_count = page.eval_on_selector("#cardStaffCount", "el => el.textContent").strip()
    assert "8" in staff_count or "Staff" in staff_count, f"Expected staff count populated, got '{staff_count}'"

    # Assertion 2: Readiness 100 with zero active findings does not display "1 ACTION REQUIRED"
    badge_text = page.eval_on_selector("#overviewAttentionCount", "el => el.textContent").strip()
    assert "1 ACTION REQUIRED" not in badge_text.upper(), (
        f"Readiness 100 with 0 findings must not display '1 ACTION REQUIRED': got '{badge_text}'"
    )
    assert badge_text.upper() in ["0 ACTIONS REQUIRED", "ALL CLEAR"], (
        f"Expected 'ALL CLEAR' or '0 ACTIONS REQUIRED', got '{badge_text}'"
    )

    # Assertion 3: No empty attention panel exists
    attention_list = page.eval_on_selector("#overviewAttentionList", "el => el.textContent").strip()
    assert len(attention_list) > 0, "Overview attention panel must never be empty"
    assert "All operational readiness gates are satisfied" in attention_list, (
        f"Zero-finding panel body must indicate gates satisfied: got '{attention_list}'"
    )

    # Assertion 4: Overview attention count matches rendered findings across all events
    options = page.eval_on_selector_all("#eventSelector option", "els => els.map(o => o.value)")
    for eid in options:
        page.select_option("#eventSelector", eid)
        time.sleep(0.5)

        cur_badge = page.eval_on_selector("#overviewAttentionCount", "el => el.textContent").strip()
        cur_panel_text = page.eval_on_selector("#overviewAttentionList", "el => el.textContent").strip()
        cur_items = page.eval_on_selector_all("#overviewAttentionList .attention-item", "els => els.length")

        # Never empty
        assert len(cur_panel_text) > 0, f"Attention panel empty for event {eid}"
        assert cur_items >= 1, f"Expected at least 1 attention-item for event {eid}"

        if "ACTION" in cur_badge.upper() and not cur_badge.upper().startswith("0"):
            m = re.search(r"(\d+)\s+ACTION", cur_badge, re.IGNORECASE)
            assert m is not None, f"Could not parse action count from badge '{cur_badge}'"
            badge_count = int(m.group(1))
            assert badge_count == cur_items, (
                f"Badge count ({badge_count}) must equal rendered findings ({cur_items}) for event {eid}"
            )
        else:
            assert cur_badge.upper() in ["ALL CLEAR", "0 ACTIONS REQUIRED"]
            assert "All operational readiness gates are satisfied" in cur_panel_text

    assert len(console_errors) == 0, f"Uncaught console errors: {console_errors}"


@pytest.mark.integration
def test_portfolio_demo_staffing_and_attention():
    """Verify staffing ratio and attention panel lifecycle on standalone portfolio demo."""
    file_url = f"file://{PORTFOLIO_DEMO_PATH.resolve()}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            _verify_staffing_ratio_and_overview_attention(page, file_url)
        finally:
            browser.close()


@pytest.mark.integration
def test_local_server_staffing_and_attention():
    """Verify staffing ratio and attention panel lifecycle on local FastAPI server."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            _verify_staffing_ratio_and_overview_attention(page, LOCAL_SERVER_URL)
        finally:
            browser.close()
