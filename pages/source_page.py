"""
Source page object for the TextUtils testing website.

Encapsulates all website-specific selectors and interactions.
To support a different source website, create a new page object
class with the same interface and swap it in the controller.

TextUtils uses Monetag/Adsterra pop-under ads. These ads work by
intercepting clicks on the page body — any click triggers a new
tab/pop-under. There are NO visible banner ads to locate and click.
The strategy is: click on the page body to trigger the pop-under.
"""

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException

from config import Config
from automation.logger import get_logger
from automation.utils import multi_click, safe_wait, safe_find_elements, is_element_visible


class SourcePage:
    """
    Page Object for the source website.

    Provides methods to interact with the source page:
        - Navigate to the page
        - Handle popups
        - Trigger advertisement interactions
        - Click to activate pop-under ads

    All website-specific selectors are isolated here.
    """

    # --- Selectors ---
    # Popup/modal close selectors (common patterns)
    POPUP_CLOSE_SELECTORS = [
        (By.CSS_SELECTOR, "button.btn-close"),
        (By.CSS_SELECTOR, "[data-bs-dismiss='modal']"),
        (By.CSS_SELECTOR, ".modal .close"),
        (By.CSS_SELECTOR, "button[aria-label='Close']"),
        (By.XPATH, "//button[contains(text(), 'Close')]"),
        (By.XPATH, "//button[contains(text(), '×')]"),
        (By.CSS_SELECTOR, ".popup-close"),
    ]

    # Clickable regions on the page to trigger pop-under ads.
    # Monetag/Adsterra inject invisible overlays that intercept body clicks.
    # We click on different areas of the page to trigger them.
    CLICK_TARGET_SELECTORS = [
        (By.CSS_SELECTOR, "body"),
        (By.CSS_SELECTOR, "h1"),
        (By.CSS_SELECTOR, "h2"),
        (By.CSS_SELECTOR, ".container"),
        (By.CSS_SELECTOR, "textarea"),
        (By.CSS_SELECTOR, "p"),
        (By.CSS_SELECTOR, "nav"),
    ]

    def __init__(self, driver):
        self._driver = driver
        self._logger = get_logger()

    def open(self, url=None):
        """
        Navigate to the source website.

        Args:
            url: Override URL. Defaults to Config.SOURCE_URL.
        """
        target = url or Config.SOURCE_URL
        self._logger.info("Opening Source Website: %s", target)

        try:
            self._driver.get(target)
            self._logger.info("Source website loaded")
            return True
        except Exception as e:
            self._logger.error("Failed to open source website: %s", str(e)[:200])
            return False

    def wait_for_page_ready(self):
        """Wait until the page's document.readyState is 'complete'."""
        result = safe_wait(
            self._driver,
            lambda d: d.execute_script("return document.readyState") == "complete",
            Config.PAGE_LOAD_TIMEOUT,
            description="page ready state"
        )
        return result is not None

    def close_popup(self):
        """
        Attempt to detect and close any popup/modal on the page.

        Tries multiple selectors and click strategies.
        If no popup is found, continues silently.

        Returns:
            True if a popup was found and closed.
            False if no popup was detected (not an error).
        """
        self._logger.info("Checking for popups")

        for attempt in range(Config.MAX_POPUP_RETRIES):
            for by, selector in self.POPUP_CLOSE_SELECTORS:
                elements = safe_find_elements(
                    self._driver, by, selector, description="popup close button"
                )

                for element in elements:
                    if is_element_visible(element):
                        self._logger.info("Popup Found — attempting to close")

                        if multi_click(self._driver, element, "popup close button"):
                            self._logger.info("Popup Closed")
                            return True

            # Brief pause before retry
            if attempt < Config.MAX_POPUP_RETRIES - 1:
                safe_wait(
                    self._driver,
                    lambda d: False,  # Just a sleep
                    1,
                    description="popup retry wait"
                )

        self._logger.info("No popup detected — continuing")
        return False

    def find_advertisements(self):
        """
        Locate clickable elements that will trigger ad interactions.

        TextUtils uses Monetag/Adsterra pop-under ads. These work by
        intercepting clicks anywhere on the page body. There are NO
        visible banner ads — clicking the page itself triggers a new
        tab/pop-under with the advertiser's page.

        Returns:
            List of (element, description) tuples for clickable targets.
        """
        self._logger.info("Searching Advertisements")

        # Wait a moment for ad scripts to initialize
        time.sleep(2)

        found_targets = []

        # Strategy 1: Look for any visible elements to click on
        for by, selector in self.CLICK_TARGET_SELECTORS:
            elements = safe_find_elements(
                self._driver, by, selector, description=f"click target ({selector})"
            )
            for element in elements:
                if is_element_visible(element):
                    found_targets.append((element, f"page element: {selector}"))
                    break  # One target per selector is enough

        if found_targets:
            self._logger.info(
                "Found %d clickable target(s) for ad trigger", len(found_targets)
            )
        else:
            self._logger.warning("No clickable targets found on page")

        return found_targets

    def click_advertisement(self, ad_element, description="advertisement"):
        """
        Click on a page element to trigger pop-under ad.

        Monetag/Adsterra pop-under ads intercept clicks on the page body.
        Clicking any visible element on the page will trigger a new
        tab/window to open with the advertiser's content.

        Args:
            ad_element: The WebElement to click.
            description: Human-readable description for logging.

        Returns:
            True if click succeeded, False otherwise.
        """
        self._logger.info("Clicking page to trigger ad: %s", description)

        try:
            # Record window handles before click
            handles_before = set(self._driver.window_handles)

            # Use ActionChains for a more "human-like" click
            ActionChains(self._driver).move_to_element(ad_element).click().perform()

            # Give the ad script a moment to react
            time.sleep(1.5)

            # Check if a new tab was opened (pop-under triggered)
            handles_after = set(self._driver.window_handles)
            new_handles = handles_after - handles_before

            if new_handles:
                self._logger.info(
                    "Advertisement Clicked — %d new tab(s) opened", len(new_handles)
                )
                return True

            # If no new tab, try JavaScript click as fallback
            self._logger.debug("No new tab from ActionChains click, trying JS click")
            self._driver.execute_script("arguments[0].click();", ad_element)
            time.sleep(1.5)

            handles_after = set(self._driver.window_handles)
            new_handles = handles_after - handles_before

            if new_handles:
                self._logger.info(
                    "Advertisement Clicked via JS — %d new tab(s) opened", len(new_handles)
                )
                return True

            self._logger.warning("Click did not trigger any new tab")
            return False

        except WebDriverException as e:
            self._logger.warning("Click failed: %s", str(e)[:150])
            return False
