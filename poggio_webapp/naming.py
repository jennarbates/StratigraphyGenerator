"""Turning user-supplied labels into safe names.

A leaf module, for the same reason ``storage`` is one: ``pipeline.build_gempy``
and ``backend.routes.trenches`` both need the filesystem slug, and
``routes/trenches.py`` previously kept its own copy specifically so that it
would not have to import the optional gempy stack to get it. Putting the rule
in a dependency-free module removes the reason for the copy.

The two functions here encode genuinely different rules and are not
interchangeable:

  * ``safe_filename`` produces a name safe to use as a path component.
  * ``clean_label`` tidies a label for display and storage; the result is not
    path-safe and must not be used as one.
"""

import re

_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_filename(name, fallback="untitled"):
    """A filesystem-safe path component built from an arbitrary label.

    Runs of unsafe characters collapse to a single underscore; leading and
    trailing underscores are trimmed. A label that reduces to nothing, or to a
    relative path component, becomes ``fallback``.

    The dot case is not hypothetical. Dot is a legal filename character, so the
    substitution above passes ``".."`` through untouched, and the callers join
    the result onto a storage root. A trench labelled ``".."`` resolved one
    level up and made every file under poggio_webapp/ readable through
    /api/trenches/<label>/file, whose containment check then compared against
    the escaped directory. Names like ``"T104.2"`` are unaffected — only a
    component that is *nothing but* dots is rejected.
    """
    cleaned = _UNSAFE.sub("_", str(name)).strip("_")
    if not cleaned or set(cleaned) <= {"."}:
        return fallback
    return cleaned


def clean_label(value) -> str:
    """Strip a trench/wall label; non-strings and blanks become ''."""
    if not isinstance(value, str):
        return ""
    return value.strip()
