"""
Centralized configuration for the automation framework.

All tunables live here. No magic numbers should exist in other modules.
To change the source website, update SOURCE_URL and swap the page object.
"""


class Config:
    """Application-wide configuration."""

    # --- Source Website ---
    SOURCE_URL = "https://textutils-3i6y.onrender.com/"

    # --- Browser Settings ---
    BROWSER_HEADLESS = True          # Visible mode for Milestone 1
    BROWSER_START_MAXIMIZED = True
    PAGE_LOAD_TIMEOUT = 30            # Seconds to wait for page loads
    IMPLICIT_WAIT = 0                 # We use ExplicitWait, keep this at 0

    # --- Timeouts (seconds) ---
    POPUP_WAIT_TIMEOUT = 5            # How long to wait for popup to appear
    AD_WAIT_TIMEOUT = 10              # How long to wait for ads to become clickable
    DESTINATION_WAIT_TIMEOUT = 15     # How long to wait for destination page load
    DESTINATION_STAY_DURATION = 3     # How long to stay on destination page
    SOURCE_RELOAD_TIMEOUT = 15        # How long to wait for source page to reload
    CYCLE_DELAY = 2                   # Seconds between cycles

    # --- Retry Settings ---
    MAX_AD_RETRIES = 3                # Number of ad-click retries per cycle
    MAX_POPUP_RETRIES = 2             # Number of popup-close retries

    # --- Logging ---
    LOG_DIR = "logs"
    LOG_FILE = "automation.log"
    LOG_MAX_BYTES = 5 * 1024 * 1024   # 5 MB per log file
    LOG_BACKUP_COUNT = 3              # Number of rotated log files to keep
    LOG_TAIL_LINES = 100              # Lines to show in dashboard

    # --- Flask ---
    FLASK_HOST = "0.0.0.0"
    FLASK_PORT = 5000
    FLASK_DEBUG = False               # Debug mode breaks threading
