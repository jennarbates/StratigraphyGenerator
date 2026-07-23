"""
convert_coords.py — face-local (x, depth) -> site-wide (X, Y, Z) for GemPy.
Adapted from 05_convert_coords/convertCoords.py into importable functions.
Logic unchanged.
"""

import csv
import math


def get_y(p):
    if p.get("yCoordinateMeters") is not None:
        return p["yCoordinateMeters"]
    return p.get("depthMeters")


def make_starter_config(data):
    """Returns a starter grid-config dict with placeholder values per face."""
    cfg = {
        "_comment": "Fill in real site values. bearing_deg = compass direction "
                    "(clockwise from north) that the face's local +x axis points. "
                    "originX/Y = site coords of the face's x=0 edge. surfaceZ = "
                    "ground-surface elevation at that edge.",
        "faces": {},
    }
    for i, face in enumerate(data.get("trenchProfiles", [])):
        name = face.get("face") or f"face_{i}"
        cfg["faces"][name] = {
            "originX": 0.0 + i * 10.0,
            "originY": 0.0,
            "surfaceZ": 100.0,
            "bearing_deg": 90.0,
        }
    return cfg


def convert(data, grid, out_csv):
    """Returns (rows, orient, missing_faces)."""
    faces_cfg = grid.get("faces", {})
    rows = []
    orient = []
    missing = []

    for fi, face in enumerate(data.get("trenchProfiles", [])):
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
            pts = [(p.get("xCoordinateMeters"), get_y(p)) for p in bb]
            pts = [(x, d) for (x, d) in pts if isinstance(x, (int, float)) and isinstance(d, (int, float))]
            for x, d in pts:
                X, Y, Z = to_site(x, d)
                rows.append({"X": round(X, 4), "Y": round(Y, 4), "Z": round(Z, 4),
                             "surface": surface, "face": fname})
            if len(pts) >= 2:
                xs = [p[0] for p in pts]
                ds = [p[1] for p in pts]
                dz_dx = (ds[-1] - ds[0]) / (xs[-1] - xs[0]) if xs[-1] != xs[0] else 0.0
                dip = math.degrees(math.atan(dz_dx))
                midx = xs[len(xs) // 2]
                midd = ds[len(ds) // 2]
                X, Y, Z = to_site(midx, midd)
                orient.append({"X": round(X, 4), "Y": round(Y, 4), "Z": round(Z, 4),
                               "surface": surface, "face": fname,
                               "dip": round(abs(dip), 2), "azimuth": round(cfg["bearing_deg"], 2),
                               "polarity": 1})

    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["X", "Y", "Z", "surface", "face"])
        w.writeheader()
        w.writerows(rows)
    orient_csv = out_csv.rsplit(".", 1)[0] + "_orientations.csv"
    with open(orient_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["X", "Y", "Z", "surface", "face", "dip", "azimuth", "polarity"])
        w.writeheader()
        w.writerows(orient)

    return rows, orient, missing


def run_convert(data: dict, grid: dict, out_csv: str):
    rows, orient, missing = convert(data, grid, out_csv)
    orient_csv = out_csv.rsplit(".", 1)[0] + "_orientations.csv"
    return {
        "points_csv": out_csv,
        "orientations_csv": orient_csv,
        "n_points": len(rows),
        "n_orientations": len(orient),
        "missing_faces": missing,
        "rows_preview": rows[:200],
    }
