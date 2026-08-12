"""A trench's surveyed layout, and the grid config derived from it.

Every trenchbook opens with a **Trench Layout** section, and *Excavation and
Documentation Procedures* says what goes in it:

    Opening trench dimensions, in meters. Opening coordinates of the four
    corners of your trench. How your trench was sited on the master grid ...
    The location and elevation of your datum nail.

That is, almost exactly, the grid config this application asks an operator to
type by hand -- and the roadmap's top item is that the typed version is usually
still placeholders. The corner coordinates already exist: staked by total
station, written on surveyor's tape on the corner nails, and logged in the
master Geospatial Spreadsheet under the opening-coordinates column.

So this module goes the other way round. Give it the corners and the wall names
and it derives each face's registration -- origin, bearing, surface elevation --
from survey data rather than asking anyone to work out a bearing.

Two things it will not do:

**It will not invent an elevation.** Opening elevations are taken "for at least
all corners of your trench", so a layout that has corners but no elevations is
incomplete rather than defaultable, and produces a config with `surfaceZ: null`
that the build refuses.

**It will not accept corners that do not describe a trench.** Corners are the
distinct vertices in order around the pit, and the last wall closes back to the
first corner. Two labels transposed produce a self-crossing shape -- still a
valid polygon, but one whose derived bearings would send two walls diagonally
across the trench -- so that is refused rather than registered.
"""

from __future__ import annotations

import math

from . import site_elevation, site_grid

# No trench at this site is anywhere near this long, so a side beyond it means
# a corner label was mistyped rather than a genuinely large unit.
_IMPLAUSIBLE_WALL_M = 50.0


class LayoutError(ValueError):
    """A layout that cannot be read. The message is user-facing."""


def bearing_degrees(start, end):
    """Grid bearing of start -> end, in degrees clockwise from Grid North.

    Matches ``convert_coords.convert`` exactly, which computes
    ``X = X0 + x*sin(bearing)``, ``Y = Y0 + x*cos(bearing)``: a direction is
    ``(sin, cos)`` of the bearing, so the bearing is ``atan2(east, north)``.
    That is also the total station's convention -- HA 0 Grid North, 90 East.
    """
    east = end[0] - start[0]
    north = end[1] - start[1]
    if math.isclose(east, 0.0, abs_tol=1e-12) and math.isclose(
        north, 0.0, abs_tol=1e-12
    ):
        raise LayoutError(
            "two consecutive corners are in the same place, so the wall "
            "between them has no direction"
        )
    return math.degrees(math.atan2(east, north)) % 360.0


def _segments_cross(a, b, c, d):
    """True when segment a-b properly crosses segment c-d.

    Shared endpoints do not count: consecutive walls of a trench meet at a
    corner by design.
    """

    def side(p, q, r):
        value = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        if abs(value) < 1e-12:
            return 0
        return 1 if value > 0 else -1

    if len({a, b, c, d}) < 4:
        return False
    return side(a, b, c) != side(a, b, d) and side(c, d, a) != side(c, d, b)


def _self_intersects(points):
    """True when the closed ring through these corners crosses itself.

    This is the check that catches the realistic mistake. Two corner labels
    transposed produce a bow-tie, which is geometrically a perfectly good
    polygon but not a trench, and the derived bearings would send two walls
    diagonally across the pit.
    """
    count = len(points)
    edges = [(points[i], points[(i + 1) % count]) for i in range(count)]
    for i in range(count):
        for j in range(i + 1, count):
            if _segments_cross(*edges[i], *edges[j]):
                return True
    return False


def _corner(entry, index):
    """One corner as (label, grid_x, grid_y, elevation or None)."""
    if not isinstance(entry, dict):
        raise LayoutError(f"corner {index + 1} is not an object")

    label = entry.get("label")
    if label:
        try:
            grid_x, grid_y = site_grid.label_to_grid(label)
        except site_grid.GridError as error:
            raise LayoutError(f"corner {index + 1}: {error}") from error
    else:
        grid_x, grid_y = entry.get("gridX"), entry.get("gridY")
        if not all(
            isinstance(v, (int, float)) and not isinstance(v, bool)
            for v in (grid_x, grid_y)
        ):
            raise LayoutError(
                f"corner {index + 1} needs either a grid label like "
                "'190E/53S' or numeric gridX and gridY"
            )
        grid_x, grid_y = float(grid_x), float(grid_y)

    return label, grid_x, grid_y, entry.get("elevation")


def _elevation(value, vertical, index):
    if value is None:
        return None
    try:
        return site_elevation.resolve(
            value, vertical, what=f"corner {index + 1} elevation"
        )
    except site_elevation.ElevationError as error:
        raise LayoutError(str(error)) from error


def _describe(corner):
    """A corner for a note: its own label where it has one, else the grid
    notation for its coordinates, so a note always reads like the drawing."""
    if corner.get("label"):
        return corner["label"]
    return site_grid.format_label(corner["gridX"], corner["gridY"])


def read_layout(layout):
    """Validate a layout and return its corners, walls and closure state.

    Returns a dict with ``corners`` (label, gridX, gridY, elevation),
    ``walls``, ``closed``, ``closure_gap_m`` and ``notes``.
    """
    if not isinstance(layout, dict):
        raise LayoutError("trench layout must be an object")

    raw_corners = layout.get("corners")
    if not isinstance(raw_corners, list) or len(raw_corners) < 3:
        raise LayoutError(
            "a trench layout needs at least three corners; the procedures ask "
            "for the opening coordinates of all four"
        )

    vertical = layout.get("vertical")
    notes = []
    corners = []
    for index, entry in enumerate(raw_corners):
        label, grid_x, grid_y, raw_elevation = _corner(entry, index)
        corners.append(
            {
                "label": label,
                "gridX": grid_x,
                "gridY": grid_y,
                "elevation": _elevation(raw_elevation, vertical, index),
            }
        )

    positions = [(c["gridX"], c["gridY"]) for c in corners]
    if len(set(positions)) != len(positions):
        raise LayoutError(
            "two corners of this trench have the same coordinates; check the "
            "labels against the corner nails"
        )

    if _self_intersects(positions):
        raise LayoutError(
            "these corners describe a self-crossing shape, not a trench. Two "
            "of them are almost certainly listed out of order -- corners go "
            "around the trench, each one adjacent to the next"
        )

    walls = layout.get("walls")
    if not isinstance(walls, list) or len(walls) != len(corners):
        raise LayoutError(
            f"this layout needs {len(corners)} wall name(s), one per edge "
            f"between consecutive corners, with the last wall closing back to "
            f"the first corner"
        )
    cleaned_walls = [str(name).strip() for name in walls]
    if not all(cleaned_walls):
        raise LayoutError("every wall in a trench layout needs a name")
    if len(set(name.lower() for name in cleaned_walls)) != len(cleaned_walls):
        raise LayoutError(
            "two walls of this trench share a name; each face needs its own"
        )

    missing_elevations = [
        corner["label"] or f"corner {i + 1}"
        for i, corner in enumerate(corners)
        if corner["elevation"] is None
    ]
    if missing_elevations:
        notes.append(
            "no opening elevation recorded for "
            + ", ".join(str(name) for name in missing_elevations)
            + ". The procedures ask for one at every corner; without them the "
            "affected faces have no surfaceZ and the build will refuse"
        )

    sides = [
        math.dist(positions[index], positions[(index + 1) % len(positions)])
        for index in range(len(positions))
    ]
    for name, length in zip(cleaned_walls, sides):
        if length > _IMPLAUSIBLE_WALL_M:
            notes.append(
                f"wall {name!r} is {length:.1f} m long, which is longer than "
                "any trench at this site. Check its two corner labels"
            )

    return {
        "corners": corners,
        "walls": cleaned_walls,
        "side_lengths_m": [round(length, 4) for length in sides],
        "notes": notes,
    }


def build_grid_config(layout):
    """A grid config derived from a surveyed layout. Returns (config, notes).

    Each wall is the edge from one corner to the next: its origin is the start
    corner, its bearing is the direction to the end corner, and its surfaceZ is
    the opening elevation measured at the start corner.

    The result declares ``source: "surveyed"`` -- these are real coordinates,
    not the starter pattern -- so the placeholder refusal lets it through.
    """
    read = read_layout(layout)
    notes = list(read["notes"])
    corners = read["corners"]
    walls = read["walls"]

    try:
        grid_name = site_grid.normalize_grid_name(layout.get("site_grid"))
    except site_grid.GridError as error:
        raise LayoutError(str(error)) from error
    if not grid_name:
        notes.append(
            "this layout names no site grid. Poggio Civitate runs two, so "
            "record which one these coordinates belong to"
        )

    faces = {}
    for index, name in enumerate(walls):
        start = corners[index]
        end = corners[(index + 1) % len(corners)]
        start_point = (start["gridX"], start["gridY"])
        end_point = (end["gridX"], end["gridY"])
        faces[name] = {
            "originX": round(start["gridX"], 4),
            "originY": round(start["gridY"], 4),
            "surfaceZ": start["elevation"],
            "bearing_deg": round(bearing_degrees(start_point, end_point), 4),
        }
        length = math.dist(start_point, end_point)
        notes.append(
            f"wall {name!r}: {length:.2f} m from "
            f"{_describe(start)} to {_describe(end)}, "
            f"bearing {faces[name]['bearing_deg']:g} degrees from Grid North"
        )

    config = {
        "_comment": (
            "Derived from this trench's surveyed layout: each wall's origin is "
            "a corner nail, its bearing is the direction to the next corner in "
            "degrees clockwise from Grid North, and its surfaceZ is the opening "
            "elevation measured at that corner. Check the wall lengths in the "
            "notes against the drawings before building."
        ),
        "site_grid": grid_name or None,
        "source": "surveyed",
        "vertical": layout.get("vertical")
        or {
            "frame": site_elevation.MAE,
            "entryForm": "absolute",
            "datumNail": {"absoluteZ": None, "label": None},
        },
        "faces": faces,
    }
    return config, notes
