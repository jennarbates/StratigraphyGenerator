"""
detect_markers.py — importable adaptation of tools/detectFieldWallMarkers.py
for the web GUI.

Finds the recorder's circle-marked vertex points on a field-wall photo with
computer vision instead of asking an LLM to trace boundaries — CV cannot
fabricate a marker that isn't on the paper, which is exactly the failure
mode Gemini tracing runs on T104-style sheets kept exhibiting (perfectly
even spacing, layers copy-pasted with a constant offset).

Differences from the CLI tool, tuned on the real T104 photo:
- ADAPTIVE thresholding for ink isolation (a fixed gray<130 threshold
  fragments light pencil and breaks under phone-photo lighting)
- morphological OPENING before the circle hunt, so vertex dots that touch
  their boundary line survive as blobs instead of merging into one big
  non-circular contour and being lost
- scale from TWO user clicks (wall's top-left and top-right corners) plus
  the real distance between them read off the sheet's own tie labels
  (e.g. 194 m ... 190 m -> 4.0) — grid-line measurement proved fragile on
  phone photos (perspective, table background, line-edge harmonics)
- candidates restricted to the wall box (the two clicks plus a third on
  the wall's lowest point), which drops handwriting, the legend, and the
  table from consideration
- solidity/fill filters + dedupe: dots are small FILLED disks; stone
  outlines and nested contour duplicates are not

Marker size limits are given in PAPER millimeters (how big the pencil dot
is on the sheet) and converted through square_cm, assuming one bold grid
square is 1 cm of paper — standard for mm graph paper.

Coordinate convention (matches extract_fieldwall.py / convert_coords.py):
    x_m     = horizontal position along the face, meters, 0 at the origin
    depth_m = downward from the origin, meters, positive down
"""

import csv
import math
import os

import cv2
import numpy as np


def load_rotated(image_path, rotate=0):
    """Read the photo with EXIF auto-rotation explicitly DISABLED (so
    `rotate` means the same thing on every machine) and apply the requested
    clockwise rotation."""
    img = cv2.imread(image_path, cv2.IMREAD_IGNORE_ORIENTATION | cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"could not read image: {image_path}")
    if rotate == 90:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif rotate == 180:
        img = cv2.rotate(img, cv2.ROTATE_180)
    elif rotate == 270:
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif rotate != 0:
        raise RuntimeError("rotate must be one of 0, 90, 180, 270")
    return img


def write_rotated_preview(image_path, rotate, out_path):
    """Write the rotated working copy the user picks reference points on.
    Returns (width, height) of the rotated frame."""
    img = load_rotated(image_path, rotate)
    cv2.imwrite(out_path, img)
    h, w = img.shape[:2]
    return w, h


def _ink_mask(img, block_px, C=10):
    """Dark-and-not-red ink, adaptively thresholded so light pencil and
    uneven phone-photo lighting don't fragment the strokes."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    b, g, r = cv2.split(img.astype(np.int32))
    redness = r - (g + b) / 2.0
    ad = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY_INV, block_px, C)
    return cv2.bitwise_and(ad, (redness < 25).astype(np.uint8) * 255)


def run_detect(image_path, origin_px, ref_px, ref_meters, bottom_px_y,
               square_cm, out_dir, rotate=0,
               min_marker_paper_mm=0.5, max_marker_paper_mm=2.5,
               line_kill_paper_mm=0.35, min_circularity=0.65,
               min_solidity=0.9, box_margin_paper_mm=2.0):
    """Detect circle markers inside the wall box.

    origin_px    : (x, y) pixel of the wall's top-LEFT corner (x=0/depth=0),
                   in the ROTATED frame — where the user clicked.
    ref_px       : (x, y) pixel of the wall's top-RIGHT corner, same frame.
    ref_meters   : real distance between those two clicks, read from the
                   sheet's tie labels (e.g. 194 m ... 190 m -> 4.0).
    bottom_px_y  : pixel y of the wall's LOWEST point (third click) — the
                   bottom of the search box.
    square_cm    : real-world cm per bold (1 cm paper) grid square — used
                   only to convert paper-mm size limits into pixels.

    Returns a dict with the marker list (pixel + meter coordinates), counts,
    the measured scale, and the paths of the rotated working image, debug
    overlay, and CSV written into out_dir.
    """
    if not ref_meters or float(ref_meters) <= 0:
        raise RuntimeError("ref_meters must be a positive real distance")
    os.makedirs(out_dir, exist_ok=True)
    img = load_rotated(image_path, rotate)
    rotated_path = os.path.join(out_dir, "marker_source_rotated.png")
    cv2.imwrite(rotated_path, img)

    ox, oy = float(origin_px[0]), float(origin_px[1])
    rx, ry = float(ref_px[0]), float(ref_px[1])
    ref_dist_px = math.hypot(rx - ox, ry - oy)
    if ref_dist_px < 20:
        raise RuntimeError("the top-left and top-right clicks are almost the "
                           "same pixel — click the wall's two top corners")
    px_per_m = ref_dist_px / float(ref_meters)
    mm_px = px_per_m * float(square_cm) / 1000.0   # px per paper millimeter
    if mm_px < 2:
        raise RuntimeError("photo resolution too low for marker detection "
                           f"({mm_px:.1f} px per paper mm) — retake closer or "
                           "at higher resolution")

    ink = _ink_mask(img, block_px=max(11, int(2.0 * mm_px) | 1))
    k = max(3, int(line_kill_paper_mm * mm_px) | 1)
    opened = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))

    margin = box_margin_paper_mm * mm_px
    x_lo, x_hi = min(ox, rx) - margin, max(ox, rx) + margin
    y_lo = min(oy, ry) - margin
    y_hi = float(bottom_px_y) + margin
    if y_hi <= y_lo + 20:
        raise RuntimeError("the bottom click is above the wall's top edge — "
                           "click the lowest point of the drawn wall")

    min_d, max_d = min_marker_paper_mm * mm_px, max_marker_paper_mm * mm_px
    contours, _ = cv2.findContours(opened, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cand, rejected = [], []
    for c in contours:
        area = cv2.contourArea(c)
        perim = cv2.arcLength(c, True)
        if area <= 0 or perim <= 0:
            continue
        (cx, cy), radius = cv2.minEnclosingCircle(c)
        diam = radius * 2
        entry = {"cx": float(cx), "cy": float(cy), "diam": float(diam)}
        if not (x_lo <= cx <= x_hi and y_lo <= cy <= y_hi):
            continue                       # outside the wall: not even shown
        circularity = 4 * math.pi * area / (perim ** 2)
        hull_area = cv2.contourArea(cv2.convexHull(c))
        solidity = area / hull_area if hull_area > 0 else 0
        fill = area / (math.pi * radius * radius) if radius > 0 else 0
        entry["circularity"] = float(circularity)
        if (min_d <= diam <= max_d and circularity >= min_circularity
                and solidity >= min_solidity and fill >= 0.5):
            cand.append(entry)
        else:
            rejected.append(entry)

    # nested-contour duplicates: keep the largest of any cluster closer
    # together than half a minimum dot
    cand.sort(key=lambda e: -e["diam"])
    kept = []
    for e in cand:
        if all((e["cx"] - k2["cx"]) ** 2 + (e["cy"] - k2["cy"]) ** 2
               > (0.5 * min_d) ** 2 for k2 in kept):
            kept.append(e)

    markers = []
    for i, e in enumerate(sorted(kept, key=lambda e: e["cx"])):
        markers.append({
            "id": i,
            "pixel_x": round(e["cx"], 1), "pixel_y": round(e["cy"], 1),
            "x_m": round((e["cx"] - ox) / px_per_m, 3),
            "depth_m": round((e["cy"] - oy) / px_per_m, 3),
            "diam_px": round(e["diam"], 1),
            "circularity": round(e["circularity"], 3),
        })

    dbg = img.copy()
    for e in rejected:
        cv2.circle(dbg, (int(e["cx"]), int(e["cy"])),
                   max(int(e["diam"] / 2), 3), (0, 0, 255), 2)
    for m in markers:
        cv2.circle(dbg, (int(m["pixel_x"]), int(m["pixel_y"])),
                   max(int(m["diam_px"] / 2), 4), (0, 255, 0), 4)
    cv2.rectangle(dbg, (int(x_lo), int(y_lo)), (int(x_hi), int(y_hi)),
                  (255, 0, 255), 4)
    cv2.drawMarker(dbg, (int(ox), int(oy)), (255, 0, 255),
                   markerType=cv2.MARKER_CROSS, markerSize=60, thickness=6)
    cv2.drawMarker(dbg, (int(rx), int(ry)), (255, 160, 0),
                   markerType=cv2.MARKER_CROSS, markerSize=60, thickness=6)
    debug_path = os.path.join(out_dir, "markers_debug.png")
    cv2.imwrite(debug_path, dbg)

    csv_path = os.path.join(out_dir, "markers.csv")
    fields = ["id", "pixel_x", "pixel_y", "x_m", "depth_m", "diam_px", "circularity"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(markers)

    return {
        "markers": markers,
        "n_accepted": len(markers),
        "n_rejected_in_box": len(rejected),
        "px_per_m": round(px_per_m, 2),
        "px_per_paper_mm": round(mm_px, 2),
        "rotated_image": rotated_path,
        "debug_image": debug_path,
        "csv": csv_path,
    }