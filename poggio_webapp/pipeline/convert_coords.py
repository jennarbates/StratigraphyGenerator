"""
convert_coords.py — face-local (x, depth) -> site-wide (X, Y, Z) for GemPy.
Adapted from 05_convert_coords/convertCoords.py into importable functions.

Two extraction shapes feed in here:
  - ArchaeologicalDiagram (illustrator sheets): {"trenchProfiles": [...]}
  - FieldWallProfile      (modern field sheets): {"loci": [...], "layers": [...]}
The second is adapted into the first's shape by fieldwall_to_profiles() so the
site-coordinate math below stays a single code path.
"""

import csv
import math

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

    Restored from commit b01638d — this was dropped when the files were
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


# ---------------------------------------------------------------------------
# FieldWallProfile -> trenchProfiles adapter
# ---------------------------------------------------------------------------

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
        parts = [str(p).strip() for p in parts if p and str(p).strip().lower() != "none"]
        return " ".join(parts) or None
    return None


def fieldwall_to_profiles(data, face_name=None):
    """Adapt a FieldWallProfile dict into the single-face trenchProfiles shape
    that convert() reads. Returns (adapted_data, notes).

    A field sheet records ONE wall, so this produces exactly one face. Surface
    names become 'Locus N (munsell)' so the GemPy surfaces stay traceable back
    to the recorder's locus numbers.
    """
    notes = []

    fname = (face_name or data.get("faceLabel") or data.get("trenchLabel")
             or "field wall")

    # locus number -> munsell label. Duplicate locus numbers happen (T104 has
    # two entries numbered 5); take the first and say so rather than merging.
    munsell_by_locus = {}
    for entry in (data.get("loci") or []):
        num = str(entry.get("locusNumber", "")).strip()
        if not num:
            continue
        label = _munsell_label(entry)
        if num in munsell_by_locus:
            notes.append(f"locus {num} is listed more than once in loci[] — "
                         f"using the first Munsell reading ({munsell_by_locus[num]}) "
                         f"and ignoring {label!r}")
            continue
        munsell_by_locus[num] = label

    layers = []
    for i, layer in enumerate(data.get("layers") or []):
        num = str(layer.get("locusNumber", "")).strip()
        munsell = munsell_by_locus.get(num)
        if num and munsell:
            surface = f"Locus {num} ({munsell})"
        elif num:
            surface = f"Locus {num}"
            notes.append(f"locus {num} has no Munsell entry in loci[] — "
                         f"surface named without a color")
        else:
            surface = f"layer_{i}"
            notes.append(f"layer at index {i} has no locusNumber — "
                         f"named {surface!r}")

        bb = []
        for p in (layer.get("bottomBoundary") or []):
            bb.append({"xCoordinateMeters": get_x(p),
                       "depthMeters": p.get("depthMeters"),
                       "confidence": p.get("confidence")})
        layers.append({"layerName": surface,
                       "inferredMaterial": surface,
                       "bottomBoundary": bb})

    if not layers:
        notes.append("no layers[] in this field-wall extraction — nothing to convert")

    adapted = {"trenchProfiles": [{"face": fname, "layers": layers}]}
    return adapted, notes


def as_profiles(data):
    """Normalize either extraction shape to the trenchProfiles shape.
    Returns (data, notes)."""
    if is_field_wall(data):
        return fieldwall_to_profiles(data)
    return data, []


def make_starter_config(data):
    """Returns a starter grid-config dict with placeholder values per face.
    Accepts either extraction shape."""
    field_wall = is_field_wall(data)
    profiles, _ = as_profiles(data)

    cfg = {
        "_comment": "Fill in real site values. bearing_deg = compass direction "
                    "(clockwise from north) that the face's local +x axis points. "
                    "originX/Y = site coords of the face's x=0 edge. surfaceZ = "
                    "ground-surface elevation at that edge.",
        "faces": {},
    }
    for i, face in enumerate(profiles.get("trenchProfiles", [])):
        name = face.get("face") or f"face_{i}"
        cfg["faces"][name] = {
            "originX": 0.0 + i * 10.0,
            "originY": 0.0,
            "surfaceZ": 100.0,
            "bearing_deg": 90.0,
        }

    if field_wall:
        # The sheet's own tie-in labels are the likeliest source of these
        # numbers, but what they mean (northing / easting / elevation) is a
        # site-records question -- surface them verbatim, don't interpret.
        ties = [t.get("rawText") for t in (data.get("gridTiePoints") or [])
                if t.get("rawText")]
        cfg["_tiePointsFromSheet"] = ties
        cfg["_comment"] += (
            " This is a single-wall field sheet, so there is one face. The "
            "labels transcribed off the drawing are listed in "
            "_tiePointsFromSheet for reference — they are NOT interpreted "
            "here; confirm against site records which are northings, "
            "eastings or elevations before using them."
        )
    return cfg


def convert(data, grid, out_csv):
    """Returns (rows, orient, missing_faces, notes)."""
    profiles, notes = as_profiles(data)
    faces_cfg = grid.get("faces", {})
    rows = []
    orient = []
    missing = []

    for fi, face in enumerate(profiles.get("trenchProfiles", [])):
        fname = face.get("face") or f"face_{fi}"
        cfg = faces_cfg.get(fname)
        if cfg is None:
            missing.append(fname)
            continue
        X0, Y0 = cfg["originX"], cfg["originY"]
        Z0 = cfg["surfaceZ"]
        th = math.radians(cfg["bearing_deg"])
        sin_t, cos_t = math.sin(th), math.cos(th)

        def to_site(x, depth):
            X = X0 + x * sin_t
            Y = Y0 + x * cos_t
            Z = Z0 - depth
            return X, Y, Z

        for layer in (face.get("layers") or []):
            surface = layer.get("inferredMaterial") or layer.get("layerName") or "unknown"
            bb = layer.get("bottomBoundary") or []
            pts = [(get_x(p), get_y(p)) for p in bb]
            pts = [(x, d) for (x, d) in pts if isinstance(x, (int, float)) and isinstance(d, (int, float))]
            for x, d in pts:
                X, Y, Z = to_site(x, d)
                rows.append({"X": round(X, 4), "Y": round(Y, 4), "Z": round(Z, 4),
                             "surface": surface, "face": fname})
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

                orient.append({
                    "X": round(X, 4),
                    "Y": round(Y, 4),
                    "Z": round(Z, 4),
                    "surface": surface,
                    "face": fname,
                    "dip": round(dip, 2),
                    "azimuth": round(azimuth, 2),
                    "polarity": 1,
                }) 
            
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["X", "Y", "Z", "surface", "face"])
        w.writeheader()
        w.writerows(rows)
    orient_csv = out_csv.rsplit(".", 1)[0] + "_orientations.csv"
    with open(orient_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["X", "Y", "Z", "surface", "face", "dip", "azimuth", "polarity"])
        w.writeheader()
        w.writerows(orient)

    return rows, orient, missing, notes


def run_convert(data: dict, grid: dict, out_csv: str):
    rows, orient, missing, notes = convert(data, grid, out_csv)
    orient_csv = out_csv.rsplit(".", 1)[0] + "_orientations.csv"
    return {
        "points_csv": out_csv,
        "orientations_csv": orient_csv,
        "n_points": len(rows),
        "n_orientations": len(orient),
        "missing_faces": missing,
        "notes": notes,
        "source_shape": "field_wall" if is_field_wall(data) else "illustrator",
        "rows_preview": rows[:200],
    }
