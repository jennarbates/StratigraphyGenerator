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
    if point.get("xCoordinateMeters") is not None:
        return point.get("xCoordinateMeters")
    return point.get("xMeters")


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


# --- fabrication detection -------------------------------------------------
# The T104 field-wall extraction produced geometrically fabricated boundaries
# twice: every point on a fixed x interval, and each locus's boundary an exact
# copy of the one above offset by a constant depth. The extraction prompt
# already warns against this and it happened anyway, so check for it here
# instead of trusting the model to police itself. Real traced boundaries have
# irregular vertex spacing (Trench 23 sits around cv 0.20); fabricated ones
# come out at cv 0.00.

UNIFORM_SPACING_CV = 0.02      # coefficient of variation below this = suspicious
PARALLEL_OFFSET_TOLERANCE_M = 0.005


def _pairs(points):
    out = []
    for p in points or []:
        x, y = get_x(p), get_y(p)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            out.append((x, y))
    return out


def check_uniform_spacing(points, where, report):
    """Warn when boundary vertices sit on a perfectly regular x interval."""
    pts = _pairs(points)
    if len(pts) < 5:
        return
    xs = [x for x, _ in pts]
    dx = [b - a for a, b in zip(xs, xs[1:])]
    mean = sum(dx) / len(dx)
    if mean <= 0:
        return
    var = sum((d - mean) ** 2 for d in dx) / len(dx)
    cv = (var ** 0.5) / mean
    if cv < UNIFORM_SPACING_CV:
        report.warn(where,
                    f"boundary vertices are evenly spaced every {mean:.3g} m "
                    f"({len(pts)} points, spacing variation {cv:.3f}) — this is "
                    "the signature of points estimated at a fixed interval "
                    "rather than read off the recorder's marked vertices. "
                    "Re-extract, or detect the markers computationally.")


def check_parallel_layers(layers, where, report):
    """Warn when two layers' boundaries are the same shape shifted by a
    constant depth — a copy-paste artifact, not real stratigraphy."""
    shaped = []
    for layer in layers or []:
        pts = _pairs(layer.get("bottomBoundary"))
        if len(pts) >= 4:
            name = (layer.get("inferredMaterial") or layer.get("layerName")
                    or layer.get("locusNumber") or "?")
            shaped.append((str(name), pts))

    for i in range(len(shaped)):
        for j in range(i + 1, len(shaped)):
            (na, pa), (nb, pb) = shaped[i], shaped[j]
            if len(pa) != len(pb):
                continue
            if any(abs(a[0] - b[0]) > 1e-9 for a, b in zip(pa, pb)):
                continue          # different x stations — not comparable
            diffs = [b[1] - a[1] for a, b in zip(pa, pb)]
            spread = max(diffs) - min(diffs)
            if spread <= PARALLEL_OFFSET_TOLERANCE_M:
                report.warn(where,
                            f"layers {na!r} and {nb!r} have identical boundary "
                            f"shapes offset by a constant "
                            f"{sum(diffs)/len(diffs):.3g} m — almost certainly "
                            "one boundary copied down, not two traced ones.")


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
               max_plausible_depth_m, source="extraction"):
    fname = face.get("face") or "UNNAMED FACE"
    layers = face.get("layers") or []
    if not layers:
        report.warn(fname, "no layers")
        return

    if source != "manual_editor":
        check_parallel_layers(layers, fname, report)

    prev_bottom = None
    prev_name = None

    for li, layer in enumerate(layers):
        lname = layer.get("layerName") or f"layer {li}"
        where = f"{fname} / {lname}"

        top = check_boundary(layer.get("topBoundary"), f"{where} top", report,
                              max_plausible_depth_m)
        bottom = check_boundary(layer.get("bottomBoundary"), f"{where} bottom", report,
                                 max_plausible_depth_m)

        if source != "manual_editor":
            check_uniform_spacing(layer.get("bottomBoundary"), f"{where} bottom", report)

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


def _check_field_wall_extras(data, report):
    """Checks that only apply to a FieldWallProfile extraction."""
    where = data.get("faceLabel") or "field wall"

    loci = data.get("loci") or []
    layer_nums = {str(l.get("locusNumber", "")).strip()
                  for l in (data.get("layers") or [])}
    locus_nums = [str(l.get("locusNumber", "")).strip() for l in loci]

    for num in sorted(layer_nums - set(locus_nums)):
        if num:
            report.warn(where, f"layer references locus {num}, which has no "
                                "entry in loci[] (no Munsell reading)")
    dupes = {n for n in locus_nums if locus_nums.count(n) > 1 and n}
    for n in sorted(dupes):
        report.warn(where, f"locus {n} appears {locus_nums.count(n)} times in "
                            "loci[] with different Munsell readings — the "
                            "converter will use the first")

    # Tie-point labels: transcribed verbatim on purpose, but if their spacing
    # on the sheet disagrees with the drawn wall's own extent, the extraction's
    # scale is probably wrong.
    ties = [t for t in (data.get("gridTiePoints") or [])
            if isinstance(t.get("approxXMeters"), (int, float))]
    numeric = []
    for t in ties:
        raw = str(t.get("rawText", "")).strip().rstrip("m").strip()
        try:
            numeric.append((float(raw), t["approxXMeters"]))
        except ValueError:
            continue
    if len(numeric) >= 2:
        numeric.sort(key=lambda v: v[1])
        label_span = abs(numeric[-1][0] - numeric[0][0])
        drawn_span = abs(numeric[-1][1] - numeric[0][1])
        if drawn_span > 0 and label_span > 0:
            ratio = label_span / drawn_span
            if ratio > 1.5 or ratio < 0.67:
                report.warn(where,
                            f"tie-point labels span {label_span:g} units but "
                            f"were placed across only {drawn_span:g} m of the "
                            f"drawing ({ratio:.1f}x apart). If those labels are "
                            "metre marks, the extracted scale is wrong.")


def validate(data, monotonic_tolerance_m=DEFAULT_MONOTONIC_TOLERANCE_M,
             top_continuity_tolerance_m=DEFAULT_TOP_CONTINUITY_TOLERANCE_M,
             max_plausible_depth_m=DEFAULT_MAX_PLAUSIBLE_DEPTH_M):
    report = Report()

    scan_null_strings(data, "root", report)

    profiles = data.get("trenchProfiles")
    if not profiles:
        # A FieldWallProfile extraction (single wall, loci + Munsell) is a
        # valid input shape -- adapt it to the same face shape and run the
        # same geometric checks, rather than rejecting it outright.
        from . import convert_coords as _cc
        if _cc.is_field_wall(data):
            adapted, notes = _cc.fieldwall_to_profiles(data)
            for n in notes:
                report.warn("field wall", n)
            profiles = adapted["trenchProfiles"]
            _check_field_wall_extras(data, report)
        else:
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
                   max_plausible_depth_m, data.get("source", "extraction"))

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
