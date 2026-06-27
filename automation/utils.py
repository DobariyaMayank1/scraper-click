"""
Shared utilities for Selenium automation.

Contains reusable helpers for clicking, waiting, and other common operations
that are used across multiple modules.
"""

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)

from automation.logger import get_logger


def multi_click(driver, element, description="element"):
    """
    Attempt to click an element using multiple strategies.

    Tries in order:
        1. Standard Selenium click
        2. JavaScript click
        3. ActionChains click

    Args:
        driver: Selenium WebDriver instance.
        element: The WebElement to click.
        description: Human-readable name for logging.

    Returns:
        True if any click method succeeded, False otherwise.
    """
    logger = get_logger()

    # Strategy 1: Normal click
    try:
        element.click()
        logger.info("Clicked %s via normal click", description)
        return True
    except (ElementClickInterceptedException, WebDriverException) as e:
        logger.debug("Normal click failed for %s: %s", description, str(e)[:100])

    # Strategy 2: JavaScript click
    try:
        driver.execute_script("arguments[0].click();", element)
        logger.info("Clicked %s via JavaScript click", description)
        return True
    except WebDriverException as e:
        logger.debug("JS click failed for %s: %s", description, str(e)[:100])

    # Strategy 3: ActionChains click
    try:
        ActionChains(driver).move_to_element(element).click().perform()
        logger.info("Clicked %s via ActionChains click", description)
        return True
    except WebDriverException as e:
        logger.debug("ActionChains click failed for %s: %s", description, str(e)[:100])

    logger.warning("All click methods failed for %s", description)
    return False


def safe_wait(driver, condition, timeout, description="condition"):
    """
    Wait for a condition using ExplicitWait, returning None on timeout.

    Unlike WebDriverWait(...).until(), this does NOT raise on timeout.

    Args:
        driver: Selenium WebDriver instance.
        condition: An expected_conditions callable.
        timeout: Maximum seconds to wait.
        description: Human-readable name for logging.

    Returns:
        The result of the condition if met, None on timeout.
    """
    logger = get_logger()
    try:
        result = WebDriverWait(driver, timeout).until(condition)
        return result
    except TimeoutException:
        logger.debug("Timed out waiting for %s (%ds)", description, timeout)
        return None


def safe_find_elements(driver, by, value, description="elements"):
    """
    Safely find elements, returning an empty list on failure.

    Args:
        driver: Selenium WebDriver instance.
        by: Locator strategy (By.CSS_SELECTOR, etc).
        value: Locator value.
        description: Human-readable name for logging.

    Returns:
        List of WebElements, or empty list on failure.
    """
    logger = get_logger()
    try:
        elements = driver.find_elements(by, value)
        logger.debug("Found %d %s", len(elements), description)
        return elements
    except WebDriverException as e:
        logger.warning("Failed to find %s: %s", description, str(e)[:100])
        return []


def scroll_into_view(driver, element):
    """Scroll an element into the viewport."""
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            element
        )
    except WebDriverException:
        pass


def is_element_visible(element):
    """Check if an element is displayed and has non-zero size."""
    try:
        return element.is_displayed() and element.size.get("height", 0) > 0
    except (StaleElementReferenceException, WebDriverException):
        return False
