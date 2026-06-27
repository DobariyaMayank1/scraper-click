"""
Automation controller — orchestrates a single automation cycle.

Uses the state machine to progress through each step of the workflow:
    OPEN_SOURCE → WAIT_PAGE → HANDLE_POPUP → LOCATE_AD → CLICK_AD
    → WAIT_DESTINATION → DESTINATION_READY → RETURN_SOURCE → WAIT_NEXT_CYCLE

Each state has a dedicated handler method. Errors are caught per-state
and the machine transitions gracefully instead of crashing.
"""

import time

from config import Config
from automation.logger import get_logger
from automation.state_machine import StateMachine, AutomationState
from automation.browser import BrowserManager
from automation.navigation import NavigationManager
from pages.source_page import SourcePage


class AutomationController:
    """
    Orchestrates one complete automation cycle.

    Owns the state machine and delegates work to the BrowserManager,
    SourcePage, and NavigationManager. The Worker calls run_cycle()
    repeatedly.
    """

    def __init__(self, browser_manager):
        """
        Args:
            browser_manager: Shared BrowserManager instance.
        """
        self._browser = browser_manager
        self._state_machine = StateMachine()
        self._logger = get_logger()
        self._cycle_count = 0

        # These are initialized when the browser starts
        self._source_page = None
        self._nav_manager = None

    @property
    def state(self):
        """Current state name."""
        return self._state_machine.state_name

    @property
    def cycle_count(self):
        """Number of completed cycles."""
        return self._cycle_count

    def run_cycle(self, stop_event):
        """
        Execute one full automation cycle through all states.

        Args:
            stop_event: threading.Event — checked before each state transition.

        Returns:
            True if cycle completed, False if stopped or error.
        """
        # State: OPEN_SOURCE
        if not self._check_stop(stop_event):
            return False
        self._transition(AutomationState.OPEN_SOURCE)

        if not self._open_source():
            return self._handle_error(stop_event)

        # State: WAIT_PAGE
        if not self._check_stop(stop_event):
            return False
        self._transition(AutomationState.WAIT_PAGE)

        if not self._wait_for_page():
            return self._handle_error(stop_event)

        # State: HANDLE_POPUP
        if not self._check_stop(stop_event):
            return False
        self._transition(AutomationState.HANDLE_POPUP)
        self._handle_popup()  # Never fails — popup is optional

        # State: LOCATE_AD
        if not self._check_stop(stop_event):
            return False
        self._transition(AutomationState.LOCATE_AD)

        ads = self._locate_ads()
        if not ads:
            self._logger.warning("No ads found — skipping to next cycle")
            self._transition(AutomationState.WAIT_NEXT_CYCLE)
            self._wait_next_cycle(stop_event)
            return True

        # State: CLICK_AD
        if not self._check_stop(stop_event):
            return False
        self._transition(AutomationState.CLICK_AD)

        # Record state before click for navigation handling
        original_handle = self._browser.driver.current_window_handle
        original_url = self._browser.current_url

        click_success = self._click_ad(ads)
        if not click_success:
            self._logger.warning("All ad click attempts failed — skipping to next cycle")
            self._transition(AutomationState.WAIT_NEXT_CYCLE)
            self._wait_next_cycle(stop_event)
            return True

        # State: WAIT_DESTINATION
        if not self._check_stop(stop_event):
            return False
        self._transition(AutomationState.WAIT_DESTINATION)

        nav_success = self._nav_manager.handle_post_click(
            original_handle, original_url
        )

        if nav_success:
            # State: DESTINATION_READY
            self._transition(AutomationState.DESTINATION_READY)
            self._logger.info("Destination interaction complete")

        # State: RETURN_SOURCE
        if not self._check_stop(stop_event):
            return False
        self._transition(AutomationState.RETURN_SOURCE)
        self._ensure_source_page()
        self._logger.info("Returning To Source")

        # State: WAIT_NEXT_CYCLE
        self._transition(AutomationState.WAIT_NEXT_CYCLE)
        self._cycle_count += 1
        self._logger.info("Cycle %d Completed", self._cycle_count)
        self._wait_next_cycle(stop_event)

        return True

    def reset(self):
        """Reset the controller state for a fresh start."""
        self._state_machine.reset()
        self._cycle_count = 0
        self._source_page = None
        self._nav_manager = None

    # --- Private State Handlers ---

    def _open_source(self):
        """Open the source website."""
        try:
            driver = self._browser.start()
            self._source_page = SourcePage(driver)
            self._nav_manager = NavigationManager(driver)
            return self._source_page.open()
        except Exception as e:
            self._logger.error("Failed to open source: %s", str(e)[:200])
            return False

    def _wait_for_page(self):
        """Wait for the source page to be ready."""
        try:
            return self._source_page.wait_for_page_ready()
        except Exception as e:
            self._logger.error("Page wait failed: %s", str(e)[:200])
            return False

    def _handle_popup(self):
        """Handle popups — never fails, popup is optional."""
        try:
            self._source_page.close_popup()
        except Exception as e:
            self._logger.warning("Popup handling error: %s", str(e)[:150])

    def _locate_ads(self):
        """Find advertisements on the page."""
        try:
            return self._source_page.find_advertisements()
        except Exception as e:
            self._logger.warning("Ad search error: %s", str(e)[:150])
            return []

    def _click_ad(self, ads):
        """
        Attempt to click an advertisement from the found list.

        Tries each ad up to MAX_AD_RETRIES times.
        """
        for attempt in range(min(Config.MAX_AD_RETRIES, len(ads))):
            ad_element, description = ads[attempt % len(ads)]
            try:
                if self._source_page.click_advertisement(ad_element, description):
                    return True
            except Exception as e:
                self._logger.warning(
                    "Ad click attempt %d failed: %s", attempt + 1, str(e)[:150]
                )
        return False

    def _ensure_source_page(self):
        """Make sure we're back on the source page."""
        try:
            current = self._browser.current_url
            if Config.SOURCE_URL not in current:
                self._logger.info("Not on source page — navigating back")
                self._source_page.open()
                self._source_page.wait_for_page_ready()
        except Exception as e:
            self._logger.warning("Source page recovery: %s", str(e)[:150])
            try:
                self._source_page.open()
            except Exception:
                pass

    def _wait_next_cycle(self, stop_event):
        """Wait between cycles, checking stop flag periodically."""
        self._logger.info(
            "Waiting %ds before next cycle", Config.CYCLE_DELAY
        )
        # Use stop_event.wait() instead of time.sleep() for responsive stopping
        stop_event.wait(timeout=Config.CYCLE_DELAY)

    def _handle_error(self, stop_event):
        """Handle an error state — attempt recovery."""
        self._transition(AutomationState.ERROR)
        self._logger.warning("Error occurred — attempting recovery")

        # Wait a moment then try to continue
        stop_event.wait(timeout=Config.CYCLE_DELAY)

        if stop_event.is_set():
            return False

        # Try to recover by going back to source
        self._transition(AutomationState.WAIT_NEXT_CYCLE)
        return True

    def _transition(self, state):
        """Transition the state machine and log."""
        old = self._state_machine.state_name
        if self._state_machine.transition(state):
            self._logger.debug("State: %s → %s", old, state.name)
        else:
            self._logger.warning(
                "Invalid state transition: %s → %s", old, state.name
            )

    def _check_stop(self, stop_event):
        """Check if stop was requested. Transition to STOPPED if so."""
        if stop_event.is_set():
            self._transition(AutomationState.STOPPED)
            return False
        return True
