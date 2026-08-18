"""The site's horizontal coordinate frame.

Poggio Civitate runs a **local site grid**: a 10 m grid, independent of GPS,
WGS84 and UTM, oriented to an artificial **Grid North**. Everything the
application computes lives in that frame. This module is the one place that
knows how to read a grid label, and the one place that names the frame.

Three rules, stated identically across *Master Grid Origins, Application, and
Seasonal Procedures*, *Conservation Kobo Form Instructions* and the *2025 Kobo
Deployment* data-entry guide:

  * Grid X is the E/W value and is recorded first.
  * Grid Y is the N/S value and is recorded second.
  * North and East are positive; **South and West are negative**.
    ``170.56E/64.26S`` is ``Grid X = 170.56, Grid Y = -64.26``.

That third rule is the whole reason this module is small and heavily tested.
A sign error there mirrors the entire site north-to-south, and nothing
downstream can detect it: every distance, every slope and every model stays
internally consistent while being reflected. It is isolated in
``label_to_grid`` so it has exactly one place to go wrong.

**There are two local grids**, the hill of Poggio Civitate and Vescovado di
Murlo, so a bare pair of numbers is not a location. Callers name the grid.
The two origins are about 1.5 million metres apart once projected, so mixing
them is never a near miss a tolerance could absorb.

Model coordinates **are** grid coordinates: ``grid_to_site`` is the identity
function, and exists so the assumption has a name and a docstring rather than
being implicit at four call sites.
"""

from __future__ import annotations

import math
import re

POGGIO_CIVITATE = "poggio-civitate"
VESCOVADO_DI_MURLO = "vescovado-di-murlo"
GRIDS = (POGGIO_CIVITATE, VESCOVADO_DI_MURLO)

GRID_NAMES = {
    POGGIO_CIVITATE: "Poggio Civitate (the hill)",
    VESCOVADO_DI_MURLO: "Vescovado di Murlo",
}

# Local grid -> Monte Mario 1 (EPSG:3003), as published in the 2025 Kobo
# Deployment guide and attributed there to Taylor Oshan. Applied exactly as
# given: the linear part is very slightly anisotropic, so re-deriving it as a
# rotation and scale would not reproduce these numbers.
#
#   proj_x = x*a + y*b + c
#   proj_y = x*d + y*e + f
_EPSG3003 = {
    POGGIO_CIVITATE: (
        0.99221693,
        0.0447248683,
        169513.520,
        -0.043247185,
        0.999281902,
        478065.144,
    ),
    VESCOVADO_DI_MURLO: (
        0.87120992587,
        0.486029300286,
        1694396.08449,
        -0.487297729938,
        0.873675651295,
        4782618.57257,
    ),
}

# "190E/53S", "190E / 53S", "190.5E/53.25S". The separator is optional so a
# label transcribed without one still reads.
_LABEL = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*([EWew])\s*[/,]?\s*(\d+(?:\.\d+)?)\s*([NSns])\s*$"
)


class GridError(ValueError):
    """A grid label or grid name that cannot be read, with a reason."""


def normalize_grid_name(value):
    """A declared grid name in canonical form, or '' if absent.

    Accepts the spellings that appear in the project's own documents and URLs
    ("poggio-civitate", "Poggio Civitate"). Raises for a name that looks like a
    grid but is not one of the two, because silently accepting it would let a
    coordinate claim a frame that has no transform.
    """
    if value is None:
        return ""
    if not isinstance(value, str) or not value.strip():
        return ""
    slug = re.sub(r"[\s_]+", "-", value.strip().lower())
    if slug in GRIDS:
        return slug
    raise GridError(
        f"{value!r} is not a Poggio Civitate site grid. Expected one of "
        + ", ".join(repr(name) for name in GRIDS)
    )


def label_to_grid(text):
    """``"190E/53S"`` -> ``(190.0, -53.0)``.

    South and West become negative, per the site's cardinal-inversion rule.
    Raises GridError rather than guessing at anything it cannot read: a label
    is survey data transcribed off a drawing, and a misread one places
    everything built from it somewhere else.
    """
    if not isinstance(text, str) or not text.strip():
        raise GridError("grid label is empty")
    match = _LABEL.match(text)
    if not match:
        raise GridError(
            f"{text.strip()!r} is not a grid label. Expected an easting then a "
            "northing with cardinal letters, like '190E/53S'"
        )
    easting, ew, northing, ns = match.groups()
    x = float(easting) * (1 if ew.upper() == "E" else -1)
    y = float(northing) * (1 if ns.upper() == "N" else -1)
    return x, y


def format_label(grid_x, grid_y, places=2):
    """``(190.0, -53.0)`` -> ``"190E/53S"``. The inverse of label_to_grid.

    For display and for round-tripping a transcription back to the operator,
    never for storage: stored coordinates keep the signed numbers, because that
    is the form the site's own database uses.
    """

    def part(value, positive, negative):
        text = f"{abs(value):.{places}f}".rstrip("0").rstrip(".")
        return f"{text or '0'}{positive if value >= 0 else negative}"

    return f"{part(grid_x, 'E', 'W')}/{part(grid_y, 'N', 'S')}"


def grid_to_site(grid_x, grid_y):
    """Grid coordinates to model coordinates: the identity.

    Model X is grid easting and model Y is grid northing, both in metres. This
    is not a simplification made here: ``convert_coords.convert`` already
    computes ``X = originX + x·sin(bearing)``, ``Y = originY + x·cos(bearing)``
    with bearing clockwise from north, which is the same frame the total
    station uses (HA 0° Grid North, 90° East, 180° South, 270° West).

    The function exists so that the assumption is written down once and can be
    changed in one place if a site ever needs an offset.
    """
    return float(grid_x), float(grid_y)


def to_epsg3003(grid_x, grid_y, grid):
    """Local grid to Monte Mario 1 / EPSG:3003, for export only.

    The application models in local grid metres; this is for handing a result
    to something that expects real-world coordinates. Offline: the affine is
    published, so no network call is involved.
    """
    name = normalize_grid_name(grid)
    if not name:
        raise GridError(
            "a site grid must be named before coordinates can be projected; "
            "the two local grids have different origins"
        )
    a, b, c, d, e, f = _EPSG3003[name]
    x, y = float(grid_x), float(grid_y)
    return a * x + b * y + c, d * x + e * y + f


def grid_north_offset_degrees(grid):
    """How far Grid North sits from projected north, in degrees.

    Derived from the published affine rather than stated anywhere: about 2.5°
    for Poggio Civitate. Reported so that "Grid North is an artificial
    reference direction" carries a number, and so a bearing taken with a
    magnetic compass can be recognised as wrong by more than rounding.
    """
    name = normalize_grid_name(grid)
    if not name:
        raise GridError("a site grid must be named")
    a, b, _, d, _e, _f = _EPSG3003[name]
    return math.degrees(math.atan2(b, a)), math.degrees(math.atan2(-d, a))


def project_model_footprint(extent, grid):
    """A model's extent projected into EPSG:3003, for handing to a GIS.

    ``extent`` is the six-value box the viewer manifest carries. Returns the
    four corners of its horizontal footprint, in order, plus the Z range
    unchanged -- elevation is already absolute metres and the projection is
    horizontal only.

    Stops at EPSG:3003 deliberately. Going on to EPSG:4326 needs a full
    projection library this application does not depend on, or Open Context's
    reprojection endpoint -- which would mean sending coordinates off the
    machine, and the promise here is that they stay on it. A GIS can take
    Monte Mario 1 directly.
    """
    if len(extent) != 6:
        raise GridError("a model extent needs six values")
    xlo, xhi, ylo, yhi, zlo, zhi = (float(value) for value in extent)
    corners = [(xlo, ylo), (xhi, ylo), (xhi, yhi), (xlo, yhi)]
    return {
        "crs": "EPSG:3003",
        "crs_name": "Monte Mario 1 / Italy zone 1",
        "site_grid": normalize_grid_name(grid),
        "corners": [list(to_epsg3003(x, y, grid)) for x, y in corners],
        "z_range": [zlo, zhi],
        "z_frame": "mAE",
    }
