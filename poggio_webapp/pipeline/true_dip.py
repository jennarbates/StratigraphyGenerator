"""true_dip.py -- solve one true dip per surface from its traces on two walls.

`convert_coords.slope_to_orientation` gives every orientation seed the azimuth
of the wall it was measured on and the dip measured *along* that wall. On a
single wall that is all anyone can know. On a merged trench it is wrong in a
systematic way: one surface arrives carrying a seed that dips toward the north
wall's bearing and another that dips toward the east wall's, and an apparent
dip is always shallower than the true dip, so GemPy fits a compromise plane
that matches neither drawing.

Two walls that are not parallel pin the plane down exactly. Each wall's trace
gives a direction in space -- along the wall, tilted by that wall's apparent
slope -- and the plane containing both directions has one normal, hence one
true dip and one dip azimuth. This module does that solve and nothing else: it
returns orientations and human-readable notes, and wires into no pipeline.

Where a solve is not available -- a surface drawn on one wall, or two walls too
nearly parallel to condition it -- nothing is emitted and a note says so. A
plausible-looking invented orientation would be worse than the apparent dips
already in the CSV, because it would look like an improvement.
"""

import csv
import math


def _number(value):
    """A float, or None when the value cannot be one. CSV rows arrive as
    strings, dicts built in memory arrive as numbers; both are accepted."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _face_bearings(grid):
    """{face name: bearing_deg} for every face the grid registers usably."""
    bearings = {}
    for name, config in ((grid or {}).get("faces") or {}).items():
        if not isinstance(config, dict):
            continue
        bearing = _number(config.get("bearing_deg"))
        if bearing is not None:
            bearings[str(name)] = bearing
    return bearings


def _grouped(points_rows, bearings, notes):
    """{surface: {face: [(s, X, Y, Z), ...]}} with the along-wall coordinate s.

    s is the projection of the site position onto the wall's own direction,
    which differs from `convert()`'s local x by a constant offset -- harmless,
    because only the slope against s is ever used.
    """
    grouped = {}
    unregistered = []
    dropped = []
    for row in points_rows:
        if not isinstance(row, dict):
            continue
        face = row.get("face")
        surface = row.get("surface")
        if not isinstance(face, str) or not isinstance(surface, str):
            continue
        if face not in bearings:
            if face not in unregistered:
                unregistered.append(face)
            continue
        x = _number(row.get("X"))
        y = _number(row.get("Y"))
        z = _number(row.get("Z"))
        if x is None or y is None or z is None:
            if face not in dropped:
                dropped.append(face)
            continue
        angle = math.radians(bearings[face])
        s = (x * math.sin(angle)) + (y * math.cos(angle))
        grouped.setdefault(surface, {}).setdefault(face, []).append((s, x, y, z))

    for face in unregistered:
        notes.append(
            f"face {face!r} has no bearing_deg in the grid config; its points "
            "cannot contribute to a true-dip solve")
    for face in dropped:
        notes.append(
            f"face {face!r} has points whose X, Y or Z could not be read as "
            "numbers; those points were left out of the true-dip solve")
    return grouped


def _wall_direction(points):
    """(direction, ordered points) for one wall's trace, or (None, ordered).

    The direction is (sin bearing, cos bearing, dZ/ds): one step along the wall
    moves that far horizontally and dZ/ds vertically. The slope is ordinary
    least squares over the whole trace rather than an endpoint difference, so
    one badly placed vertex cannot swing it.
    """
    ordered = sorted(points)
    n = len(ordered)
    if n < 2:
        return None, ordered

    s_values = [point[0] for point in ordered]
    z_values = [point[3] for point in ordered]
    s_mean = sum(s_values) / n
    z_mean = sum(z_values) / n
    variance = sum((s - s_mean) ** 2 for s in s_values)
    if variance == 0.0:
        return None, ordered

    slope = sum(
        (s - s_mean) * (z - z_mean) for s, z in zip(s_values, z_values)
    ) / variance
    return slope, ordered


def _best_pair(faces, bearings, threshold):
    """The two faces whose bearings are furthest from parallel, or None.

    Pairs are scored by |sin(difference)|: 1 for perpendicular walls, 0 for
    parallel ones. Ties keep the earlier pair in face order, so the result does
    not depend on dict iteration luck.
    """
    best = None
    best_score = threshold
    for first in range(len(faces)):
        for second in range(first + 1, len(faces)):
            a, b = faces[first], faces[second]
            score = abs(math.sin(math.radians(bearings[a] - bearings[b])))
            if score > best_score:
                best_score = score
                best = (a, b)
    return best


def _dip_from_normal(normal):
    """(dip_degrees, azimuth_degrees) for a plane normal, pointing upward.

    For an upward normal the downhill horizontal direction is (n_x, n_y), and a
    compass bearing is atan2(east, north) -- not the mathematical atan2(y, x).
    """
    length = math.sqrt(sum(component ** 2 for component in normal))
    if length == 0.0:
        return None
    x, y, z = (component / length for component in normal)
    if z < 0:
        x, y, z = -x, -y, -z

    dip = math.degrees(math.acos(max(-1.0, min(1.0, z))))
    if math.hypot(x, y) == 0.0:
        # Perfectly flat: the dip direction is undefined, and the sign flip
        # above can leave negative zeros that atan2 would read as due south.
        return dip, 0.0
    # Near-flat surfaces keep their solved azimuth on purpose. Rounding it to
    # zero would not remove the orientation's pull on the model, it would aim
    # that same pull north. A surface too flat to trust has to be dropped, not
    # flattened -- and near-horizontal layers are the normal case here.
    return dip, math.degrees(math.atan2(x, y)) % 360.0


def true_orientations(points_rows, grid, min_separation_deg=10.0):
    """Solve one orientation per surface from its traces on two walls.

    points_rows: interface points as run_convert writes them -- dicts with X,
    Y, Z, surface and face; numbers or numeric strings both work.
    grid: the trench grid config; only each face's bearing_deg is read.
    min_separation_deg: walls closer in bearing than this are treated as
    parallel and refused rather than solved badly.

    Returns (orientations, notes). Each orientation is
    {"surface", "dip", "azimuth", "faces": [a, b], "seeds": [{face, X, Y, Z}]}
    with both seeds carrying the same solved dip and azimuth, each placed on a
    real traced point of its own wall. Neither argument is mutated.
    """
    notes = []
    bearings = _face_bearings(grid)
    grouped = _grouped(points_rows, bearings, notes)
    threshold = abs(math.sin(math.radians(min_separation_deg)))

    orientations = []
    for surface, by_face in grouped.items():
        directions = {}
        traces = {}
        for face, points in by_face.items():
            slope, ordered = _wall_direction(points)
            if slope is None:
                notes.append(
                    f"surface {surface!r} on face {face!r} has too few "
                    "distinct points along the wall to measure a slope; it "
                    "was left out of the true-dip solve")
                continue
            angle = math.radians(bearings[face])
            directions[face] = (math.sin(angle), math.cos(angle), slope)
            traces[face] = ordered

        faces = list(directions)
        if len(faces) < 2:
            if len(faces) == 1:
                notes.append(
                    f"surface {surface!r} is only on face {faces[0]!r}; its "
                    "dip stays the apparent dip measured on that one wall, "
                    "which is always shallower than the true dip")
            continue

        pair = _best_pair(faces, bearings, threshold)
        if pair is None:
            notes.append(
                f"surface {surface!r} appears only on walls that are within "
                f"{min_separation_deg} degrees of parallel "
                f"({', '.join(repr(face) for face in faces)}); a true dip "
                "cannot be solved from them, so the existing apparent dips "
                "stand")
            continue

        first, second = pair
        a = directions[first]
        b = directions[second]
        normal = (
            (a[1] * b[2]) - (a[2] * b[1]),
            (a[2] * b[0]) - (a[0] * b[2]),
            (a[0] * b[1]) - (a[1] * b[0]),
        )
        solved = _dip_from_normal(normal)
        if solved is None:  # pragma: no cover - _best_pair rules this out
            continue
        dip, azimuth = solved

        seeds = []
        for face in pair:
            ordered = traces[face]
            _s, x, y, z = ordered[len(ordered) // 2]
            seeds.append({"face": face, "X": x, "Y": y, "Z": z})

        orientations.append({
            "surface": surface,
            "dip": dip,
            "azimuth": azimuth,
            "faces": [first, second],
            "seeds": seeds,
        })

    return orientations, notes


def apply_true_dip(points_csv, orientations_csv, grid, min_separation_deg=10.0):
    """Give every seed of a solved surface that surface's true orientation.

    Rewrites `orientations_csv` in place: each seed keeps its own position on
    its own wall -- `convert()` already placed those on real traced points --
    and only its dip and azimuth change, to the one plane solved from two
    walls. Surfaces that could not be solved are left exactly as they were,
    still carrying the apparent dip of the wall they were measured on, which
    is the best available answer for them.

    Returns notes: the solver's own, plus one line per corrected surface
    recording what was replaced, so a reader can see the change rather than
    discovering the numbers moved.
    """
    try:
        with open(points_csv, newline="") as handle:
            points_rows = list(csv.DictReader(handle))
    except OSError as error:
        return [f"could not read {points_csv} to solve true dips: {error}"]

    orientations, notes = true_orientations(
        points_rows, grid, min_separation_deg)
    if not orientations:
        return notes

    try:
        with open(orientations_csv, newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames
            seed_rows = list(reader)
    except OSError as error:
        notes.append(
            f"solved true dips but could not read {orientations_csv} to "
            f"apply them: {error}")
        return notes

    by_surface = {
        orientation["surface"]: orientation for orientation in orientations
    }
    replaced = {surface: [] for surface in by_surface}
    for row in seed_rows:
        solved = by_surface.get(row.get("surface"))
        if solved is None:
            continue
        replaced[solved["surface"]].append(
            f"{row.get('face')} {row.get('dip')} toward {row.get('azimuth')}")
        row["dip"] = round(solved["dip"], 2)
        row["azimuth"] = round(solved["azimuth"], 2)

    for surface, before in replaced.items():
        solved = by_surface[surface]
        if not before:
            notes.append(
                f"surface {surface!r}: solved a true dip from "
                f"{' and '.join(solved['faces'])} but the orientations file "
                "has no seed for it, so nothing was changed")
            continue
        notes.append(
            f"surface {surface!r}: replaced the per-wall apparent dips "
            f"({'; '.join(before)}) with one true dip of "
            f"{round(solved['dip'], 2)} toward {round(solved['azimuth'], 2)}, "
            f"solved from {' and '.join(solved['faces'])}")

    with open(orientations_csv, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(seed_rows)
    return notes
