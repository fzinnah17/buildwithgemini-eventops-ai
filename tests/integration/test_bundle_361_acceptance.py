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

"""Automated browser acceptance tests for Bundle 3.6.1.

Verifies:
1. Header structure (selector, edit button, create button, more menu).
2. Semicircle gauge, gates card, segmented budget bar, RACI progress, risk profile, decision pipeline.
3. 3-step Create Event wizard rejecting 'Untitled Event' and requiring valid title.
4. Edit Event Dossier modal with concise diff preview before saving.
5. Analytics scope switching: Active Event vs Portfolio Aggregate with fleet comparison bars.
"""

import os
import time
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PORTFOLIO_DEMO_PATH = REPO_ROOT / "portfolio-demo" / "index.html"
LOCAL_SERVER_URL = os.environ.get("EVENTOPS_TEST_URL", "http://localhost:8080/")


def _verify_bundle_361_features(page, url: str):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    page.goto(url)
    page.wait_for_selector("#heroTitle")
    page.wait_for_function(
        "document.getElementById('heroTitle').textContent !== 'Loading Event Dossier...'",
        timeout=15000,
    )
    time.sleep(0.5)

    # 1. Header Structure (Active Event Popover)
    if not page.is_visible("#eventSelector") and page.is_visible("#btnEventControl"):
        page.click("#btnEventControl")
        time.sleep(0.2)
    assert page.is_visible("#eventSelector"), "Event selector must be visible"
    assert page.is_visible("#btnEditEventDossier"), "Edit Dossier button must be visible in header"
    assert page.is_visible("#btnOpenNewEvent"), "Create Event button must be visible in header"
    assert page.is_visible("#btnMoreMenu"), "More menu button must be visible in header"

    # Test More menu toggle
    page.click("#btnMoreMenu")
    time.sleep(0.2)
    assert page.is_visible("#moreMenuDropdown"), "More menu dropdown must appear on click"
    assert page.is_visible("#btnOpenIntegrations"), "Connected Services in More menu"
    assert page.is_visible("#btnOpenAnalytics"), "Executive Analytics in More menu"
    page.click("body")
    time.sleep(0.2)

    # 2. Visual Elements: Overview Tab
    assert page.is_visible("#readinessGaugePath"), "Semicircle readiness gauge SVG path must be present"
    assert page.is_visible("#heroGateStatus"), "Readiness Gate Status badge must be visible"
    gauge_offset = page.eval_on_selector("#readinessGaugePath", "el => el.getAttribute('stroke-dashoffset')")
    assert gauge_offset is not None, "Gauge path stroke-dashoffset must be computed"

    # 3. Visual Elements: Plan Tab
    page.click('button[data-tab="plan"]')
    time.sleep(0.3)
    assert page.is_visible("#budgetSegmentedBar"), "Segmented budget bar must be visible"
    assert page.is_visible("#budgetLegend"), "Budget legend must be visible"
    seg_items = page.eval_on_selector_all("#budgetSegmentedBar .budget-segment", "els => els.length")
    assert seg_items >= 2, f"Segmented budget bar should contain category segments, found {seg_items}"
    assert page.is_visible("#raciProgressSummary"), "RACI progress summary bar must be visible"

    # 4. Visual Elements: Risks Tab
    page.click('button[data-tab="risks"]')
    time.sleep(0.3)
    assert page.is_visible("#riskDistributionBar"), "Risk severity distribution bar must be visible"
    assert page.is_visible("#decisionPipelineBar"), "Decision governance pipeline bar must be visible"

    # 5. Create Event Wizard & Title Validation
    if not page.is_visible("#btnOpenNewEvent") and page.is_visible("#btnEventControl"):
        page.click("#btnEventControl")
        time.sleep(0.2)
    page.click("#btnOpenNewEvent")
    time.sleep(0.3)
    assert page.is_visible("#modalNewEvent"), "Create modal must open"
    assert page.is_visible("#wizardPane1"), "Step 1 must be active"

    # Try advancing with invalid title
    page.fill("#newEventTitle", "Untitled Event")
    page.click("#btnWizardNext")
    time.sleep(0.2)
    assert page.is_visible("#newEventTitleError"), "Inline validation must block 'Untitled Event'"
    assert page.is_visible("#wizardPane1"), "Must remain on Step 1"

    # Advance with valid title
    page.fill("#newEventTitle", "AI Systems Leadership Summit")
    page.fill("#newEventLocation", "Pier 57, New York, NY")
    page.click("#btnWizardNext")
    time.sleep(0.2)
    assert page.is_visible("#wizardPane2"), "Step 2 must become active"

    # Advance to Step 3
    page.fill("#newEventGuests", "55")
    page.fill("#newEventBudget", "12500")
    page.click("#btnWizardNext")
    time.sleep(0.2)
    assert page.is_visible("#wizardPane3"), "Step 3 summary must be active"
    summary_title = page.eval_on_selector("#wizSummaryTitle", "el => el.textContent")
    assert "AI Systems Leadership Summit" in summary_title

    # Cancel modal
    page.click("#modalNewEvent .btn-header:has-text('Cancel')")
    time.sleep(0.2)
    assert not page.is_visible("#modalNewEvent")

    # 6. Edit Event Dossier & Diff Flow
    if not page.is_visible("#btnEditEventDossier") and page.is_visible("#btnEventControl"):
        page.click("#btnEventControl")
        time.sleep(0.2)
    page.click("#btnEditEventDossier")
    time.sleep(0.3)
    assert page.is_visible("#modalEditEvent"), "Edit Dossier modal must open"

    cur_guests = page.input_value("#editEventGuests")
    new_guests = str(int(cur_guests) + 10)
    page.fill("#editEventGuests", new_guests)

    # Click Review Changes
    page.click("#btnReviewEditChanges")
    time.sleep(0.3)
    assert page.is_visible("#modalEditDiff"), "Edit Diff modal must open"
    diff_text = page.eval_on_selector("#editDiffList", "el => el.textContent")
    assert "Guest Count" in diff_text
    assert f"{new_guests} guests" in diff_text

    # Back to edit then cancel (do NOT mutate canonical event!)
    page.click("#btnBackToEdit")
    time.sleep(0.2)
    assert page.is_visible("#modalEditEvent")
    page.click("#modalEditEvent .btn-header:has-text('✕')")
    time.sleep(0.2)
    assert not page.is_visible("#modalEditEvent")

    # 7. Analytics Multi-Scope & Comparative Bars
    page.click("#btnMoreMenu")
    time.sleep(0.2)
    page.click("#btnOpenAnalytics")
    time.sleep(0.3)
    assert page.is_visible("#modalAnalytics"), "Analytics modal must open"

    # Event scope
    page.click("#btnScopeEvent")
    time.sleep(0.3)
    assert not page.is_visible("#portfolioComparisonSection"), "Portfolio comparison hidden in event scope"

    # Portfolio scope
    page.click("#btnScopePortfolio")
    assert page.is_visible("#portfolioComparisonSection"), "Portfolio comparison visible in portfolio scope"
    page.wait_for_selector("#comparisonReadinessBars div", timeout=10000)
    r_bars = page.eval_on_selector_all("#comparisonReadinessBars div", "els => els.length")
    b_bars = page.eval_on_selector_all("#comparisonBudgetBars div", "els => els.length")
    assert r_bars >= 1, "Fleet readiness bars must be rendered"
    assert b_bars >= 1, "Fleet budget bars must be rendered"

    # Check honest reliability display
    tel_status = page.eval_on_selector("#anSysTelemetryStatus", "el => el.textContent").strip()
    assert tel_status in ["MEASURED", "DEMO / NOT MEASURED"], f"Telemetry status must be honest, got: {tel_status}"

    page.click("#modalAnalytics .btn-header:has-text('✕')")
    time.sleep(0.2)

    assert len(console_errors) == 0, f"Uncaught console errors detected: {console_errors}"


@pytest.mark.integration
def test_portfolio_demo_bundle_361():
    """Verify Bundle 3.6.1 features in standalone portfolio demo mode."""
    file_url = f"file://{PORTFOLIO_DEMO_PATH.resolve()}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            _verify_bundle_361_features(page, file_url)
        finally:
            browser.close()


@pytest.mark.integration
def test_local_server_bundle_361():
    """Verify Bundle 3.6.1 features on live FastAPI local server."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            _verify_bundle_361_features(page, LOCAL_SERVER_URL)
        finally:
            browser.close()
