"""Register all backend blueprints."""

from flask import Flask

from .demo import bp as demo_bp
from .editor import bp as editor_bp
from .extraction import bp as extraction_bp
from .features import bp as features_bp
from .finds import bp as finds_bp
from .gempy import bp as gempy_bp
from .harris import bp as harris_bp
from .jobs import bp as jobs_bp
from .manual import bp as manual_bp
from .markers import bp as markers_bp
from .pages import bp as pages_bp
from .preprocess import bp as preprocess_bp
from .processing import bp as processing_bp
from .scans import bp as scans_bp
from .task_status import bp as task_status_bp
from .text_metadata import bp as text_metadata_bp
from .trenches import bp as trenches_bp

BLUEPRINTS = (
    pages_bp,
    jobs_bp,
    editor_bp,
    finds_bp,
    scans_bp,
    preprocess_bp,
    extraction_bp,
    features_bp,
    markers_bp,
    manual_bp,
    task_status_bp,
    text_metadata_bp,
    processing_bp,
    gempy_bp,
    harris_bp,
    trenches_bp,
    demo_bp,
)


def register_blueprints(app: Flask) -> None:
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
