"""
Face-local (x, depth) -> site-wide (X, Y, Z) for GemPy.
Adapted from 05_convert_coords/convertCoords.py into importable functions.

Two extraction shapes feed in here:
  - ArchaeologicalDiagram (illustrator sheets): {"trenchProfiles": [...]}
  - FieldWallProfile      (modern field sheets): {"loci": [...], "layers": [...]}
The second is adapted into the first's shape by fieldwall_to_profiles() so the
site-coordinate math below stays a single code path.
"""

import csv
import math

from . import canonical, site_elevation, site_grid


def slope_to_orientation(
    slope: float,
    face_bearing: float,
) -> tuple[float, float]:
    """
    Convert a signed section slope into GemPy dip and azimuth values.

    A positive slope dips in the direction of face_bearing.
    A negative slope dips in the opposite direction.

    Returns:
        (dip_degrees, azimuth_degrees)
    """
    if not math.isfinite(slope):
        raise ValueError("slope must be finite")

    if not math.isfinite(face_bearing):
        raise ValueError("face_bearing must be finite")

    dip = math.degrees(math.atan(abs(slope)))

    if slope >= 0:
        azimuth = face_bearing % 360.0
    else:
        azimuth = (face_bearing + 180.0) % 360.0

    return dip, azimuth


def least_squares_slope(xs, ds):
    """Best-fit slope (dz/dx) of depth vs. x over ALL points, not just the
    endpoints. Falls back to 0.0 if x has no spread (can't determine a slope).

    Restored from commit b01638d. This was dropped when the files were
    reorganized into numbered folders (c7ec511), silently reverting the
    orientation seeds to an endpoint-only slope."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_d = sum(ds) / n
    num = sum((x - mean_x) * (d - mean_d) for x, d in zip(xs, ds))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0:
        return 0.0
    return num / den


def get_y(p):
    if p.get("yCoordinateMeters") is not None:
        return p["yCoordinateMeters"]
    return p.get("depthMeters")


def get_x(p):
    """x along the face. Illustrator sheets say xCoordinateMeters; field
    sheets say xMeters."""
    if p.get("xCoordinateMeters") is not None:
        return p["xCoordinateMeters"]
    return p.get("xMeters")


# FieldWallProfile -> trenchProfiles adapter


def is_field_wall(data):
    """True for a FieldWallProfile extraction (T104-style field sheet)."""
    return "trenchProfiles" not in data and ("loci" in data or "layers" in data)


def _munsell_label(entry):
    """'10YR 5/3 brown' from a locus entry, however munsell got serialized."""
    m = entry.get("munsell")
    if isinstance(m, str):
        return m.strip() or None
    if isinstance(m, dict):
        parts = [m.get("raw"), m.get("colorName")]
        parts = [
            str(p).strip() for p in parts if p and str(p).strip().lower() != "none"
        ]
        return " ".join(parts) or None
    return None


def surface_id(locus_number):
    """The stable identity of a locus's model surface: ``Locus 6``.

    A deposit is identified at this site by its trench and locus number. A
    model is built from one trench, so the locus number alone is unique within
    it, and the prefix would add nothing.

    What this deliberately does NOT contain is the Munsell reading. GemPy fuses
    interface points into a surface by exact string match on this value, so
    anything inside it is part of the deposit's identity. A soil colour is an
    observation about a deposit, not a name for one: readings of the same
    deposit differ legitimately between recorders, between walls, and between
    wet and dry soil. When the reading was part of the name, two walls
    describing one deposit slightly differently produced two model surfaces,
    and an entire canonicalization layer existed in merge_walls to stop that
    happening. Identity here, colour in the display label.
    """
    return canonical.surface_id_for(locus_number, canonical.FIELD_WALL)


def as_canonical(data):
    """A canonical document from a canonical document or either capture shape.

    Returns (canonical, warnings)."""
    if canonical.is_canonical(data):
        return data, []
    return canonical.canonicalize(data)


def canonical_to_profiles(document, face_name=None):
    """Project a canonical document into the legacy trenchProfiles shape.

    The shape consumers below and in merge_walls still read. Both boundaries
    keep their own names here: the old adapter wrote a locus top into the key
    called ``bottomBoundary``, which every reader then had to know about.
    """
    profiles = []
    for face in document.get("faces") or []:
        layers = []
        for layer in face.get("layers") or []:
            layers.append(
                {
                    "layerName": layer["surfaceId"],
                    "inferredMaterial": layer["surfaceId"],
                    "displayLabel": layer["displayLabel"],
                    "topBoundary": layer["topBoundary"],
                    "bottomBoundary": layer["bottomBoundary"],
                    "featuresInLayer": layer["features"] or None,
                }
            )
        profiles.append(
            {
                "face": face_name or face["face"],
                "gridRefs": face["gridRefs"],
                "layers": layers,
            }
        )
    return {"trenchProfiles": profiles}


def fieldwall_to_profiles(data, face_name=None):
    """Adapt a FieldWallProfile dict into the trenchProfiles shape.

    A compatibility delegate: canonicalization does the work and every
    consumer should read the canonical form directly. Kept because
    merge_walls and the validator still speak trenchProfiles.
    """
    document, warnings = as_canonical(data)
    name = face_name or data.get("faceLabel") or data.get("trenchLabel") or "field wall"
    return canonical_to_profiles(document, face_name=name), warnings


def make_starter_config(data):
    """Returns a starter grid-config dict with placeholder values per face.
    Accepts a canonical document or either capture shape."""
    document, _ = as_canonical(data)
    field_wall = document["sourceSchema"] == canonical.FIELD_WALL

    cfg = {
        "_comment": (
            "Fill in real site values from the master Geospatial Spreadsheet "
            "(opening-coordinates column for the season). bearing_deg = the "
            "direction the face's local +x axis points, in degrees clockwise "
            "from GRID NORTH -- the site's artificial reference direction, the "
            "one the total station sets as HA 0 (90 East, 180 South, 270 "
            "West). It is NOT magnetic north and NOT projected north; Grid "
            "North sits about 2.5 degrees off the latter. originX/originY = "
            "site grid coordinates of the face's x=0 edge, with the site's "
            "sign rule: North and East positive, South and West negative, so "
            "190E/53S is originX 190, originY -53. surfaceZ = ground-surface "
            "elevation at that edge, absolute, in mAE (meters absolute "
            "elevation) -- elevations at this site are in the twenties, not "
            "the hundreds."
        ),
        # Which of the site's two local grids these numbers belong to. A bare
        # pair of coordinates is not a location: the Poggio Civitate and
        # Vescovado di Murlo grids have origins about 1.5 million metres apart
        # once projected.
        "site_grid": None,
        # Where the numbers below came from. Declared rather than inferred:
        # is_placeholder() otherwise has to recognise the starter's own value
        # pattern, and its docstring admits real survey values can collide
        # with it. Set to "surveyed" once these are real.
        "source": "placeholder",
        "vertical": {
            "frame": site_elevation.MAE,
            # "absolute" or "below-datum". Below-datum readings need the datum
            # nail's own elevation before they can be resolved, and are
            # transitional by the site's own rule -- they must be corrected to
            # absolute elevations for the final record.
            "entryForm": "absolute",
            "datumNail": {"absoluteZ": None, "label": None},
        },
        "faces": {},
    }
    for i, face in enumerate(document["faces"]):
        name = face.get("face") or f"face_{i}"
        cfg["faces"][name] = {
            "originX": 0.0 + i * 10.0,
            "originY": 0.0,
            "surfaceZ": 100.0,
            "bearing_deg": 90.0,
        }

    # The sheet's own tie-in labels are the likeliest source of these numbers.
    # Grid labels like "190E/53S" have a defined reading (site_grid.label_to_grid
    # applies the site's sign rule), so any that parse are offered alongside the
    # raw text. Both mediums record them: a field sheet in gridTiePoints, an
    # illustrator sheet in gridLabels. Canonical calls both gridRefs, which is
    # why the same hint now reaches both.
    ties = []
    for face in document["faces"]:
        for ref in face["gridRefs"]:
            raw = ref.get("rawText")
            if not raw:
                continue
            try:
                grid_x, grid_y = site_grid.label_to_grid(raw)
            except site_grid.GridError:
                ties.append({"rawText": raw, "gridX": None, "gridY": None})
            else:
                ties.append({"rawText": raw, "gridX": grid_x, "gridY": grid_y})

    if ties:
        cfg["_tiePointsFromSheet"] = ties
        cfg["_comment"] += (
            " The labels transcribed off the drawing are listed in "
            "_tiePointsFromSheet, with their grid coordinates where the label "
            "could be read. They are NOT applied here: which end of a face "
            "each label marks is a site-records question. Confirm before use."
        )
    if field_wall:
        cfg["_comment"] += " This is a single-wall field sheet, so there is one face."
    return cfg


def surface_labels(data):
    """{surface_id: display label} for a document, for anything user-facing.

    Only surfaces whose label differs from their id appear, so a document with
    no Munsell readings produces an empty map rather than a table of
    identities. The first label seen for an id wins; a later disagreement is
    the merge layer's to report, not this function's to resolve.
    """
    document, _ = as_canonical(data or {})
    labels = {}
    for face in document["faces"]:
        for layer in face["layers"]:
            name = layer["surfaceId"]
            label = layer["displayLabel"]
            if not name or not label or label == name:
                continue
            labels.setdefault(str(name), str(label))
    return labels


def modelled_boundaries(face):
    """Every drawn interface on a face, with the surface each one belongs to.

    D2: a locus is a volume, and GemPy builds volumes between interfaces, so
    each unit is enclosed by its own two lines. A layer's TOP carries that
    layer's identity, which is the site's own practice of naming a locus by
    the surface it opens on. The deepest layer's base line is the limit of
    excavation rather than a deposit, so it is modelled under its own name.
    """
    layers = face.get("layers") or []
    pairs = [(layer["surfaceId"], layer["topBoundary"]) for layer in layers]
    if layers and layers[-1]["bottomBoundary"]:
        pairs.append((canonical.BASE_SURFACE_ID, layers[-1]["bottomBoundary"]))
    return pairs


def convert(data, grid, out_csv):
    """Returns (rows, orient, missing_faces, notes)."""
    document, notes = as_canonical(data)
    faces_cfg = grid.get("faces", {})
    rows = []
    orient = []
    missing = []

    for fi, face in enumerate(document["faces"]):
        fname = face.get("face") or f"face_{fi}"
        cfg = faces_cfg.get(fname)
        if cfg is None:
            missing.append(fname)
            continue
        X0, Y0 = cfg["originX"], cfg["originY"]
        Z0 = cfg["surfaceZ"]
        th = math.radians(cfg["bearing_deg"])
        sin_t, cos_t = math.sin(th), math.cos(th)

        # The registration values are bound as defaults rather than closed
        # over: to_site is only ever called inside this iteration, but binding
        # makes that explicit and keeps the closure from tracking the loop.
        def to_site(x, depth, X0=X0, Y0=Y0, Z0=Z0, sin_t=sin_t, cos_t=cos_t):
            X = X0 + x * sin_t
            Y = Y0 + x * cos_t
            Z = Z0 - depth
            return X, Y, Z

        for surface, boundary in modelled_boundaries(face):
            pts = [(get_x(p), get_y(p)) for p in boundary or []]
            pts = [
                (x, d)
                for (x, d) in pts
                if isinstance(x, (int, float)) and isinstance(d, (int, float))
            ]
            for x, d in pts:
                X, Y, Z = to_site(x, d)
                rows.append(
                    {
                        "X": round(X, 4),
                        "Y": round(Y, 4),
                        "Z": round(Z, 4),
                        "surface": surface,
                        "face": fname,
                    }
                )
            if len(pts) >= 2:
                xs = [p[0] for p in pts]
                ds = [p[1] for p in pts]

                dz_dx = least_squares_slope(xs, ds)

                dip, azimuth = slope_to_orientation(
                    slope=dz_dx,
                    face_bearing=cfg["bearing_deg"],
                )

                midx = xs[len(xs) // 2]
                midd = ds[len(ds) // 2]

                X, Y, Z = to_site(midx, midd)

                orient.append(
                    {
                        "X": round(X, 4),
                        "Y": round(Y, 4),
                        "Z": round(Z, 4),
                        "surface": surface,
                        "face": fname,
                        "dip": round(dip, 2),
                        "azimuth": round(azimuth, 2),
                        "polarity": 1,
                    }
                )

    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["X", "Y", "Z", "surface", "face"])
        w.writeheader()
        w.writerows(rows)
    orient_csv = out_csv.rsplit(".", 1)[0] + "_orientations.csv"
    with open(orient_csv, "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["X", "Y", "Z", "surface", "face", "dip", "azimuth", "polarity"],
        )
        w.writeheader()
        w.writerows(orient)

    return rows, orient, missing, notes


def run_convert(data: dict, grid: dict, out_csv: str):
    rows, orient, missing, notes = convert(data, grid, out_csv)
    orient_csv = out_csv.rsplit(".", 1)[0] + "_orientations.csv"
    document, _ = as_canonical(data)
    return {
        "points_csv": out_csv,
        "orientations_csv": orient_csv,
        "n_points": len(rows),
        "n_orientations": len(orient),
        "missing_faces": missing,
        "notes": notes,
        "source_shape": (
            "field_wall"
            if document["sourceSchema"] == canonical.FIELD_WALL
            else "illustrator"
        ),
        "rows_preview": rows[:200],
        # Not written into the CSV: the CSV's `surface` column is the identity
        # GemPy fuses on, and adding a colour to it is the coupling this
        # separation removes. Labels travel beside it, for display only.
        "surface_labels": surface_labels(document),
    }
