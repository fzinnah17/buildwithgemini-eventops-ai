import time
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright

LOCAL_SERVER_URL = "http://127.0.0.1:8080"
PORTFOLIO_DEMO_PATH = Path("portfolio-demo/index.html").resolve()
PORTFOLIO_DEMO_URL = f"file://{PORTFOLIO_DEMO_PATH}"


@pytest.mark.parametrize("target_name, url", [
    ("portfolio_demo", PORTFOLIO_DEMO_URL),
    ("local_server", LOCAL_SERVER_URL),
])
def test_theme_system_and_drawer_interaction(target_name, url):
    """
    Validates Perfect Crown theme switching, Copilot slide-over drawer,
    Active Event control popover, and zero console errors.
    """
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        page.goto(url)
        page.wait_for_selector("#heroTitle")
        page.wait_for_function(
            "document.getElementById('heroTitle').textContent !== 'Loading Event Dossier...'",
            timeout=15000,
        )
        time.sleep(0.5)

        # 1. Default Copilot State: CLOSED
        ws_classes = page.eval_on_selector("#workspaceContainer", "el => el.className")
        assert "copilot-closed" in ws_classes, f"Copilot drawer must be closed by default, got workspace classes: {ws_classes}"

        # 2. Toggle Copilot Drawer Open
        page.click("#btnToggleCopilot")
        time.sleep(0.3)
        ws_classes_open = page.eval_on_selector("#workspaceContainer", "el => el.className")
        assert "copilot-closed" not in ws_classes_open, f"Workspace should not have copilot-closed after open toggle, got: {ws_classes_open}"
        assert page.is_visible("#copilotDrawer"), "Copilot drawer must be visible when opened"

        # Close Copilot Drawer
        page.click("#btnCloseCopilotDrawer")
        time.sleep(0.3)
        ws_classes_closed = page.eval_on_selector("#workspaceContainer", "el => el.className")
        assert "copilot-closed" in ws_classes_closed, "Workspace should have copilot-closed after closing drawer"

        # 3. Active Event Popover Interaction
        assert page.is_visible("#btnEventControl"), "Active Event center control button must be visible"
        assert not page.is_visible("#eventControlPopover"), "Event popover should be hidden initially"

        page.click("#btnEventControl")
        time.sleep(0.3)
        assert page.is_visible("#eventControlPopover"), "Event popover must be visible after click"
        assert page.is_visible("#btnEditEventDossier"), "Edit Dossier button visible in popover"
        assert page.is_visible("#btnOpenNewEvent"), "Create Event button visible in popover"
        assert page.is_visible("#eventSelector"), "Event Selector visible in popover"

        # Click outside to dismiss popover
        page.click(".header-left")
        time.sleep(0.3)
        assert not page.is_visible("#eventControlPopover"), "Event popover must close when clicking outside"

        def open_more_menu():
            if not page.is_visible("#moreMenuDropdown"):
                page.click("#btnMoreMenu")
                time.sleep(0.3)

        # 4. Perfect Crown Theme Switching (System -> Light -> Dark -> System)
        open_more_menu()
        assert page.is_visible("#moreMenuDropdown"), "More menu dropdown must open"
        assert page.is_visible(".theme-toggle-strip"), "Theme selector group must be in More menu"

        # Switch to Light Theme
        page.click("#btnThemeLight")
        time.sleep(0.3)
        theme_attr = page.eval_on_selector("html", "el => el.getAttribute('data-theme')")
        assert theme_attr == "light", f"Expected data-theme='light', got {theme_attr}"
        stored_theme = page.evaluate("() => localStorage.getItem('eventops_theme')")
        assert stored_theme == "light", f"Expected localStorage eventops_theme='light', got {stored_theme}"

        # Switch to Dark Theme
        open_more_menu()
        page.click("#btnThemeDark")
        time.sleep(0.3)
        theme_attr_dark = page.eval_on_selector("html", "el => el.getAttribute('data-theme')")
        assert theme_attr_dark == "dark", f"Expected data-theme='dark', got {theme_attr_dark}"
        stored_theme_dark = page.evaluate("() => localStorage.getItem('eventops_theme')")
        assert stored_theme_dark == "dark", f"Expected localStorage eventops_theme='dark', got {stored_theme_dark}"

        # Switch back to System Theme
        open_more_menu()
        page.click("#btnThemeSystem")
        time.sleep(0.3)
        stored_theme_sys = page.evaluate("() => localStorage.getItem('eventops_theme')")
        assert stored_theme_sys == "system", f"Expected localStorage eventops_theme='system', got {stored_theme_sys}"

        # 5. Connected Services Tiles in Governance Modal
        open_more_menu()
        page.click("#btnOpenIntegrations")
        time.sleep(0.3)
        assert page.is_visible("#modalIntegrations"), "Connected Services modal must open"
        assert page.is_visible("#statusBadgeCalendar"), "Google Calendar status badge must be visible"
        assert page.is_visible("#statusBadgeGmail"), "Gmail status badge must be visible"
        assert page.is_visible("#statusBadgeSlack"), "Slack status badge must be visible"
        page.click("#modalIntegrations .modal-header .btn-header")
        time.sleep(0.3)

        # 6. Systems Architecture Diagram
        open_more_menu()
        page.click("#btnOpenAbout")
        time.sleep(0.3)
        assert page.is_visible("#modalAbout"), "About / Architecture modal must open"
        assert page.is_visible("#modalAbout svg"), "Interactive SVG architecture diagram must be present"
        page.click("#modalAbout .modal-header .btn-header")
        time.sleep(0.3)

        # 7. Zero Console Errors
        clean_errors = [e for e in console_errors if "favicon" not in e.lower()]
        assert len(clean_errors) == 0, f"Uncaught console errors detected: {clean_errors}"

        browser.close()
