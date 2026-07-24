"""
detectFieldWallMarkers.py — find the artist's actual circle-marked vertex
points on a field-wall photo (like T104's), computationally, instead of
asking an LLM to invent boundary coordinates.

Why this exists
================
extractFieldWall.py asked Gemini to report boundary points directly, twice,
and both times it produced geometrically fabricated results (perfectly even
spacing, identical patterns copy-pasted across loci) instead of actually
reading the drawn line. The recorder's convention on this sheet is: measure
each vertex, mark it with a small circle/dot, connect the dots with a
straightedge. That means the real vertex positions are a computer-vision
problem (find small circular marks), not a freeform-tracing problem — and
CV can't fabricate a point that isn't there the way an LLM can.

This script does NOT figure out which locus/boundary each marker belongs
to — that's a separate, still-open step (see bottom of file). It only
finds markers and converts pixel -> real meters.

Coordinate convention (matches extractFieldWall.py / convertCoords.py):
    x     = horizontal position along the face, meters, 0 at the wall's
            left edge.
    depth = downward from the ground surface, meters, positive down.

Usage:
    python detectFieldWallMarkers.py T104_southern_baulk_wall.jpeg \\
        --rotate 90 \\
        --square-cm 20 \\
        --origin-px 1148 823 \\
        --out markers.csv \\
        --debug-image markers_debug.png

--rotate matches how the source photo needs turning to be right-side-up
(T104_southern_baulk_wall.jpeg as stored is sideways — needs --rotate 90).
This script always reads the image with EXIF auto-rotation explicitly
DISABLED (cv2.IMREAD_IGNORE_ORIENTATION), because some OpenCV builds apply
EXIF rotation automatically and some don't — without forcing this off,
--rotate's meaning would depend on whose machine runs the script. All
other pixel-based arguments refer to the ALREADY-ROTATED frame.

--origin-px is the PIXEL coordinate of the wall's top-left corner
(x=0, depth=0) in the (possibly rotated) source photo. Read it off by
hovering in any image viewer — automated corner detection on this photo
was unreliable (the drawn box border fragments under contour/line
detection, competing with the grid and the profile ink itself), so this
script asks for it once rather than guessing.

Always inspect --debug-image before trusting the CSV: it draws every
accepted marker as a circle and every size/shape-rejected candidate in a
different color, over the original photo, so false positives (grid
intersections, stray dots in handwriting, letter "o"s) are visible at a
glance rather than silently baked into the numbers.
"""

import argparse
import csv
import math

import cv2
import numpy as np


def find_grid_px_per_cm(gray, redness, sample_box, square_cm):
    """Re-derive px/cm from the red grid spacing in a clean (blank) patch
    of the sheet, the same way this was done interactively for T104:
    minor grid lines ~10 per bold square, bold spacing measured from
    column-sum peaks of 'redness'."""
    y0, y1, x0, x1 = sample_box
    strip = redness[y0:y1, x0:x1]
    colsum = strip.sum(axis=0)
    colsum = colsum - colsum.min()
    from scipy.signal import find_peaks
    peaks, props = find_peaks(colsum, height=colsum.max() * 0.3, distance=5)
    heights = props["peak_heights"]
    bold = [p for p, h in zip(peaks, heights) if h > np.median(heights) * 1.3]
    if len(bold) < 2:
        raise SystemExit(
            "Couldn't find at least 2 bold grid lines in --grid-sample-box "
            "to measure spacing — pick a cleaner blank patch of the grid "
            "(no ink/text) via --grid-sample-box y0 y1 x0 x1.")
    bold_spacing_px = float(np.mean(np.diff(bold)))
    return bold_spacing_px / square_cm


def isolate_ink(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    b, g, r = cv2.split(img.astype(np.int32))
    redness = r - (g + b) / 2.0
    ink_mask = ((gray < 130) & (redness < 25)).astype(np.uint8) * 255
    return gray, redness, ink_mask


def find_circle_markers(ink_mask, min_diam_px, max_diam_px, min_circularity=0.55):
    contours, _ = cv2.findContours(ink_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    accepted, rejected = [], []
    for c in contours:
        area = cv2.contourArea(c)
        perim = cv2.arcLength(c, True)
        if area <= 0 or perim <= 0:
            continue
        (cx, cy), radius = cv2.minEnclosingCircle(c)
        diam = radius * 2
        circularity = 4 * math.pi * area / (perim ** 2)
        entry = {"cx": cx, "cy": cy, "diam": diam, "circularity": circularity,
                 "area": area}
        if min_diam_px <= diam <= max_diam_px and circularity >= min_circularity:
            accepted.append(entry)
        else:
            rejected.append(entry)
    return accepted, rejected


def draw_debug_image(img, accepted, rejected, origin_px, px_per_cm, path):
    dbg = img.copy()
    for e in rejected:
        cv2.circle(dbg, (int(e["cx"]), int(e["cy"])), max(int(e["diam"] / 2), 3),
                    (0, 0, 255), 2)   # red = rejected
    for e in accepted:
        cv2.circle(dbg, (int(e["cx"]), int(e["cy"])), max(int(e["diam"] / 2), 3),
                    (0, 255, 0), 3)   # green = accepted marker
    ox, oy = origin_px
    cv2.drawMarker(dbg, (int(ox), int(oy)), (255, 0, 255),
                    markerType=cv2.MARKER_CROSS, markerSize=40, thickness=4)
    cv2.imwrite(path, dbg)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--square-cm", type=float, required=True,
                    help="real-world size of one BOLD grid square, in cm")
    ap.add_argument("--origin-px", type=float, nargs=2, metavar=("X", "Y"),
                    required=True,
                    help="pixel coords of the wall's x=0/depth=0 corner "
                         "(top-left of the drawn box), read off by eye in "
                         "an image viewer")
    ap.add_argument("--grid-sample-box", type=int, nargs=4,
                    metavar=("Y0", "Y1", "X0", "X1"), default=None,
                    help="a clean/blank patch of grid (no ink) used to "
                         "re-measure px/cm; defaults to a patch near the "
                         "image's top-left corner if not given")
    ap.add_argument("--min-marker-cm", type=float, default=0.15,
                    help="smallest real diameter (cm) counted as a vertex "
                         "marker, not noise (default 0.15)")
    ap.add_argument("--max-marker-cm", type=float, default=0.6,
                    help="largest real diameter (cm) counted as a vertex "
                         "marker before it's probably a stone/letter "
                         "instead (default 0.6)")
    ap.add_argument("--out", default="markers.csv")
    ap.add_argument("--debug-image", default="markers_debug.png")
    ap.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=0,
                     help="degrees to rotate the source photo clockwise "
                          "before processing, e.g. 90 if it was shot "
                          "sideways (default 0). All other arguments "
                          "(--origin-px, --grid-sample-box) refer to pixel "
                          "coordinates AFTER this rotation is applied.")
    args = ap.parse_args()

    img = cv2.imread(args.image, cv2.IMREAD_IGNORE_ORIENTATION | cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"could not read {args.image}")
    if args.rotate == 90:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif args.rotate == 180:
        img = cv2.rotate(img, cv2.ROTATE_180)
    elif args.rotate == 270:
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    gray, redness, ink_mask = isolate_ink(img)

    h, w = gray.shape
    sample_box = args.grid_sample_box or (100, 400, 100, 1200)
    px_per_cm = find_grid_px_per_cm(gray, redness, sample_box, args.square_cm)
    print(f"measured scale: {px_per_cm:.3f} px/cm")

    min_diam_px = args.min_marker_cm * px_per_cm
    max_diam_px = args.max_marker_cm * px_per_cm
    accepted, rejected = find_circle_markers(ink_mask, min_diam_px, max_diam_px)
    print(f"found {len(accepted)} candidate markers "
          f"({len(rejected)} shapes rejected by size/circularity)")

    ox, oy = args.origin_px
    rows = []
    for e in accepted:
        x_m = (e["cx"] - ox) / px_per_cm / 100.0
        depth_m = (e["cy"] - oy) / px_per_cm / 100.0
        rows.append({
            "pixel_x": round(e["cx"], 1), "pixel_y": round(e["cy"], 1),
            "x_m": round(x_m, 3), "depth_m": round(depth_m, 3),
            "diam_px": round(e["diam"], 1),
            "circularity": round(e["circularity"], 3),
        })
    rows.sort(key=lambda r: r["x_m"])

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                                 ["pixel_x", "pixel_y", "x_m", "depth_m",
                                  "diam_px", "circularity"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.out}")

    draw_debug_image(img, accepted, rejected, args.origin_px, px_per_cm,
                      args.debug_image)
    print(f"wrote {args.debug_image} — ALWAYS check this before trusting "
          f"{args.out}. Green circles = accepted markers, red = rejected "
          f"candidates, magenta cross = the origin you gave.")
    print("\nNOTE: this only finds marker points, it does not know which "
          "locus/boundary each one belongs to. That assignment step is "
          "still open — see the file's module docstring.")


if __name__ == "__main__":
    main()

# ============================================================
# STILL OPEN: assigning markers to a locus/boundary
# ============================================================
# This script finds every circle-marker-shaped thing in the ink layer, in
# no particular grouping — locus boundaries, stray dots in handwriting,
# and any letter "o"s that survive the circularity filter all come out the
# same way. What it does NOT do is know that, say, markers at
# (0.10, 0.14), (0.32, 0.15), (0.58, 0.13)... belong to Locus 3's top
# boundary specifically.
#
# Two ways to close that gap, roughly in order of how much to trust them:
#   1. Manual: open markers_debug.png next to the original photo and
#      group markers by eye, boundary by boundary. Slow but has zero
#      fabrication risk.
#   2. Semi-automated: feed Gemini the ORIGINAL photo plus this script's
#      already-detected pixel/meter coordinates (not asking it to invent
#      new ones), and ask it only to assign each given point to a locus
#      and top/final-base role. This is a classification task over real,
#      fixed points rather than a coordinate-generation task, which is
#      exactly the part of the previous approach that kept fabricating —
#      worth trying, but verify the assignments the same way the
#      coordinates themselves needed verifying.
