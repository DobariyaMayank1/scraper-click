"""
Structured logging for the automation framework.

Provides a single named logger ('automation') used across all modules.
Outputs to both console and a rotating log file under logs/.
"""

import os
import logging
from collections import deque

from config import Config


class LogCapture(logging.Handler):
    """
    In-memory log handler that keeps the last N log records.
    Used by the dashboard to serve live logs without reading disk.
    """

    def __init__(self, max_lines=Config.LOG_TAIL_LINES):
        super().__init__()
        self._buffer = deque(maxlen=max_lines)

    def emit(self, record):
        try:
            message = self.format(record)
            self._buffer.append(message)
        except Exception:
            self.handleError(record)

    def get_logs(self):
        """Return captured log lines as a list."""
        return list(self._buffer)

    def clear(self):
        """Clear the in-memory buffer."""
        self._buffer.clear()


# Module-level singleton instances
_log_capture = LogCapture()
_logger = None


def setup_logger():
    """
    Initialize the 'automation' logger with console + file + capture handlers.
    Clears old logs on every startup so each session is clean.
    Safe to call multiple times — only configures once.
    """
    global _logger

    if _logger is not None:
        return _logger

    # Create logs directory
    os.makedirs(Config.LOG_DIR, exist_ok=True)

    # Delete old log file so each restart is completely clean
    file_path = os.path.join(Config.LOG_DIR, Config.LOG_FILE)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    # Clear in-memory buffer from any previous session
    _log_capture.clear()

    logger = logging.getLogger("automation")
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers to prevent duplicates
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler — INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # File handler — mode='w' overwrites on each startup
    file_handler = logging.FileHandler(
        file_path,
        mode="w",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # In-memory capture handler — INFO and above (for dashboard)
    _log_capture.setLevel(logging.INFO)
    _log_capture.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(_log_capture)

    _logger = logger
    return _logger


def get_logger():
    """Get the automation logger. Initializes on first call."""
    if _logger is None:
        return setup_logger()
    return _logger


def get_log_capture():
    """Get the in-memory log capture handler."""
    return _log_capture
