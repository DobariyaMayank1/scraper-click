"""
Navigation manager for post-click advertisement handling.

Handles two scenarios after an ad is clicked:
    Case 1: Ad opens a NEW browser tab
    Case 2: Ad replaces the current page

Also contains the placeholder for future destination scraping.
"""

import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchWindowException,
)

from config import Config
from automation.logger import get_logger


class NavigationManager:
    """
    Manages navigation after an advertisement click.

    Detects whether the ad opened a new tab or replaced the current page,
    handles the destination, then returns to the source website.
    """

    def __init__(self, driver):
        self._driver = driver
        self._logger = get_logger()

    def handle_post_click(self, original_handle, original_url):
        """
        Handle navigation after an ad click.

        Detects the navigation case (new tab vs same tab) and delegates
        to the appropriate handler.

        Args:
            original_handle: The window handle of the source page before click.
            original_url: The URL of the source page before click.

        Returns:
            True if destination was reached and source was restored.
            False on failure.
        """
        try:
            # Brief pause to let the browser react to the click
            time.sleep(1)

            current_handles = self._driver.window_handles

            if len(current_handles) > 1 and original_handle in current_handles:
                # Case 1: New tab opened
                return self._handle_new_tab(original_handle)
            else:
                # Case 2: Same tab navigation (URL changed)
                return self._handle_same_tab(original_url)

        except WebDriverException as e:
            self._logger.warning("Navigation handling failed: %s", str(e)[:150])
            return False

    def _handle_new_tab(self, original_handle):
        """
        Handle Case 1: Advertisement opened a new browser tab.

        Switch to the new tab, wait for load, stay briefly,
        close the tab, and return to the original tab.
        """
        self._logger.info("New Tab Detected")

        try:
            # Find the new tab handle
            all_handles = self._driver.window_handles
            new_handles = [h for h in all_handles if h != original_handle]

            if not new_handles:
                self._logger.warning("Expected new tab but none found")
                return False

            # Switch to the newest tab
            new_handle = new_handles[-1]
            self._driver.switch_to.window(new_handle)

            # Wait for the destination page to load
            self._wait_for_page_load()
            self._logger.info("Destination Loaded: %s", self._safe_url())

            # Placeholder: future scraping will happen here
            scrape_destination_page(self._driver)

            # Stay on destination briefly
            self._logger.info(
                "Staying on destination for %ds", Config.DESTINATION_STAY_DURATION
            )
            time.sleep(Config.DESTINATION_STAY_DURATION)

            # Close the destination tab
            try:
                self._driver.close()
            except WebDriverException:
                pass

            # Switch back to the original tab
            try:
                self._driver.switch_to.window(original_handle)
                self._logger.info("Returned to source tab")
            except NoSuchWindowException:
                self._logger.warning("Original tab no longer exists")
                # Try to switch to any remaining tab
                remaining = self._driver.window_handles
                if remaining:
                    self._driver.switch_to.window(remaining[0])
                else:
                    return False

            return True

        except WebDriverException as e:
            self._logger.warning("New tab handling error: %s", str(e)[:150])
            # Attempt recovery — switch back to original
            self._recover_to_handle(original_handle)
            return False

    def _handle_same_tab(self, original_url):
        """
        Handle Case 2: Advertisement replaced the current page.

        Wait for the destination to load, stay briefly,
        then navigate back to the source URL.
        """
        current_url = self._safe_url()

        # Check if URL actually changed
        if current_url == original_url:
            self._logger.info("URL did not change after click — ad may have failed")
            return False

        self._logger.info("Page replaced — destination: %s", current_url)

        # Wait for destination page load
        self._wait_for_page_load()
        self._logger.info("Destination Loaded: %s", self._safe_url())

        # Placeholder: future scraping will happen here
        scrape_destination_page(self._driver)

        # Stay on destination briefly
        self._logger.info(
            "Staying on destination for %ds", Config.DESTINATION_STAY_DURATION
        )
        time.sleep(Config.DESTINATION_STAY_DURATION)

        # Navigate back
        self._logger.info("Navigating back to source")
        try:
            self._driver.back()

            # Wait for source page to reload
            WebDriverWait(self._driver, Config.SOURCE_RELOAD_TIMEOUT).until(
                lambda d: original_url in d.current_url
                or d.execute_script("return document.readyState") == "complete"
            )
            self._logger.info("Returned to source page")
            return True

        except (TimeoutException, WebDriverException) as e:
            self._logger.warning("Back navigation failed: %s", str(e)[:150])
            # Force navigate to source
            try:
                self._driver.get(original_url)
                self._logger.info("Force-navigated back to source")
                return True
            except WebDriverException:
                return False

    def _wait_for_page_load(self):
        """Wait for the current page to finish loading."""
        try:
            WebDriverWait(self._driver, Config.DESTINATION_WAIT_TIMEOUT).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            self._logger.debug("Page load wait timed out — continuing anyway")

    def _safe_url(self):
        """Return current URL without raising."""
        try:
            return self._driver.current_url
        except WebDriverException:
            return "<unavailable>"

    def _recover_to_handle(self, handle):
        """Attempt to switch back to a specific window handle."""
        try:
            if handle in self._driver.window_handles:
                self._driver.switch_to.window(handle)
        except WebDriverException:
            pass


def scrape_destination_page(driver):
    """
    Placeholder for future destination page scraping.

    This function will be expanded in a future milestone to extract:
        - Company Name
        - Emails
        - Phone Numbers
        - Address
        - Social Media Links
        - Website Metadata

    Currently only logs that the destination was reached.
    """
    logger = get_logger()
    logger.info("Destination page reached — future scraping starts here")
