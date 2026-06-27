"""
Flask API routes for the automation dashboard.

Endpoints:
    POST /api/start   — Start the automation worker
    POST /api/stop    — Stop the automation worker
    GET  /api/status  — Get current status + live logs
"""

from flask import Blueprint, jsonify

from automation.logger import get_log_capture

api = Blueprint("api", __name__)

# The worker instance is set by app.py during initialization
_worker = None


def init_worker(worker):
    """Register the shared worker instance. Called once from app.py."""
    global _worker
    _worker = worker


@api.route("/api/start", methods=["POST"])
def start_automation():
    """Start the automation worker."""
    if _worker is None:
        return jsonify({"error": "Worker not initialized"}), 500

    started = _worker.start()

    if started:
        return jsonify({"message": "Automation started"}), 200
    else:
        return jsonify({"message": "Automation already running"}), 200


@api.route("/api/stop", methods=["POST"])
def stop_automation():
    """Stop the automation worker and close browser."""
    if _worker is None:
        return jsonify({"error": "Worker not initialized"}), 500

    stopped = _worker.stop()

    if stopped:
        return jsonify({"message": "Automation stopped"}), 200
    else:
        return jsonify({"message": "Automation was not running"}), 200


@api.route("/api/status", methods=["GET"])
def get_status():
    """
    Return current automation status and recent logs.

    Response JSON:
    {
        "running": bool,
        "state": str,
        "cycle_count": int,
        "current_url": str,
        "browser_alive": bool,
        "logs": [str, ...]
    }
    """
    if _worker is None:
        return jsonify({"error": "Worker not initialized"}), 500

    status = _worker.status
    status["logs"] = get_log_capture().get_logs()

    return jsonify(status), 200
