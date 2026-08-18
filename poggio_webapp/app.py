"""Trench Digitization Pipeline backend entry point.

Every route lives in a blueprint under backend/routes/ and is registered by
backend.create_app(). Nothing should be added directly to the app object here.
If you are about to, it belongs in a blueprint.
"""

import os

from backend import create_app

app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(
        debug=debug,
        port=int(os.environ.get("PORT", 5000)),
    )
