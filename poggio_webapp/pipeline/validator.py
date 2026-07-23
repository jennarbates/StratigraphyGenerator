"""
validator.py — sanity-checks the trench-extraction JSON before it feeds GemPy.
Adapted from 04_normalize_validate/validator.py into an importable function
returning structured results instead of printing + exit code. Logic unchanged.
"""

import json
from dataclasses import dataclass, field

DEFAULT_MONOTONIC_TOLERANCE_M = 0.02
DEFAULT_TOP_CONTINUITY_TOLERANCE_M = 0.10
DEFAULT_MAX_PLAUSIBLE_DEPTH_M = 5.0


@dataclass
class Report:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def err(self, where, msg):
        self.errors.append(f"[ERROR] {where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"[WARN]  {where}: {msg}")


def get_y(point):
    if point is None:
        return None
    if point.get("yCoordinateMeters") is not None:
        return point.get("yCoordinateMeters")
    return point.get("depthMeters")


def get_x(point):
    if point is None:
        return None
    return point.get("xCoordinateMeters")


def is_null_string(v):
    return isinstance(v, str) and v.strip().lower() in ("null", "none", "n/a")


def scan_null_strings(obj, path, report):
    if isinstance(obj, dict):
        for k, v in obj.items():
            scan_null_strings(v, f"{path}.{k}", report)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            scan_null_strings(v, f"{path}[{i}]", report)
    elif is_null_string(obj):
        report.warn(path, f'literal string "{obj}" — should this be a real null?')


def check_boundary(points, where, report, max_plausible_depth_m):
    cleaned = []
    if points is None:
        return cleaned
    for i, p in enumerate(points):
        x, y = get_x(p), get_y(p)
        conf = p.get("confidence")
        if (x is None or y is None) and not conf:
            report.err(f"{where}[{i}]",
                       "null coordinate with no confidence note explaining why")
        if y is not None and y < 0:
            report.err(f"{where}[{i}]", f"negative depth {y} (depth is positive-down)")
        if y is not None and y > max_plausible_depth_m:
            report.warn(f"{where}[{i}]", f"implausibly deep ({y} m)")
        if x is not None and y is not None:
            cleaned.append((x, y))
    xs = [x for x, _ in cleaned]
    if xs != sorted(xs):
        report.warn(where, f"x-coordinates not left-to-right: {xs}")
    return cleaned


def depth_at_x(boundary_pairs, x):
    if not boundary_pairs:
        return None
    pts = sorted(boundary_pairs)
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return None


def check_features(layer, top, bottom, where, report, monotonic_tolerance_m):
    feats = layer.get("featuresInLayer")
    if not feats:
        return
    top_min = min((y for _, y in top), default=None)
    bot_max = max((y for _, y in bottom), default=None)

    for fi, feat in enumerate(feats):
        fname = feat.get("feature") or f"feature {fi}"
        fwhere = f"{where} / {fname}"
        sp = feat.get("shapePoints")
        has_shape = bool(sp)
        has_approx = any(
            feat.get(k) is not None
            for k in ("approxXMeters", "approxYMeters",
                      "approxWidthMeters", "approxHeightMeters"))

        if not has_shape and not has_approx:
            report.warn(
                fwhere,
                "no shapePoints and no approx* coords — geometry may be "
                "trapped in the description string")

        if has_shape and top_min is not None and bot_max is not None:
            for pi, p in enumerate(sp):
                y = get_y(p)
                if y is None:
                    continue
                if y < top_min - monotonic_tolerance_m or y > bot_max + monotonic_tolerance_m:
                    report.warn(
                        f"{fwhere}[{pi}]",
                        f"point depth {y:.2f} lies outside layer band "
                        f"[{top_min:.2f}, {bot_max:.2f}]")


def check_face(face, report, monotonic_tolerance_m, top_continuity_tolerance_m,
               max_plausible_depth_m):
    fname = face.get("face") or "UNNAMED FACE"
    layers = face.get("layers") or []
    if not layers:
        report.warn(fname, "no layers")
        return

    prev_bottom = None
    prev_name = None

    for li, layer in enumerate(layers):
        lname = layer.get("layerName") or f"layer {li}"
        where = f"{fname} / {lname}"

        top = check_boundary(layer.get("topBoundary"), f"{where} top", report,
                              max_plausible_depth_m)
        bottom = check_boundary(layer.get("bottomBoundary"), f"{where} bottom", report,
                                 max_plausible_depth_m)

        if prev_bottom and top:
            for x, y in top:
                above = depth_at_x(prev_bottom, x)
                if above is not None and abs(y - above) > top_continuity_tolerance_m:
                    report.warn(
                        where,
                        f"top at x={x} (depth {y:.2f}) is far from "
                        f"{prev_name} bottom (depth {above:.2f}) — "
                        f"possible void/overlap")

        if prev_bottom and bottom:
            for x, y in bottom:
                above = depth_at_x(prev_bottom, x)
                if above is not None and y < above - monotonic_tolerance_m:
                    report.err(
                        where,
                        f"bottom at x={x} (depth {y:.2f}) is ABOVE "
                        f"{prev_name}'s bottom (depth {above:.2f}) — layers cross")

        check_features(layer, top, bottom, where, report, monotonic_tolerance_m)

        if bottom:
            prev_bottom = bottom
            prev_name = lname


def validate(data, monotonic_tolerance_m=DEFAULT_MONOTONIC_TOLERANCE_M,
             top_continuity_tolerance_m=DEFAULT_TOP_CONTINUITY_TOLERANCE_M,
             max_plausible_depth_m=DEFAULT_MAX_PLAUSIBLE_DEPTH_M):
    report = Report()

    scan_null_strings(data, "root", report)

    profiles = data.get("trenchProfiles")
    if not profiles:
        report.err("root", "no trenchProfiles")
        return report

    for face in profiles:
        gx = face.get("gridLabelXMeters")
        gl = face.get("gridLabels")
        if gl and gx and len(gl) != len(gx):
            report.warn(
                face.get("face") or "face",
                f"gridLabels ({len(gl)}) and gridLabelXMeters ({len(gx)}) "
                "differ in length")
        check_face(face, report, monotonic_tolerance_m, top_continuity_tolerance_m,
                   max_plausible_depth_m)

    return report


def run_validate(input_path: str, monotonic_tolerance=DEFAULT_MONOTONIC_TOLERANCE_M,
                  top_continuity_tolerance=DEFAULT_TOP_CONTINUITY_TOLERANCE_M,
                  max_depth=DEFAULT_MAX_PLAUSIBLE_DEPTH_M):
    """Returns a dict: {errors: [...], warnings: [...], ok: bool}"""
    data = json.load(open(input_path))
    report = validate(data, monotonic_tolerance, top_continuity_tolerance, max_depth)
    return {
        "errors": report.errors,
        "warnings": report.warnings,
        "ok": len(report.errors) == 0,
    }
