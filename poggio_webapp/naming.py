"""Turning user-supplied labels into safe names.

A leaf module, for the same reason ``storage`` is one: ``pipeline.build_gempy``
and ``backend.routes.trenches`` both need the filesystem slug, and
``routes/trenches.py`` previously kept its own copy specifically so that it
would not have to import the optional gempy stack to get it. Putting the rule
in a dependency-free module removes the reason for the copy.

The functions here encode genuinely different rules and are not
interchangeable:

  * ``safe_filename`` produces a name safe to use as a path component.
  * ``clean_label`` tidies a label for display and storage; the result is not
    path-safe and must not be used as one.
  * ``canonical_trench`` and ``canonical_locus`` put an identifier into the
    form the site's own data-entry standard requires, so that two spellings of
    one trench are one trench.
"""

import re

_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")

# "T104", "T-104", "t 104", "CA 100" -> letters + digits, no separator.
# Property abbreviations are short (T, CA); four characters is generous.
_TRENCH_SHAPE = re.compile(r"^([A-Za-z]{1,4})[\s._-]*(\d+)$")

# "5", "Locus 5", "locus5" -> "5".
_LOCUS_SHAPE = re.compile(r"^(?:locus\s*)?(\d+)$", re.IGNORECASE)


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
    the escaped directory. Names like ``"T104.2"`` are unaffected, because only a
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


def canonical_trench(value) -> str:
    """A trench label in the site's required form: ``T104``, never ``T-104``.

    *Conservation Kobo Form Instructions* requires the property designation
    abbreviation followed by the number "without spacing", and names ``T-62``
    and ``T 62`` as incorrect. That rule is not cosmetic here:
    ``trench_builder.grouped_members`` groups jobs by this exact string, so two
    spellings build two trenches, each holding a subset of the walls, each
    producing a confident model of half a pit. Both spellings are already in
    circulation on the same material -- the T104 field drawings are titled
    "T-104" while the Open Context records read "T104".

    Only a label that actually looks like an identifier is rewritten. Anything
    else comes back merely stripped, because a label this function does not
    recognise is more likely to be something it should not be mangling than a
    misspelt trench.

    Digits are preserved exactly. ``T007`` does not become ``T7``: no trench at
    this site is written with a leading zero, so collapsing them would only
    ever change a label nobody meant to write that way.
    """
    label = clean_label(value)
    match = _TRENCH_SHAPE.match(label)
    if not match:
        return label
    letters, digits = match.groups()
    return f"{letters.upper()}{digits}"


def canonical_locus(value) -> str:
    """A locus number in the site's required form: ``5``, never ``" 5 "``.

    The same source requires the bare number, and warns that devices insert
    spacing into form fields. A recorder typing "Locus 5" is spelling the same
    thing, so that form is accepted too.

    Digits are preserved exactly, for the reason given in ``canonical_trench``.
    Accepts an int as well as a string: locus numbers arrive from JSON both
    ways.
    """
    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    match = _LOCUS_SHAPE.match(clean_label(value))
    if not match:
        return clean_label(value)
    return match.group(1)
