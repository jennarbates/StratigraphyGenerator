"""Flask application factory."""

from flask import Flask

from .config import STATIC_DIR, TEMPLATES_DIR
from .routes import register_blueprints


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(STATIC_DIR),
        template_folder=str(TEMPLATES_DIR),
    )

    register_blueprints(app)
    return app
