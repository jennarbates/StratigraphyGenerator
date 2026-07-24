"""Flask application factory for the trench digitization web app."""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .config import STATIC_DIR, TEMPLATES_DIR
from .routes import register_blueprints


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(STATIC_DIR),
        template_folder=str(TEMPLATES_DIR),
        static_url_path="/static",
    )
    register_blueprints(app)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return jsonify({
            "error": error.description or error.name,
            "status": error.code,
        }), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Unhandled application error")
        return jsonify({"error": str(error) or "unexpected server error"}), 500

    return app
