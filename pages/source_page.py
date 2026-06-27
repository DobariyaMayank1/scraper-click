"""
Source page object for the TextUtils testing website.

Encapsulates all website-specific selectors and interactions.
To support a different source website, create a new page object
class with the same interface and swap it in the controller.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from config import Config
from automation.logger import get_logger
from automation.utils import multi_click, safe_wait, safe_find_elements, scroll_into_view, is_element_visible


class SourcePage:
    """
    Page Object for the source website.

    Provides methods to interact with the source page:
        - Navigate to the page
        - Handle popups
        - Find advertisements
        - Click advertisements

    All website-specific selectors are isolated here.
    """

    # --- Selectors ---
    # Popup selectors (common patterns for ad/cookie popups)
    POPUP_CLOSE_SELECTORS = [
        (By.CSS_SELECTOR, "button.btn-close"),
        (By.CSS_SELECTOR, "[data-bs-dismiss='modal']"),
        (By.CSS_SELECTOR, ".modal .close"),
        (By.CSS_SELECTOR, "button[aria-label='Close']"),
        (By.XPATH, "//button[contains(text(), 'Close')]"),
        (By.XPATH, "//button[contains(text(), '×')]"),
        (By.CSS_SELECTOR, ".popup-close"),
    ]

    # Advertisement selectors (generic patterns for common ad placements)
    AD_SELECTORS = [
        (By.CSS_SELECTOR, "iframe[id*='google_ads']"),
        (By.CSS_SELECTOR, "iframe[id*='aswift']"),
        (By.CSS_SELECTOR, "iframe[src*='doubleclick']"),
        (By.CSS_SELECTOR, "iframe[src*='googlesyndication']"),
        (By.CSS_SELECTOR, "ins.adsbygoogle"),
        (By.CSS_SELECTOR, "[id*='ad-'] a"),
        (By.CSS_SELECTOR, "[class*='ad-'] a"),
        (By.CSS_SELECTOR, "[id*='advertisement'] a"),
        (By.CSS_SELECTOR, "a[href*='googleads']"),
        (By.CSS_SELECTOR, "a[target='_blank'][rel*='sponsored']"),
        # Fallback: any external link that might be an ad
        (By.CSS_SELECTOR, "a[target='_blank'][href^='http']"),
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
        Locate clickable advertisement elements on the page.

        Searches for ads in iframes and as direct links.
        Returns a list of clickable elements.

        Returns:
            List of (element, description) tuples for found ads.
        """
        self._logger.info("Searching Advertisements")
        found_ads = []

        # First check for Google Ad iframes
        iframe_ads = self._find_iframe_ads()
        found_ads.extend(iframe_ads)

        # Then check for direct ad links
        link_ads = self._find_link_ads()
        found_ads.extend(link_ads)

        if found_ads:
            self._logger.info("Found %d potential advertisement(s)", len(found_ads))
        else:
            self._logger.warning("No advertisements found on page")

        return found_ads

    def click_advertisement(self, ad_element, description="advertisement"):
        """
        Click an advertisement element with retry and fallback.

        Args:
            ad_element: The WebElement to click.
            description: Human-readable description for logging.

        Returns:
            True if click succeeded, False otherwise.
        """
        self._logger.info("Attempting to click: %s", description)

        # Scroll the ad into view first
        scroll_into_view(self._driver, ad_element)

        # Use multi-click strategy
        if multi_click(self._driver, ad_element, description):
            self._logger.info("Advertisement Clicked")
            return True

        self._logger.warning("Failed to click advertisement: %s", description)
        return False

    def _find_iframe_ads(self):
        """Find clickable elements inside ad iframes."""
        found = []
        iframe_selectors = [
            (By.CSS_SELECTOR, "iframe[id*='google_ads']"),
            (By.CSS_SELECTOR, "iframe[id*='aswift']"),
            (By.CSS_SELECTOR, "iframe[src*='doubleclick']"),
            (By.CSS_SELECTOR, "iframe[src*='googlesyndication']"),
        ]

        for by, selector in iframe_selectors:
            iframes = safe_find_elements(
                self._driver, by, selector, description="ad iframe"
            )
            for iframe in iframes:
                if is_element_visible(iframe):
                    try:
                        # Switch into the iframe
                        self._driver.switch_to.frame(iframe)

                        # Look for clickable elements inside
                        links = safe_find_elements(
                            self._driver, By.CSS_SELECTOR, "a[href]",
                            description="iframe ad link"
                        )
                        for link in links:
                            if is_element_visible(link):
                                found.append((link, f"iframe ad link: {selector}"))
                                break  # Take first visible link per iframe

                        # Switch back to main content
                        self._driver.switch_to.default_content()

                    except Exception:
                        # Ensure we're back in main content
                        try:
                            self._driver.switch_to.default_content()
                        except Exception:
                            pass

        return found

    def _find_link_ads(self):
        """Find direct ad link elements on the page."""
        found = []
        link_selectors = [
            (By.CSS_SELECTOR, "ins.adsbygoogle a"),
            (By.CSS_SELECTOR, "[id*='ad-'] a[href]"),
            (By.CSS_SELECTOR, "[class*='ad-'] a[href]"),
            (By.CSS_SELECTOR, "a[href*='googleads']"),
            (By.CSS_SELECTOR, "a[target='_blank'][rel*='sponsored']"),
        ]

        for by, selector in link_selectors:
            elements = safe_find_elements(
                self._driver, by, selector, description="ad link"
            )
            for element in elements:
                if is_element_visible(element):
                    href = element.get_attribute("href") or ""
                    found.append((element, f"ad link: {href[:60]}"))

        # Deduplicate by element reference
        seen = set()
        unique = []
        for elem, desc in found:
            elem_id = id(elem)
            if elem_id not in seen:
                seen.add(elem_id)
                unique.append((elem, desc))

        return unique
