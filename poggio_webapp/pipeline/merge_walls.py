"""
merge_walls.py -- combine several per-wall extractions into ONE multi-face
trenchProfiles document.

Why this exists: one job holds one sheet, and a FieldWallProfile sheet records
one wall. To model a whole trench, the per-wall extractions must be merged
BEFORE coordinate conversion, because everything downstream (grid config,
convert(), build_gempy) is already multi-face.

The one correctness rule that shapes this module: GemPy fuses interface points
into a surface purely by exact string match on the surface name. The same
locus on two walls is the same deposit and MUST get the identical name;
different deposits must never collide. Surface names for field sheets are
built by convert_coords.fieldwall_to_profiles() as 'Locus N (munsell)', and
Munsell readings of one locus routinely differ slightly between sheets, so
this module canonicalizes the Munsell label per locus number trench-wide and
feeds the canonical values into the existing adapter. It never builds surface
strings itself.

Like the rest of the pipeline, functions return a `notes` list of
human-readable warnings instead of silently guessing, and raise ValueError
only on genuinely unusable input.
"""

import copy
import heapq
import math

from . import convert_coords


def _validate_sheets(sheets):
    """Returns [(stripped_label, data), ...] or raises ValueError."""
    if not sheets:
        raise ValueError("no sheets given -- need at least one wall to merge")
    cleaned = []
    seen = {}
    for i, item in enumerate(sheets):
        try:
            label, data = item
        except (TypeError, ValueError):
            raise ValueError(f"sheets[{i}] is not a (wall_label, data) pair")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"sheets[{i}] has an empty wall_label")
        if not isinstance(data, dict):
            raise ValueError(f"sheets[{i}] ({label!r}) data is not a dict")
        key = label.strip().lower()
        if key in seen:
            raise ValueError(
                f"wall_label {label.strip()!r} duplicates {seen[key]!r} "
                "(labels are compared case-insensitively)")
        seen[key] = label.strip()
        cleaned.append((label.strip(), data))
    return cleaned


def _parse_correlation(correlation):
    """'wall:locus' -> canonical, keyed for lookup as (wall_lower, locus)."""
    parsed = {}
    for key, canonical in (correlation or {}).items():
        wall, sep, num = str(key).partition(":")
        if not sep or not wall.strip() or not str(num).strip():
            raise ValueError(
                f"correlation key {key!r} is not 'wall_label:locusNumber'")
        parsed[(wall.strip().lower(), str(num).strip())] = str(canonical).strip()
    return parsed


def _apply_correlation(label, sheet, parsed, notes):
    """Rename locusNumber values in loci[] and layers[] per the correlation
    map, in place (sheet is already a private deep copy)."""
    renames = {num: canon for (wall, num), canon in parsed.items()
               if wall == label.lower()}
    if not renames:
        return
    applied = set()
    for section in ("loci", "layers"):
        for entry in (sheet.get(section) or []):
            if not isinstance(entry, dict):
                continue
            num = str(entry.get("locusNumber", "")).strip()
            if num in renames:
                entry["locusNumber"] = renames[num]
                applied.add(num)
    for num in sorted(applied):
        notes.append(f"wall {label!r}: locus {num} renamed to "
                     f"{renames[num]} per the correlation map")
    for num in sorted(set(renames) - applied):
        notes.append(f"correlation key {label}:{num} matched no locus on "
                     f"wall {label!r} -- check the map for typos")


def _canonical_munsell(field_sheets, notes):
    """One trench-wide locusNumber -> Munsell label map. First usable reading
    (in sheet order, then loci[] order) wins; disagreements become notes.
    Within one sheet, only the first entry per number is considered; the
    adapter itself notes intra-sheet duplicates when it runs."""
    canon = {}   # num -> (label, wall_label that defined it)
    for wall_label, sheet in field_sheets:
        seen_here = set()
        for entry in (sheet.get("loci") or []):
            if not isinstance(entry, dict):
                continue
            num = str(entry.get("locusNumber", "")).strip()
            if not num or num in seen_here:
                continue
            seen_here.add(num)
            reading = convert_coords._munsell_label(entry)
            if reading is None:
                continue
            if num not in canon:
                canon[num] = (reading, wall_label)
            elif canon[num][0] != reading:
                first_reading, first_wall = canon[num]
                notes.append(
                    f"locus {num}: Munsell disagrees between wall "
                    f"{first_wall!r} ({first_reading!r}) and wall "
                    f"{wall_label!r} ({reading!r}); using {first_reading!r} "
                    "trench-wide so both walls map to one model surface")
    return {num: reading for num, (reading, _) in canon.items()}


def _canonicalize_sheet(label, sheet, canon, notes):
    """Overwrite this sheet's Munsell values with the trench-wide canonical
    ones, and make sure every locus used in layers[] has a loci[] entry when
    a canonical reading exists -- otherwise fieldwall_to_profiles would name
    it 'Locus N' (no color) here and 'Locus N (color)' on another wall, and
    GemPy would treat one deposit as two surfaces."""
    listed = set()
    for entry in (sheet.get("loci") or []):
        if not isinstance(entry, dict):
            continue
        num = str(entry.get("locusNumber", "")).strip()
        if not num:
            continue
        listed.add(num)
        if num in canon:
            entry["munsell"] = canon[num]
    for entry in (sheet.get("layers") or []):
        if not isinstance(entry, dict):
            continue
        num = str(entry.get("locusNumber", "")).strip()
        if num and num in canon and num not in listed:
            sheet.setdefault("loci", []).append(
                {"locusNumber": num, "munsell": canon[num]})
            listed.add(num)
            notes.append(
                f"wall {label!r}: locus {num} appears in layers[] but not "
                f"loci[]; using the trench-wide Munsell reading "
                f"{canon[num]!r} so its surface name matches the other walls")


def merge_extractions(sheets, correlation=None):
    """Merge per-wall extractions into one multi-face trenchProfiles document.

    sheets: list of (wall_label: str, data: dict) where data is a normalized
        extraction in either shape (FieldWallProfile or a document that
        already has 'trenchProfiles').
    correlation: optional dict mapping 'wall_label:locusNumber' -> canonical
        locusNumber string, for deposits recorded under different numbers on
        different walls.

    Returns (merged, notes) where merged == {'trenchProfiles': [...]}.
    Inputs are never mutated.
    """
    cleaned = _validate_sheets(sheets)
    parsed_correlation = _parse_correlation(correlation)
    notes = []

    # Private deep copies from here on; callers' dicts stay untouched.
    copies = [(label, copy.deepcopy(data)) for label, data in cleaned]

    # 1. Correlation renames first, so the canonical-Munsell map is built on
    #    the corrected numbering.
    for label, sheet in copies:
        if convert_coords.is_field_wall(sheet):
            _apply_correlation(label, sheet, parsed_correlation, notes)

    # 2. Trench-wide canonical Munsell per locus, pushed back into each copy.
    field_sheets = [(label, sheet) for label, sheet in copies
                    if convert_coords.is_field_wall(sheet)]
    canon = _canonical_munsell(field_sheets, notes)
    for label, sheet in field_sheets:
        _canonicalize_sheet(label, sheet, canon, notes)

    # 3. Adapt every sheet to faces. Field sheets go through the existing
    #    adapter (which does ALL surface naming); illustrator-shaped sheets
    #    pass through.
    entries = []   # {'face': dict, 'name': str, 'sheet': int,
                   #  'wall_label': str, 'illustrator': bool}
    for sheet_index, (label, sheet) in enumerate(copies):
        if convert_coords.is_field_wall(sheet):
            adapted, adapter_notes = convert_coords.fieldwall_to_profiles(
                sheet, face_name=label)
            notes.extend(adapter_notes)
            for face in adapted.get("trenchProfiles", []):
                entries.append({"face": face, "name": face.get("face"),
                                "sheet": sheet_index, "wall_label": label,
                                "illustrator": False})
        else:
            faces = sheet.get("trenchProfiles") or []
            if not faces:
                notes.append(f"sheet {label!r} has no recognizable extraction "
                             "content (no trenchProfiles, loci, or layers); "
                             "it contributed no faces")
            for j, face in enumerate(faces):
                name = face.get("face")
                if not name:
                    name = f"face_{j}"
                    face["face"] = name
                    notes.append(f"sheet {label!r}: face at index {j} has no "
                                 f"name -- assigned {name!r}")
                entries.append({"face": face, "name": name,
                                "sheet": sheet_index, "wall_label": label,
                                "illustrator": True})

    # 4. Cross-sheet name collisions: prefix the illustrator face(s) with
    #    their wall label. Decided on the pre-prefix names so order can't
    #    matter. Field-wall faces are named by their (unique) wall labels and
    #    are never renamed.
    if len(copies) > 1:
        sheets_using = {}
        for e in entries:
            sheets_using.setdefault(e["name"], set()).add(e["sheet"])
        for e in entries:
            if e["illustrator"] and len(sheets_using.get(e["name"], set())) > 1:
                new_name = f"{e['wall_label']}: {e['name']}"
                notes.append(f"sheet {e['wall_label']!r}: face "
                             f"{e['name']!r} collides with a face from "
                             f"another sheet -- renamed to {new_name!r}")
                e["name"] = new_name
                e["face"]["face"] = new_name

    # 5. Any duplicate left now means the input itself was pathological.
    names = [e["name"] for e in entries]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ValueError("duplicate face names after merge: "
                         + ", ".join(repr(d) for d in duplicates))

    merged = {"trenchProfiles": [e["face"] for e in entries]}
    return merged, notes


def _surface_name(layer):
    """The surface string convert() will write for this layer. Resolved with
    convert()'s own precedence so the returned order matches the CSV's
    `surface` column exactly -- GemPy fuses by exact string match, and
    run_build rejects a series_order naming anything absent from the CSV."""
    if not isinstance(layer, dict):
        return None
    return str(layer.get("inferredMaterial") or layer.get("layerName")
               or "unknown")


def merged_series_order(merged):
    """One trench-wide young-to-old surface order for a merged document.

    merged: the dict returned by merge_extractions().
    Returns (order, notes) where order is a list[str] suitable to pass as
    `series_order` to build_gempy.run_build().

    Each face's layers[] is already top-to-bottom, i.e. young to old, so every
    adjacent pair within a face is an ordering constraint. The constraints from
    all faces are merged and topologically sorted (Kahn's algorithm). Ties are
    broken by first-seen input order, so the result is deterministic.

    Raises ValueError if the walls contradict each other (a cycle). Guessing an
    order there would invent stratigraphy, so it refuses.
    """
    faces = (merged or {}).get("trenchProfiles") or []
    notes = []

    order_index = {}       # surface -> first-seen position (the tie-breaker)
    faces_by_surface = {}  # surface -> [face names, in order]
    successors = {}        # surface -> {surfaces that must come after it}
    indegree = {}

    for face_i, face in enumerate(faces):
        if not isinstance(face, dict):
            continue
        fname = face.get("face") or f"face_{face_i}"
        sequence = []
        for layer in (face.get("layers") or []):
            name = _surface_name(layer)
            if name is None:
                continue
            if name not in order_index:
                order_index[name] = len(order_index)
                faces_by_surface[name] = []
                successors[name] = set()
                indegree[name] = 0
            if fname not in faces_by_surface[name]:
                faces_by_surface[name].append(fname)
            sequence.append(name)
        for earlier, later in zip(sequence, sequence[1:]):
            if earlier == later:
                notes.append(
                    f"face {fname!r} lists surface {earlier!r} in two adjacent "
                    "layers; ignoring that self-constraint (it would look like "
                    "a contradiction)")
                continue
            if later not in successors[earlier]:
                successors[earlier].add(later)
                indegree[later] += 1

    if not order_index:
        notes.append("no named layers in the merged document -- no "
                     "stratigraphic order to derive")
        return [], notes

    # Kahn's algorithm. The ready set is a heap of first-seen positions, so
    # whenever several surfaces are simultaneously available the earliest-seen
    # one wins and the output is stable.
    by_index = {position: name for name, position in order_index.items()}
    ready = [position for name, position in order_index.items()
             if indegree[name] == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        name = by_index[heapq.heappop(ready)]
        order.append(name)
        for later in sorted(successors[name], key=lambda n: order_index[n]):
            indegree[later] -= 1
            if indegree[later] == 0:
                heapq.heappush(ready, order_index[later])

    if len(order) < len(order_index):
        raise ValueError(_cycle_message(order, order_index, successors,
                                        faces_by_surface))

    if len(faces) > 1:
        for name in order:
            if len(faces_by_surface[name]) == 1:
                notes.append(
                    f"surface {name!r} has layers on only one wall "
                    f"({faces_by_surface[name][0]}); it is ordered from fewer "
                    "constraints and will still be interpolated across the "
                    "whole model extent")

    return order, notes


def _cycle_message(order, order_index, successors, faces_by_surface):
    """Name the surfaces actually on a cycle, not everything downstream of it.
    Repeatedly drop unsorted surfaces with no remaining predecessor or no
    remaining successor; what survives is on a cycle."""
    remaining = set(order_index) - set(order)
    changed = True
    while changed:
        changed = False
        for name in sorted(remaining, key=lambda n: order_index[n]):
            has_successor = bool(successors[name] & remaining)
            has_predecessor = any(name in successors[other]
                                  for other in remaining)
            if not (has_successor and has_predecessor):
                remaining.discard(name)
                changed = True
    cycle = remaining or (set(order_index) - set(order))
    listed = ", ".join(
        f"{name!r} (on {', '.join(faces_by_surface[name])})"
        for name in sorted(cycle, key=lambda n: order_index[n]))
    return ("the walls contradict each other: these surfaces form a "
            "stratigraphic cycle and cannot be ordered young to old -- "
            + listed
            + ". Check the layer order on those walls, or correlate the loci "
              "explicitly; no order is guessed.")


# ---------------------------------------------------------------------------
# Grid config for a merged trench
# ---------------------------------------------------------------------------

# The pattern make_starter_config() stamps out: face i gets originX = i * 10,
# originY 0, surfaceZ 100, bearing 90. Left in a config it silently produces a
# row of parallel walls 10 m apart instead of a pit.
_PLACEHOLDER_ORIGIN_STEP = 10.0
_PLACEHOLDER_ORIGIN_Y = 0.0
_PLACEHOLDER_SURFACE_Z = 100.0
_PLACEHOLDER_BEARING = 90.0

_MAX_DATUM_SPREAD_M = 2.0


def make_trench_starter_config(merged):
    """A starter grid config for a merged multi-wall document.

    Delegates to convert_coords.make_starter_config() and returns its result
    unchanged except for an extended _comment: a merged trench only forms a pit
    if adjacent walls actually share their corner coordinates, which a
    per-sheet starter cannot know.
    """
    cfg = convert_coords.make_starter_config(merged)
    cfg["_comment"] = cfg.get("_comment", "") + (
        " This is a MERGED multi-wall trench: every face below is one wall of "
        "the same pit, and the placeholder values put them in a row 10 m "
        "apart, not around a pit. Adjacent walls MUST share corner "
        "coordinates -- one wall's end point has to be the next wall's start "
        "point within survey tolerance -- or the model will not close into a "
        "trench and surfaces will be interpolated across empty space. Replace "
        "every value with real survey numbers, then re-check with "
        "check_trench_grid_config()."
    )
    return cfg


def _face_names(merged):
    """Face names in document order, resolved the way convert() resolves
    them so a config keyed off one works for the other."""
    names = []
    for face_i, face in enumerate((merged or {}).get("trenchProfiles") or []):
        if not isinstance(face, dict):
            continue
        names.append(face.get("face") or f"face_{face_i}")
    return names


def face_length_m(face):
    """The face's along-wall extent: the largest x found on its boundaries.
    Returns None when the face has no usable points."""
    xs = []
    for layer in (face.get("layers") or []):
        if not isinstance(layer, dict):
            continue
        for key in ("bottomBoundary", "topBoundary"):
            for point in (layer.get(key) or []):
                if not isinstance(point, dict):
                    continue
                x = convert_coords.get_x(point)
                if isinstance(x, (int, float)) and not isinstance(x, bool):
                    xs.append(float(x))
    return max(xs) if xs else None


def face_endpoints(face_cfg, length_m):
    """The face's two ends in site coordinates: ((X0, Y0), (X1, Y1)).

    Uses convert()'s axis convention exactly -- X = X0 + x*sin(bearing),
    Y = Y0 + x*cos(bearing), bearing in degrees clockwise from north -- so
    bearing 90 puts all displacement into X and none into Y.
    """
    X0 = float(face_cfg["originX"])
    Y0 = float(face_cfg["originY"])
    theta = math.radians(float(face_cfg["bearing_deg"]))
    L = float(length_m)
    return (X0, Y0), (X0 + L * math.sin(theta), Y0 + L * math.cos(theta))


def _is_placeholder(face_cfg):
    """True if this face still carries make_starter_config()'s pattern."""
    try:
        originX = float(face_cfg["originX"])
        originY = float(face_cfg["originY"])
        surfaceZ = float(face_cfg["surfaceZ"])
        bearing = float(face_cfg["bearing_deg"])
    except (KeyError, TypeError, ValueError):
        return False
    remainder = abs(originX) % _PLACEHOLDER_ORIGIN_STEP
    on_step = (remainder < 1e-9
               or abs(remainder - _PLACEHOLDER_ORIGIN_STEP) < 1e-9)
    return (originY == _PLACEHOLDER_ORIGIN_Y
            and surfaceZ == _PLACEHOLDER_SURFACE_Z
            and bearing == _PLACEHOLDER_BEARING
            and on_step)


def _endpoint_components(endpoints, tolerance_m):
    """Group faces that meet at a corner. endpoints: {face: (start, end)}.
    Returns a list of face-name lists, each list in first-seen order."""
    names = list(endpoints)
    parent = {name: name for name in names}

    def find(name):
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    for i, a in enumerate(names):
        for b in names[i + 1:]:
            touching = any(
                math.dist(pa, pb) <= tolerance_m
                for pa in endpoints[a] for pb in endpoints[b])
            if touching:
                parent[find(a)] = find(b)

    groups = {}
    for name in names:
        groups.setdefault(find(name), []).append(name)
    return list(groups.values())


def check_trench_grid_config(grid, merged, tolerance_m=0.05):
    """Sanity-check a merged trench's grid config. Returns warnings: list[str].

    Bad geometry is never fatal -- it is the operator's to judge, and this
    repo's convention is to report rather than guess. A face missing from the
    config IS fatal (ValueError): convert() would silently drop that wall.
    """
    faces = [f for f in ((merged or {}).get("trenchProfiles") or [])
             if isinstance(f, dict)]
    names = _face_names(merged)
    faces_cfg = (grid or {}).get("faces") or {}

    missing = [name for name in names if name not in faces_cfg]
    if missing:
        raise ValueError(
            "grid config has no entry for these faces of the merged trench: "
            + ", ".join(repr(name) for name in missing)
            + " -- convert() would drop them from the model")

    warnings = []

    # 1. Starter placeholders. Building on these is the failure mode the
    #    README warns about, so it is worth naming loudly per face.
    for name in names:
        if _is_placeholder(faces_cfg[name]):
            warnings.append(
                f"face {name!r} is still the starter placeholder "
                f"(originY 0, surfaceZ 100, bearing 90, originX a multiple of "
                f"10); replace it with real survey values before building")

    # 2. Corner adjacency. Only meaningful once there are walls to join.
    if len(names) > 1:
        endpoints = {}
        for name, face in zip(names, faces):
            length = face_length_m(face)
            if length is None:
                warnings.append(
                    f"face {name!r} has no boundary points, so its extent is "
                    "unknown -- skipped the corner-adjacency check for it")
                continue
            try:
                endpoints[name] = face_endpoints(faces_cfg[name], length)
            except (KeyError, TypeError, ValueError):
                warnings.append(
                    f"face {name!r} has an unusable grid entry (need numeric "
                    "originX, originY, bearing_deg) -- skipped the "
                    "corner-adjacency check for it")

        if len(endpoints) > 1:
            components = _endpoint_components(endpoints, tolerance_m)
            # The trench is whichever group of walls is largest; ties go to the
            # group holding the earliest face, so the answer is deterministic.
            # An open end (a wall of an unexcavated side) is fine; a wall that
            # joins nothing at either end is the real problem.
            order = {name: i for i, name in enumerate(endpoints)}
            trench = max(components,
                         key=lambda g: (len(g), -min(order[n] for n in g)))
            for name in endpoints:
                if name not in trench:
                    warnings.append(
                        f"face {name!r} is not connected to the rest of the "
                        f"trench: neither of its ends lands within "
                        f"{tolerance_m} m of another wall's end. Adjacent "
                        "walls must share corner coordinates")

    # 3. Datum sanity.
    elevations = []
    for name in names:
        try:
            elevations.append(float(faces_cfg[name]["surfaceZ"]))
        except (KeyError, TypeError, ValueError):
            continue
    if len(elevations) > 1:
        spread = max(elevations) - min(elevations)
        if spread > _MAX_DATUM_SPREAD_M:
            warnings.append(
                f"surfaceZ spreads {spread:.2f} m across the faces "
                f"({min(elevations):.2f} to {max(elevations):.2f}); the walls "
                "may not share a datum -- confirm all elevations come from the "
                "same benchmark")

    return warnings