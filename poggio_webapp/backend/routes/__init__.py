"""Register all backend blueprints."""

from flask import Flask

from .pages import bp as pages_bp
from .jobs import bp as jobs_bp
from .scans import bp as scans_bp
from .preprocess import bp as preprocess_bp
from .extraction import bp as extraction_bp
from .markers import bp as markers_bp
from .task_status import bp as task_status_bp
from .processing import bp as processing_bp
from .gempy import bp as gempy_bp


BLUEPRINTS = (
    pages_bp,
    jobs_bp,
    scans_bp,
    preprocess_bp,
    extraction_bp,
    markers_bp,
    task_status_bp,
    processing_bp,
    gempy_bp,
)


def register_blueprints(app: Flask) -> None:
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
