"""The browser's copy of the drawn-feature vocabulary must match Python's.

The browser cannot import ``pipeline/site_vocab.py``, so the list is duplicated
in ``static/shared/site-vocab.mjs``. Duplicated vocabularies drift, and a drift
here means a recorder picks a term the backend has never heard of. This test is
the thing that stops that happening quietly.
"""

import json
import re

from pipeline.site_vocab import DRAWN_FEATURE_TYPES, feature_type

MODULE = "static/shared/site-vocab.mjs"
_ENTRY = re.compile(r'\{\s*key:\s*"([^"]+)",\s*label:\s*"([^"]+)"\s*\}')
_DEFAULT = re.compile(r'DEFAULT_FEATURE_TYPE\s*=\s*"([^"]+)"')


def _browser_vocabulary(webapp_root):
    source = (webapp_root / MODULE).read_text()
    body = source.split("DRAWN_FEATURE_TYPES", 1)[1].split("];", 1)[0]
    return _ENTRY.findall(body)


def test_the_browser_list_matches_python_exactly(webapp_root):
    expected = [(entry["key"], entry["label"]) for entry in DRAWN_FEATURE_TYPES]
    assert _browser_vocabulary(webapp_root) == expected, (
        "static/shared/site-vocab.mjs has drifted from "
        "pipeline/site_vocab.py; the Python module is the source"
    )


def test_the_browser_default_is_a_key_python_knows(webapp_root):
    source = (webapp_root / MODULE).read_text()
    default = _DEFAULT.search(source).group(1)
    assert feature_type(default) is not None


def test_no_stage_module_still_carries_its_own_feature_list(webapp_root):
    """Regression: draw.js and features.js each held a private
    ["rock/stone", "cut", "lens", "void", "other feature"] -- invented for this
    application, matching nothing the site records."""
    for name in ("app/stages/draw.js", "app/stages/features.js"):
        source = (webapp_root / "static" / name).read_text()
        assert "rock/stone" not in source, name
        assert "const FEATURE_TYPES" not in source, name
        assert "site-vocab.mjs" in source, name


def test_material_features_are_serializable_for_the_frontend():
    """The richer Python entries carry material and survey codes the browser
    does not need; they must still be plain JSON-safe data."""
    json.dumps(DRAWN_FEATURE_TYPES)
