"""
Background worker thread for running the automation loop.

The worker runs AutomationController.run_cycle() in a daemon thread
and can be started/stopped from the Flask API. Only ONE worker
instance is allowed at a time.
"""

import threading

from automation.logger import get_logger
from automation.browser import BrowserManager
from automation.controller import AutomationController
from automation.state_machine import AutomationState


class AutomationWorker:
    """
    Manages a background thread that runs the automation cycle loop.

    Usage:
        worker = AutomationWorker()
        worker.start()   # Launches background thread
        worker.stop()    # Gracefully stops thread + browser

    Thread safety: All public methods are safe to call from Flask routes.
    """

    def __init__(self):
        self._logger = get_logger()
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Shared components
        self._browser = BrowserManager()
        self._controller = AutomationController(self._browser)

    @property
    def is_running(self):
        """True if the worker thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def status(self):
        """
        Return a dict describing the current worker state.
        Used by the dashboard API.
        """
        return {
            "running": self.is_running,
            "state": self._controller.state,
            "cycle_count": self._controller.cycle_count,
            "current_url": self._browser.current_url,
            "browser_alive": self._browser.is_alive,
        }

    def start(self):
        """
        Start the automation worker thread.

        If already running, the request is silently ignored.
        """
        with self._lock:
            if self.is_running:
                self._logger.info("Worker already running — ignoring start request")
                return False

            self._logger.info("Worker Started")
            self._stop_event.clear()
            self._controller.reset()

            self._thread = threading.Thread(
                target=self._run_loop,
                name="AutomationWorker",
                daemon=True
            )
            self._thread.start()
            return True

    def stop(self):
        """
        Stop the worker thread and close the browser.

        Blocks until the thread exits (with timeout).
        """
        with self._lock:
            if not self.is_running:
                self._logger.info("Worker not running — nothing to stop")
                return False

            self._logger.info("Stopping Worker")
            self._stop_event.set()

        # Wait for thread to finish (outside the lock)
        if self._thread is not None:
            self._thread.join(timeout=15)

        # Cleanup browser
        try:
            self._browser.stop()
        except Exception as e:
            self._logger.warning("Browser cleanup error: %s", str(e)[:150])

        self._logger.info("Worker Stopped")
        return True

    def _run_loop(self):
        """
        Main loop — runs cycles until stop is requested.
        This runs inside the background thread.
        """
        self._logger.info("Automation loop started")

        try:
            while not self._stop_event.is_set():
                try:
                    self._controller.run_cycle(self._stop_event)
                except Exception as e:
                    self._logger.error(
                        "Unexpected error in cycle: %s", str(e)[:200]
                    )
                    # Wait before retrying to avoid tight error loops
                    self._stop_event.wait(timeout=5)

        finally:
            self._logger.info("Automation loop ended")
