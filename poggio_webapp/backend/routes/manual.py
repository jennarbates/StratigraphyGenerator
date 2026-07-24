"""Manual tracing routes.

The browser supplies calibration clicks, boundary polylines, and optional
feature polygons. This module converts pixels to metres deterministically and
installs a complete extraction JSON without CV, Gemini, or any other model.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import Blueprint, abort, jsonify, request

from ..jobs import job_dir, load_meta, rel_url, save_meta


bp = Blueprint("manual", __name__)


@dataclass(frozen=True)
class Calibration:
    origin_x: float
    origin_y: float
    ux: float
    uy: float
    vx: float
    vy: float
    px_per_m: float
    ref_x: float
    ref_y: float

    def convert(self, point: list[float] | tuple[float, float]) -> tuple[float, float]:
        px, py = float(point[0]), float(point[1])
        dx, dy = px - self.origin_x, py - self.origin_y
        x_m = (dx * self.ux + dy * self.uy) / self.px_per_m
        depth_m = (dx * self.vx + dy * self.vy) / self.px_per_m
        return round(x_m, 4), round(depth_m, 4)


def _point(value: Any, name: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{name} must be [pixel_x, pixel_y]")
    try:
        return float(value[0]), float(value[1])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain two numbers") from exc


def _make_calibration(payload: dict[str, Any]) -> Calibration:
    calibration = payload.get("calibration") or {}
    ox, oy = _point(calibration.get("origin_px"), "calibration.origin_px")
    rx, ry = _point(calibration.get("ref_px"), "calibration.ref_px")
    lx, ly = _point(calibration.get("lowest_px"), "calibration.lowest_px")

    try:
        ref_meters = float(calibration.get("ref_meters"))
    except (TypeError, ValueError) as exc:
        raise ValueError("calibration.ref_meters must be a number") from exc
    if ref_meters <= 0:
        raise ValueError("calibration.ref_meters must be greater than zero")

    dx, dy = rx - ox, ry - oy
    pixel_span = math.hypot(dx, dy)
    if pixel_span < 2:
        raise ValueError("the two top calibration points are too close together")

    ux, uy = dx / pixel_span, dy / pixel_span
    # One of the two perpendiculars points toward the user's lowest click.
    vx, vy = -uy, ux
    toward_lowest = (lx - ox) * vx + (ly - oy) * vy
    if toward_lowest < 0:
        vx, vy = -vx, -vy

    return Calibration(
        origin_x=ox,
        origin_y=oy,
        ux=ux,
        uy=uy,
        vx=vx,
        vy=vy,
        px_per_m=pixel_span / ref_meters,
        ref_x=rx,
        ref_y=ry,
    )


def _clean_polyline(raw: Any, label: str, minimum: int) -> list[list[float]]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} points must be a list")
    points: list[list[float]] = []
    for i, item in enumerate(raw):
        x, y = _point(item, f"{label} point {i + 1}")
        if not points or abs(points[-1][0] - x) > 0.01 or abs(points[-1][1] - y) > 0.01:
            points.append([x, y])
    if len(points) < minimum:
        raise ValueError(f"{label} needs at least {minimum} points")
    return points


def _converted_points(calib: Calibration, points: list[list[float]], fieldwall: bool) -> list[dict[str, Any]]:
    converted = [calib.convert(p) for p in points]
    converted.sort(key=lambda p: (p[0], p[1]))
    if fieldwall:
        return [
            {"xMeters": x, "depthMeters": max(0.0, depth), "confidence": "human-traced"}
            for x, depth in converted
        ]
    return [
        {"xCoordinateMeters": x, "yCoordinateMeters": max(0.0, depth),
         "confidence": "human-traced"}
        for x, depth in converted
    ]


def _xy(point: dict[str, Any]) -> tuple[float, float]:
    x = point.get("xMeters", point.get("xCoordinateMeters"))
    depth = point.get("depthMeters", point.get("yCoordinateMeters"))
    return float(x), float(depth)


def _average_depth(points: list[dict[str, Any]]) -> float:
    return sum(_xy(p)[1] for p in points) / len(points)


def _depth_at_x(points: list[dict[str, Any]], x: float) -> float:
    rows = sorted((_xy(p) for p in points), key=lambda p: p[0])
    if x <= rows[0][0]:
        return rows[0][1]
    if x >= rows[-1][0]:
        return rows[-1][1]
    for (x1, y1), (x2, y2) in zip(rows, rows[1:]):
        if x1 <= x <= x2:
            if abs(x2 - x1) < 1e-9:
                return (y1 + y2) / 2
            t = (x - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    return rows[-1][1]


def _feature_geometry(calib: Calibration, row: dict[str, Any], fieldwall: bool) -> dict[str, Any]:
    points_px = _clean_polyline(row.get("points"), "feature polygon", 3)
    converted = [calib.convert(p) for p in points_px]
    xs = [p[0] for p in converted]
    depths = [max(0.0, p[1]) for p in converted]
    center_x = sum(xs) / len(xs)
    center_depth = sum(depths) / len(depths)

    if fieldwall:
        shape = [
            {"xMeters": round(x, 4), "depthMeters": round(max(0.0, d), 4),
             "confidence": "human-traced"}
            for x, d in converted
        ]
    else:
        shape = [
            {"xCoordinateMeters": round(x, 4), "yCoordinateMeters": round(max(0.0, d), 4),
             "confidence": "human-traced"}
            for x, d in converted
        ]

    out = {
        "feature": str(row.get("feature_type") or "other feature").strip(),
        "description": str(row.get("description") or "").strip() or None,
        "shapePoints": shape,
        "approxXMeters": round(center_x, 4),
        "center_depth": round(center_depth, 4),
        "approxWidthMeters": round(max(xs) - min(xs), 4),
        "approxHeightMeters": round(max(depths) - min(depths), 4),
        "confidence": "human-traced",
    }
    if fieldwall:
        out["approxDepthMeters"] = round(center_depth, 4)
    else:
        out["approxYMeters"] = round(center_depth, 4)
    return out


def _assign_features(
    feature_rows: list[dict[str, Any]],
    layer_bands: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]],
) -> list[list[dict[str, Any]]]:
    assigned: list[list[dict[str, Any]]] = [[] for _ in layer_bands]
    for feature in feature_rows:
        x = feature["approxXMeters"]
        depth = feature.pop("center_depth")
        chosen = None
        best_distance = float("inf")
        for i, (top, bottom) in enumerate(layer_bands):
            top_depth = _depth_at_x(top, x)
            bottom_depth = _depth_at_x(bottom, x)
            low, high = sorted((top_depth, bottom_depth))
            if low - 0.02 <= depth <= high + 0.02:
                chosen = i
                break
            distance = min(abs(depth - low), abs(depth - high))
            if distance < best_distance:
                best_distance = distance
                chosen = i
        if chosen is not None:
            assigned[chosen].append(feature)
    return assigned


def _manual_boundaries(payload: dict[str, Any], calib: Calibration, fieldwall: bool):
    boundaries = payload.get("boundaries") or []
    if not isinstance(boundaries, list):
        raise ValueError("boundaries must be a list")

    surface = None
    bottoms = []
    warnings = []
    for i, boundary in enumerate(boundaries):
        kind = boundary.get("kind")
        if kind not in {"surface", "bottom"}:
            continue
        points_px = _clean_polyline(boundary.get("points"), f"boundary {i + 1}", 2)
        converted = _converted_points(calib, points_px, fieldwall)
        if kind == "surface":
            if surface is None:
                surface = converted
            else:
                warnings.append("More than one surface line was supplied; only the first was used.")
        else:
            name = str(boundary.get("name") or "").strip()
            if not name:
                raise ValueError(f"bottom boundary {i + 1} has no layer/locus name")
            bottoms.append({"name": name, "points": converted})

    if surface is None:
        # The calibration edge is a valid flat surface fallback.
        surface = _converted_points(
            calib,
            [[calib.origin_x, calib.origin_y], [calib.ref_x, calib.ref_y]],
            fieldwall,
        )
        warnings.append("No surface line was drawn, so the top calibration edge was used as the surface.")

    if not bottoms:
        raise ValueError("draw at least one bottom boundary")

    original_order = [b["name"] for b in bottoms]
    bottoms.sort(key=lambda b: _average_depth(b["points"]))
    if [b["name"] for b in bottoms] != original_order:
        warnings.append("Bottom boundaries were reordered from shallowest to deepest before building layers.")

    return surface, bottoms, warnings


def _build_fieldwall(payload: dict[str, Any], calib: Calibration, source_path: str | None):
    surface, bottoms, warnings = _manual_boundaries(payload, calib, fieldwall=True)
    loci_rows = payload.get("loci") or []
    loci_meta = {str(row.get("locusNumber", "")).strip(): row for row in loci_rows}

    bands = []
    top = surface
    for bottom in bottoms:
        bands.append((top, bottom["points"]))
        top = bottom["points"]

    feature_rows = [
        _feature_geometry(calib, row, fieldwall=True)
        for row in (payload.get("features") or [])
        if isinstance(row, dict) and len(row.get("points") or []) >= 3
    ]
    assigned = _assign_features(feature_rows, bands)

    layers = []
    loci = []
    for i, bottom in enumerate(bottoms):
        name = bottom["name"]
        info = loci_meta.get(name, {})
        munsell_raw = str(info.get("munsellRaw") or "").strip()
        description = str(info.get("description") or "").strip() or None
        loci.append({
            "locusNumber": name,
            "munsell": {"raw": munsell_raw, "colorName": None} if munsell_raw else None,
            "description": description,
            "confidence": "human-entered",
        })
        layers.append({
            "locusNumber": name,
            "topBoundary": bands[i][0],
            "bottomBoundary": bands[i][1],
            "featuresInLayer": assigned[i] or None,
        })

    data = {
        "trenchLabel": str(payload.get("trenchLabel") or "").strip() or None,
        "faceLabel": str(payload.get("faceLabel") or "").strip() or None,
        "illustrators": None,
        "date": None,
        "northArrowPresent": None,
        "gridSquareCm": payload.get("square_cm"),
        "gridTiePoints": [],
        "loci": loci,
        "layers": layers,
        "marginalia": [
            "Boundary and feature geometry was manually traced by a user.",
            f"Source image: {source_path}" if source_path else "Source image unavailable.",
        ],
    }
    return data, warnings


def _build_illustrator(payload: dict[str, Any], calib: Calibration, source_path: str | None):
    surface, bottoms, warnings = _manual_boundaries(payload, calib, fieldwall=False)
    layer_info = payload.get("layerInfo") or {}

    bands = []
    top = surface
    for bottom in bottoms:
        bands.append((top, bottom["points"]))
        top = bottom["points"]

    feature_rows = [
        _feature_geometry(calib, row, fieldwall=False)
        for row in (payload.get("features") or [])
        if isinstance(row, dict) and len(row.get("points") or []) >= 3
    ]
    assigned = _assign_features(feature_rows, bands)

    layers = []
    for i, bottom in enumerate(bottoms):
        name = bottom["name"]
        info = layer_info.get(name) or {}
        material = str(info.get("inferredMaterial") or "").strip() or name
        description = str(info.get("description") or "").strip() or None
        layers.append({
            "layerName": name,
            "inferredMaterial": material,
            "description": description,
            "visualPattern": None,
            "featuresInLayer": assigned[i] or None,
            "topBoundary": bands[i][0],
            "bottomBoundary": bands[i][1],
        })

    face = (str(payload.get("faceLabel") or "").strip()
            or str(payload.get("trenchLabel") or "").strip()
            or "manual trace")
    data = {
        "metadata": {
            "currentFilePath": source_path,
            "suggestedFilename": None,
            "trenchLabel": str(payload.get("trenchLabel") or "").strip() or None,
            "scale": {
                "unit": "m",
                "valuesMarked": [],
                "metricConversionAssumption": "Manual calibration from two user-selected reference points.",
                "confidence": "human-confirmed",
            },
            "credits": None,
            "marginalia": ["Boundary and feature geometry was manually traced by a user."],
        },
        "trenchProfiles": [{
            "face": face,
            "gridLabels": None,
            "gridLabelXMeters": None,
            "layers": layers,
        }],
        "legend": None,
        "inferred_notes": ["No model generated or altered the traced geometry."],
        "rawTranscription": None,
    }
    return data, warnings


@bp.route("/api/jobs/<job_id>/boundaries/manual", methods=["POST"])
def build_manual_extraction(job_id):
    meta = load_meta(job_id)
    if not meta.get("scan_path"):
        abort(400, description="upload a scan first")

    payload = request.get_json(force=True, silent=True) or {}
    try:
        calib = _make_calibration(payload)
        fieldwall = meta.get("sheet_type") == "fieldwall"
        image_kind = payload.get("image")
        if image_kind == "clean" and meta.get("clean_image_path"):
            source_path = meta["clean_image_path"]
        elif image_kind == "rotated":
            rotated = job_dir(job_id) / "03_extraction" / "marker_source_rotated.png"
            source_path = str(rotated) if rotated.exists() else meta.get("scan_path")
        else:
            source_path = meta.get("scan_path")
        if fieldwall:
            data, warnings = _build_fieldwall(payload, calib, source_path)
            filename = "field_wall_manual.json"
        else:
            data, warnings = _build_illustrator(payload, calib, source_path)
            filename = "illustrator_manual.json"
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    out_dir = job_dir(job_id) / "03_extraction"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    raw = json.dumps(data, indent=2)
    out_path.write_text(raw)

    meta["extraction_path"] = str(out_path)
    meta["manual_image_path"] = source_path
    meta["manual_calibration"] = {
        "origin_px": payload["calibration"]["origin_px"],
        "ref_px": payload["calibration"]["ref_px"],
        "lowest_px": payload["calibration"]["lowest_px"],
        "ref_meters": payload["calibration"]["ref_meters"],
        "px_per_m": round(calib.px_per_m, 6),
    }
    meta.pop("normalized_path", None)
    save_meta(job_id, meta)

    return jsonify({
        "raw_json": raw,
        "warnings": warnings,
        "file_url": rel_url(job_id, Path(out_path)),
        "px_per_m": round(calib.px_per_m, 3),
        "n_boundaries": len(payload.get("boundaries") or []),
        "n_features": len(payload.get("features") or []),
    })
