"""
validate.py — sanity-checks the trench-extraction JSON before it feeds GemPy.

Usage:
    python validate.py path/to/output.json

Exit code 0 = no errors (warnings allowed), 1 = at least one error.

Severity:
    ERROR   — will corrupt the GemPy model or indicates a broken extraction.
    WARNING — suspicious, worth a human look, but not necessarily wrong.

The validator is intentionally schema-tolerant: it accepts either
`yCoordinateMeters` or `depthMeters` for the vertical axis, so it works whether
or not you've finished the depth-rename. It never mutates the data.
"""

import json
import sys
from dataclasses import dataclass, field


# ---- config knobs --------------------------------------------------------
# How much a lower layer's boundary may sit ABOVE the layer above it (in
# meters) before we call it a crossing. Hand-drawn lines wobble, so a tiny
# tolerance avoids false alarms.
MONOTONIC_TOLERANCE_M = 0.02
# Max plausible depth (m). Anything beyond is flagged as a likely mis-read.
MAX_PLAUSIBLE_DEPTH_M = 5.0


@dataclass
class Report:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def err(self, where, msg):
        self.errors.append(f"[ERROR] {where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"[WARN]  {where}: {msg}")


# ---- helpers -------------------------------------------------------------

def get_y(point):
    """Vertical value, tolerant of both field names. None if absent/null."""
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
    """Catch the '"null"' string bug (a real null typed as the word)."""
    return isinstance(v, str) and v.strip().lower() in ("null", "none", "n/a")


def scan_null_strings(obj, path, report):
    """Recursively flag any value that is the literal string 'null'."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            scan_null_strings(v, f"{path}.{k}", report)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            scan_null_strings(v, f"{path}[{i}]", report)
    elif is_null_string(obj):
        report.warn(path, f'literal string "{obj}" — should this be a real null?')


# ---- per-boundary checks -------------------------------------------------

def check_boundary(points, where, report):
    """Validate a single boundary point list. Returns cleaned (x, y) pairs."""
    cleaned = []
    if points is None:
        return cleaned
    for i, p in enumerate(points):
        x, y = get_x(p), get_y(p)
        conf = p.get("confidence")
        # A null coordinate is only acceptable if a confidence note explains it.
        if (x is None or y is None) and not conf:
            report.err(f"{where}[{i}]",
                       "null coordinate with no confidence note explaining why")
        if y is not None and y < 0:
            report.err(f"{where}[{i}]", f"negative depth {y} (depth is positive-down)")
        if y is not None and y > MAX_PLAUSIBLE_DEPTH_M:
            report.warn(f"{where}[{i}]", f"implausibly deep ({y} m)")
        if x is not None and y is not None:
            cleaned.append((x, y))
    # x should march left-to-right; flag out-of-order x (often a transcription slip)
    xs = [x for x, _ in cleaned]
    if xs != sorted(xs):
        report.warn(where, f"x-coordinates not left-to-right: {xs}")
    return cleaned


def depth_at_x(boundary_pairs, x):
    """Linear-interpolate a boundary's depth at a given x. None if uncoverable."""
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


# ---- per-face checks -----------------------------------------------------

def check_face(face, report):
    fname = face.get("face") or "UNNAMED FACE"
    layers = face.get("layers") or []
    if not layers:
        report.warn(fname, "no layers")
        return

    prev_bottom = None          # cleaned pairs of the layer above's bottom
    prev_name = None

    for li, layer in enumerate(layers):
        lname = layer.get("layerName") or f"layer {li}"
        where = f"{fname} / {lname}"

        top = check_boundary(layer.get("topBoundary"), f"{where} top", report)
        bottom = check_boundary(layer.get("bottomBoundary"), f"{where} bottom", report)

        # 1) top of this layer should match bottom of the layer above.
        if prev_bottom and top:
            for x, y in top:
                above = depth_at_x(prev_bottom, x)
                if above is not None and abs(y - above) > MONOTONIC_TOLERANCE_M:
                    report.warn(
                        where,
                        f"top at x={x} (depth {y:.2f}) doesn't meet "
                        f"{prev_name} bottom (depth {above:.2f}) — gap/overlap")

        # 2) monotonic stacking: this layer's bottom must not rise above the
        #    layer above's bottom (layers can't cross).
        if prev_bottom and bottom:
            for x, y in bottom:
                above = depth_at_x(prev_bottom, x)
                if above is not None and y < above - MONOTONIC_TOLERANCE_M:
                    report.err(
                        where,
                        f"bottom at x={x} (depth {y:.2f}) is ABOVE "
                        f"{prev_name}'s bottom (depth {above:.2f}) — layers cross")

        # 3) features should stay within this layer's vertical extent.
        check_features(layer, top, bottom, where, report)

        if bottom:
            prev_bottom = bottom
            prev_name = lname
        # if a layer has no bottom (e.g. virgin soil), keep the previous one
        # as the reference so the next real layer still gets checked.


def check_features(layer, top, bottom, where, report):
    feats = layer.get("featuresInLayer")
    if not feats:
        return
    # Vertical band this layer occupies, for containment checks.
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

        # containment: shape points shouldn't fall outside the layer band.
        if has_shape and top_min is not None and bot_max is not None:
            for pi, p in enumerate(sp):
                y = get_y(p)
                if y is None:
                    continue
                # small tolerance; carbon lenses can hug the boundary
                if y < top_min - MONOTONIC_TOLERANCE_M or y > bot_max + MONOTONIC_TOLERANCE_M:
                    report.warn(
                        f"{fwhere}[{pi}]",
                        f"point depth {y:.2f} lies outside layer band "
                        f"[{top_min:.2f}, {bot_max:.2f}]")


# ---- top-level -----------------------------------------------------------

def validate(data):
    report = Report()

    scan_null_strings(data, "root", report)

    profiles = data.get("trenchProfiles")
    if not profiles:
        report.err("root", "no trenchProfiles")
        return report

    for face in profiles:
        # grid label / x-position sanity
        gx = face.get("gridLabelXMeters")
        gl = face.get("gridLabels")
        if gl and gx and len(gl) != len(gx):
            report.warn(
                face.get("face") or "face",
                f"gridLabels ({len(gl)}) and gridLabelXMeters ({len(gx)}) "
                "differ in length")
        check_face(face, report)

    return report


def main():
    if len(sys.argv) != 2:
        print("usage: python validate.py <output.json>")
        sys.exit(2)
    with open(sys.argv[1]) as f:
        data = json.load(f)

    report = validate(data)

    for line in report.warnings:
        print(line)
    for line in report.errors:
        print(line)

    print(f"\n{len(report.errors)} error(s), {len(report.warnings)} warning(s).")
    sys.exit(1 if report.errors else 0)


if __name__ == "__main__":
    main()