"""
convert_coords.py — face-local (x, depth) -> site-wide (X, Y, Z) for GemPy.

Each trench face is drawn in its OWN local frame:
    x     = metres along the face from its left edge
    depth = metres downward from the ground surface (positive down)

Remember a trench is ONE PIT in the ground; each face is a WALL of that
same pit, not an independent slab. Real grid registration should place
adjacent faces so they meet at actual shared corners, tracing the pit's
true footprint (bearings generally turning corner to corner, e.g. ~90
degrees apart for a rectangular trench) -- not lined up arbitrarily.

GemPy needs true site coordinates (X, Y, Z). Converting requires knowing, per
face, where it sits in the site grid and which way it runs — the "grid
registration". That info comes from the site records (Jenna); it is NOT in the
drawing and is NOT something the LLM can infer.

This script reads:
    - an extraction JSON (output_clean.json)
    - a grid-config JSON mapping each face name -> its registration
and writes a flat table of interface points (and orientation seeds) in site
coordinates, ready for the GemPy step.

The math per point, given a face with origin (X0, Y0), surface elevation Z0,
and compass bearing theta (degrees, direction the face's +x axis points):
    X = X0 + x * sin(theta)
    Y = Y0 + x * cos(theta)
    Z = Z0 - depth
(bearing measured clockwise from north; x runs along the face, depth lowers Z.)

Usage:
    python convert_coords.py output_clean.json --grid grid_config.json --out points.csv
    # or, to emit a starter grid config to fill in:
    python convert_coords.py output_clean.json --make-config grid_config.json
"""

import argparse
import csv
import json
import math


def get_y(p):
    if p.get("yCoordinateMeters") is not None:
        return p["yCoordinateMeters"]
    return p.get("depthMeters")


def make_starter_config(data, path):
    """Emit a grid-config skeleton with placeholder values for each face."""
    cfg = {"_comment": "Fill in real site values. bearing_deg = compass direction "
                       "(clockwise from north) that the face's local +x axis points. "
                       "originX/Y = site coords of the face's x=0 edge. surfaceZ = "
                       "ground-surface elevation at that edge.",
           "faces": {}}
    for i, face in enumerate(data.get("trenchProfiles", [])):
        name = face.get("face") or f"face_{i}"
        cfg["faces"][name] = {
            "originX": 0.0 + i * 10.0,   # placeholder — spread faces apart
            "originY": 0.0,
            "surfaceZ": 100.0,           # placeholder surface elevation
            "bearing_deg": 90.0          # placeholder: +x points east
        }
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"wrote starter grid config -> {path}")
    print("Edit the placeholder values with real site registration, then run "
          "with --grid.")


def convert(data, grid, out_csv):
    faces_cfg = grid.get("faces", {})
    rows = []          # interface points
    orient = []        # orientation seeds (one per layer boundary, optional)
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
            # one crude orientation seed per boundary: use the average dip along x
            if len(pts) >= 2:
                # slope of depth vs x -> dip; azimuth from bearing
                xs = [p[0] for p in pts]; ds = [p[1] for p in pts]
                dz_dx = (ds[-1] - ds[0]) / (xs[-1] - xs[0]) if xs[-1] != xs[0] else 0.0
                dip = math.degrees(math.atan(dz_dx))
                midx = xs[len(xs)//2]; midd = ds[len(ds)//2]
                X, Y, Z = to_site(midx, midd)
                orient.append({"X": round(X,4), "Y": round(Y,4), "Z": round(Z,4),
                               "surface": surface, "face": fname,
                               "dip": round(abs(dip),2), "azimuth": round(cfg["bearing_deg"],2),
                               "polarity": 1})

    if missing:
        print(f"WARNING: no grid config for face(s): {', '.join(missing)} — skipped.")

    # write interface points
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["X","Y","Z","surface","face"])
        w.writeheader(); w.writerows(rows)
    # write orientations alongside
    orient_csv = out_csv.rsplit(".",1)[0] + "_orientations.csv"
    with open(orient_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["X","Y","Z","surface","face","dip","azimuth","polarity"])
        w.writeheader(); w.writerows(orient)

    print(f"wrote {len(rows)} interface points -> {out_csv}")
    print(f"wrote {len(orient)} orientation seeds -> {orient_csv}")
    return rows, orient


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--grid", help="grid-config JSON with per-face registration")
    ap.add_argument("--make-config", help="write a starter grid config to this path and exit")
    ap.add_argument("--out", default="points.csv")
    args = ap.parse_args()

    data = json.load(open(args.input))

    if args.make_config:
        make_starter_config(data, args.make_config)
        return
    if not args.grid:
        raise SystemExit("provide --grid grid_config.json (or --make-config to create one)")

    grid = json.load(open(args.grid))
    convert(data, grid, args.out)


if __name__ == "__main__":
    main()