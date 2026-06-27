"""
Chrome browser lifecycle manager.

Creates, manages, and cleans up a single Chrome WebDriver instance.
Uses Selenium Manager for driver binary management.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException

from config import Config
from automation.logger import get_logger


class BrowserManager:
    """
    Manages a single Chrome browser instance.

    Only one Chrome window is ever created. The same instance is reused
    across all automation cycles until explicitly stopped.
    """

    def __init__(self):
        self._driver = None
        self._logger = get_logger()

    @property
    def driver(self):
        """Return the WebDriver instance, or None if not started."""
        return self._driver

    @property
    def is_alive(self):
        """Check if the browser is still responsive."""
        if self._driver is None:
            return False
        try:
            # Accessing title forces a command to the browser
            _ = self._driver.title
            return True
        except WebDriverException:
            return False

    @property
    def current_url(self):
        """Return the current browser URL, or empty string if unavailable."""
        if not self.is_alive:
            return ""
        try:
            return self._driver.current_url
        except WebDriverException:
            return ""

    def start(self):
        """
        Launch a Chrome browser instance.

        If a browser is already running and responsive, reuse it.
        Uses Selenium Manager — no manual chromedriver setup needed.
        """
        if self.is_alive:
            self._logger.info("Browser already running — reusing existing instance")
            return self._driver

        # Close any stale instance
        self._cleanup()

        self._logger.info("Opening Browser")

        options = Options()

        if Config.BROWSER_HEADLESS:
            options.add_argument("--headless=new")

        if Config.BROWSER_START_MAXIMIZED:
            options.add_argument("--start-maximized")

        # Ensure browser window is visible with a sensible size
        options.add_argument("--window-size=1280,900")

        # Disable popup blocking — we NEED pop-under ads to open new tabs
        options.add_argument("--disable-popup-blocking")

        # Disable automation detection flags
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        try:
            # Selenium Manager handles chromedriver automatically
            service = Service()
            self._driver = webdriver.Chrome(service=service, options=options)
            self._driver.set_page_load_timeout(Config.PAGE_LOAD_TIMEOUT)
            self._driver.implicitly_wait(Config.IMPLICIT_WAIT)

            # Force the window to the foreground
            self._driver.maximize_window()

            self._logger.info("Browser opened successfully")
            return self._driver

        except WebDriverException as e:
            self._logger.error("Failed to open browser: %s", str(e)[:200])
            self._driver = None
            raise

    def stop(self):
        """Close the browser and clean up resources."""
        self._logger.info("Closing Browser")
        self._cleanup()
        self._logger.info("Browser closed")

    def _cleanup(self):
        """Safely quit the browser, ignoring errors."""
        if self._driver is not None:
            try:
                self._driver.quit()
            except WebDriverException:
                pass
            finally:
                self._driver = None
