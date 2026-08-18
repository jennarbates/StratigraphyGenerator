"""The site's vertical frame: absolute elevation, datum nails, uncertainty.

Where ``site_grid`` holds the horizontal frame, this holds the vertical one.

How elevation is actually recorded at Poggio Civitate, from *Excavation and
Documentation Procedures*:

  * Each trench gets a **datum nail** driven into a fixed object near it,
    levelled to the site's master height matrix.
  * Readings are taken **below datum** with a line level, at minimum at all
    four trench corners, plus more where the ground slopes.
  * The datum's own absolute elevation is "determined at a later time", so a
    trench can legitimately sit in below-datum form for a while.
  * But below-datum is transitional: "Any below datum measurements must be
    corrected/rectified with absolute elevation for your final paperwork
    (trenchbook, find tags, Kobo/Open Context entries, etc.), so it is ideal to
    work in below datum as little as possible."

The final form is **mAE** ("meters absolute elevation"), and values at this
site are in the twenties. A worked find entry in the procedures reads
``187E/56S``, ``28.73mAE``, Locus 2.

Two consequences shape this module:

**A below-datum reading without a datum height is refused, not defaulted.**
Treating a missing datum as zero produces a model that is internally
consistent, plausible-looking, and tens of metres from where the trench is:
wrong in the one way nothing downstream can detect.

**Uncertainty is recorded, not modelled.** The Kobo forms carry a ± in
centimetres per coordinate or elevation, with ranged readings stored as a
midpoint plus half the range. GemPy's build path has no per-point weighting, so
carrying that number into the solve would mean inventing a weighting the data
does not justify. It is stored and displayed instead, which is the same line
this project already draws between traced evidence and interpolation.
"""

from __future__ import annotations

import math

# "meters absolute elevation" -- the site's own abbreviation, and the frame
# every final record uses. mASL appears in the Kobo instructions only as
# another unit suffix recorders are told not to type; it is listed here so a
# record that genuinely uses it can say so rather than being mislabelled.
MAE = "mAE"
MASL = "mASL"
FRAMES = (MAE, MASL)

ENTRY_FORMS = ("absolute", "below-datum")

# A trench datum nail clears the ground and the trench never descends far, so
# a below-datum reading is a small positive number. Anything outside this is
# more likely a mis-entered absolute elevation than a real depth.
_IMPLAUSIBLE_BELOW_DATUM_M = 15.0


class ElevationError(ValueError):
    """A vertical record that cannot be resolved, with a reason."""


def normalize_frame(value):
    """A declared vertical frame in canonical form, or '' if absent."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    if not isinstance(value, str):
        raise ElevationError(f"vertical frame {value!r} is not a string")
    for frame in FRAMES:
        if value.strip().lower() == frame.lower():
            return frame
    raise ElevationError(
        f"{value!r} is not a vertical frame. Expected "
        + " or ".join(FRAMES)
        + " (mAE is 'meters absolute elevation', the form every final site "
        "record uses)"
    )


def _number(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ElevationError(f"{what} must be a number, got {value!r}")
    if not math.isfinite(value):
        raise ElevationError(f"{what} must be finite, got {value!r}")
    return float(value)


def absolute_from_below_datum(below_datum_m, datum_absolute_z):
    """Convert one below-datum reading to absolute elevation.

    ``below_datum_m`` is the measured drop from the datum nail, so it is
    subtracted. A negative reading means the point is *above* the datum, which
    happens and is allowed; the nail is meant to clear the trench corners but
    not everything around them.
    """
    drop = _number(below_datum_m, "below-datum reading")
    datum = _number(datum_absolute_z, "datum absolute elevation")
    if abs(drop) > _IMPLAUSIBLE_BELOW_DATUM_M:
        raise ElevationError(
            f"below-datum reading {drop} m is implausible for a trench "
            f"(more than {_IMPLAUSIBLE_BELOW_DATUM_M} m from the datum nail). "
            "An absolute elevation entered as a below-datum reading looks "
            "exactly like this"
        )
    return datum - drop


def datum_absolute_z(vertical):
    """The datum nail's absolute elevation from a ``vertical`` block, or None.

    None means "no datum height recorded yet", which is a legitimate state
    mid-season, not an error. It only becomes an error when a below-datum
    reading has to be resolved against it.
    """
    if not isinstance(vertical, dict):
        return None
    nail = vertical.get("datumNail")
    if not isinstance(nail, dict):
        return None
    value = nail.get("absoluteZ")
    if value is None:
        return None
    return _number(value, "datum absolute elevation")


def resolve(value, vertical, *, what="elevation"):
    """One recorded elevation as absolute elevation in the declared frame.

    ``vertical`` is the trench's vertical block: ``frame``, ``entryForm`` and
    optionally ``datumNail``. In ``absolute`` form the value passes through; in
    ``below-datum`` form it is converted, and refused if no datum height is
    recorded.
    """
    block = vertical if isinstance(vertical, dict) else {}
    form = block.get("entryForm") or "absolute"
    if form not in ENTRY_FORMS:
        raise ElevationError(
            f"entryForm {form!r} must be one of " + ", ".join(ENTRY_FORMS)
        )
    reading = _number(value, what)
    if form == "absolute":
        return reading
    datum = datum_absolute_z(block)
    if datum is None:
        raise ElevationError(
            f"{what} is recorded below datum, but this trench has no datum "
            "nail elevation. Record the datum's absolute elevation before "
            "building: a missing datum treated as zero puts the model tens of "
            "metres from the trench while looking entirely consistent"
        )
    return absolute_from_below_datum(reading, datum)


def midpoint_and_uncertainty_cm(low, high):
    """A ranged reading as ``(midpoint, ± centimetres)``.

    The arithmetic the Kobo guide spells out: an elevation range of
    27.00-27.50 mAE is entered as 27.25 with ±25 cm.
    """
    lo = _number(low, "range lower bound")
    hi = _number(high, "range upper bound")
    if hi < lo:
        lo, hi = hi, lo
    half = (hi - lo) / 2
    return lo + half, round(half * 100, 6)


def describe(vertical):
    """A short human-readable summary of a vertical block, for notes and logs.

    Says out loud when a trench is still stored below datum, because by the
    site's own rule that is unfinished paperwork rather than a settled state.
    """
    block = vertical if isinstance(vertical, dict) else {}
    frame = normalize_frame(block.get("frame")) or MAE
    form = block.get("entryForm") or "absolute"
    if form == "below-datum":
        datum = datum_absolute_z(block)
        if datum is None:
            return (
                "elevations are recorded below datum and the datum nail's own "
                "elevation is not yet known; they cannot be resolved to "
                f"{frame} until it is"
            )
        return (
            f"elevations are recorded below datum against a nail at "
            f"{datum:g} {frame}; correct them to absolute elevations for the "
            "final record"
        )
    return f"elevations are absolute, in {frame}"
