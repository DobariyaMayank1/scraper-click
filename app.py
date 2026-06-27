"""
Flask application entry point.

Initializes the Flask app, registers blueprints, creates
the shared worker instance, and serves the dashboard.
"""

from flask import Flask, render_template

from config import Config
from automation.logger import setup_logger
from automation.worker import AutomationWorker
from routes.api import api, init_worker


def create_app():
    """Application factory."""
    app = Flask(__name__)

    # Initialize logging before anything else
    logger = setup_logger()
    logger.info("Application Started")

    # Create the shared worker instance
    worker = AutomationWorker()
    init_worker(worker)

    # Register API blueprint
    app.register_blueprint(api)

    # Dashboard route
    @app.route("/")
    def dashboard():
        return render_template("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
