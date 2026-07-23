"""
assign_markers.py — close the gap detectFieldWallMarkers left open: decide
which locus/boundary each CV-detected marker belongs to.

Division of labor, per the note at the bottom of the original tool:
  - the marker COORDINATES come from computer vision and are immutable —
    they pass through this module verbatim, byte for byte
  - Gemini only CLASSIFIES each fixed point (surface line / bottom boundary
    of locus N / noise) and reads the sheet's labels (loci Munsell colors,
    tie points, metadata) — a task it did fine on even in the runs whose
    geometry was fabricated
The final FieldWallProfile JSON is then assembled deterministically here,
so there is no path by which the model can invent, move, or drop a vertex:
if it misassigns one, the point is on the wrong boundary but still a real
point from the paper, and the validator's spacing checks stay meaningful.
"""

import json
import os

from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel

from pipeline._extract_common import generate_with_retry, check_response
from pipeline.extract_fieldwall import (
    FieldWallProfile, Locus, GridTiePoint, _cap_for_sending)

Image.MAX_IMAGE_PIXELS = None


# ---------------------------------------------------------------------------
# response schema: per-marker classification + the label-reading parts of
# the ordinary field-wall extraction (geometry deliberately absent)
# ---------------------------------------------------------------------------

class MarkerAssignment(BaseModel):
    markerId: int
    # "surface"  -> the wall's top/ground line (top boundary of the first locus)
    # "bottom"   -> the bottom boundary of locusNumber
    # "noise"    -> stone, hatch mark, stray dot: not a boundary vertex
    kind: str
    locusNumber: str | None = None


class MarkerAssignmentResult(BaseModel):
    trenchLabel: str | None
    faceLabel: str | None
    illustrators: list[str] | None
    date: str | None
    northArrowPresent: bool | None
    gridSquareCm: float | None
    gridTiePoints: list[GridTiePoint] | None
    loci: list[Locus] | None
    marginalia: list[str] | None
    assignments: list[MarkerAssignment]


def build_prompt(markers, square_cm):
    lines = "\n".join(
        f"  id={m['id']}  x={m['x_m']:.3f}  depth={m['depth_m']:.3f}"
        for m in markers)
    return f"""
You are looking at a MODERN FIELD RECORDING SHEET of a single trench wall
(baulk section) hand-drawn on graph paper. One bold grid square represents
{square_cm} cm (echo this back as gridSquareCm).

A computer-vision pass has ALREADY located every candidate vertex marker
(the recorder's small circles/dots) and measured its position. These points
are REAL and FIXED. You must not invent new points, move points, or report
coordinates anywhere. Your job has exactly two parts:

PART 1 — transcribe the sheet's text, verbatim:
- trenchLabel, faceLabel, illustrators, date, northArrowPresent
- gridTiePoints: the coordinate labels along the top edge, rawText exactly
  as written
- loci[]: every locus entry with its Munsell color exactly as written,
  including duplicates if a locus number appears twice
- marginalia: any other writing on the sheet

PART 2 — classify every candidate point below. The wall's boundary lines
are polylines connecting these dots. For each id, decide:
- kind="surface": the point sits on the wall's TOP edge / ground line
- kind="bottom", locusNumber="N": the point sits on the line that forms the
  BOTTOM boundary of locus N (the line separating locus N from what lies
  below it). Use the sheet's locus labels and vertical order to decide N.
- kind="noise": the point is NOT a boundary vertex — a small stone, a hatch
  mark in a textured band, or a stray dot.

Rules:
- Return exactly one assignment for EVERY id listed, no more, no fewer.
- Points on the same drawn line must get the same classification.
- A boundary's points appear at similar depths that vary gradually with x;
  a sudden isolated outlier on an otherwise smooth line is probably noise.
- The lowest drawn line of the section is the bottom boundary of the
  deepest locus.

Candidate points (x = meters from the wall's left edge, depth = meters
down from the wall's top-left corner):
{lines}

Emit ONLY JSON conforming to the schema.
"""


# ---------------------------------------------------------------------------
# deterministic assembly: CV coordinates in, FieldWallProfile out
# ---------------------------------------------------------------------------

def _assemble(markers, result_dict):
    """Build the FieldWallProfile dict. Coordinates come exclusively from
    `markers`; `result_dict` contributes only labels and classifications.
    Returns (profile_dict, warnings:list[str])."""
    warnings = []
    by_id = {m["id"]: m for m in markers}

    seen = {}
    for a in result_dict.get("assignments") or []:
        mid = a.get("markerId")
        if mid not in by_id:
            warnings.append(f"assignment for unknown marker id {mid} ignored")
            continue
        if mid in seen:
            warnings.append(f"marker id {mid} assigned twice — keeping the "
                            f"first ({seen[mid]['kind']})")
            continue
        seen[mid] = a
    missing = sorted(set(by_id) - set(seen))
    if missing:
        warnings.append(f"{len(missing)} markers got no assignment "
                        f"(ids {missing[:10]}{'…' if len(missing) > 10 else ''}) "
                        f"— treated as noise")

    def pt(m):
        return {"xMeters": m["x_m"], "depthMeters": m["depth_m"],
                "confidence": None}

    surface, bottoms, n_noise = [], {}, 0
    for mid, a in seen.items():
        kind = (a.get("kind") or "").strip().lower()
        if kind == "surface":
            surface.append(by_id[mid])
        elif kind == "bottom":
            num = str(a.get("locusNumber") or "").strip()
            if not num:
                warnings.append(f"marker {mid} classified 'bottom' with no "
                                f"locusNumber — treated as noise")
                n_noise += 1
                continue
            bottoms.setdefault(num, []).append(by_id[mid])
        else:
            n_noise += 1

    for lst in bottoms.values():
        lst.sort(key=lambda m: m["x_m"])
    surface.sort(key=lambda m: m["x_m"])

    # vertical order of loci = mean depth of their bottom boundaries
    order = sorted(bottoms,
                   key=lambda n: sum(m["depth_m"] for m in bottoms[n])
                   / len(bottoms[n]))

    layers = []
    prev = surface
    for num in order:
        pts = bottoms[num]
        if len(pts) < 2:
            warnings.append(f"locus {num}: only {len(pts)} marker(s) on its "
                            f"bottom boundary — too few to draw a line; check "
                            f"the debug image / assignments")
        layers.append({
            "locusNumber": num,
            "topBoundary": [pt(m) for m in prev] or None,
            "bottomBoundary": [pt(m) for m in pts],
            "featuresInLayer": None,
        })
        prev = pts

    listed = [str(l.get("locusNumber") or "").strip()
              for l in (result_dict.get("loci") or [])]
    for num in dict.fromkeys(n for n in listed if n):
        if num not in bottoms:
            warnings.append(f"locus {num} is listed in the legend but got no "
                            f"boundary markers")

    if not surface:
        warnings.append("no markers classified as the surface line — the "
                        "first locus has no top boundary")

    marginalia = list(result_dict.get("marginalia") or [])
    marginalia.append(
        f"[provenance] boundary coordinates from CV marker detection "
        f"({len(markers)} candidates: {sum(len(v) for v in bottoms.values())} "
        f"boundary + {len(surface)} surface + {n_noise + len(missing)} noise); "
        f"Gemini assigned loci/labels only and generated no geometry")

    profile = {
        "trenchLabel": result_dict.get("trenchLabel"),
        "faceLabel": result_dict.get("faceLabel"),
        "illustrators": result_dict.get("illustrators"),
        "date": result_dict.get("date"),
        "northArrowPresent": result_dict.get("northArrowPresent"),
        "gridSquareCm": result_dict.get("gridSquareCm"),
        "gridTiePoints": result_dict.get("gridTiePoints"),
        "loci": result_dict.get("loci"),
        "layers": layers,
        "marginalia": marginalia,
    }
    # guarantee schema compatibility with everything downstream
    profile = FieldWallProfile(**profile).model_dump()
    return profile, warnings


# ---------------------------------------------------------------------------
# entry points
#
# Two-phase API used by the webapp (/markers/assign then /markers/finalize):
#   classify_markers()     network call, returns the proposal for user review
#   finalize_assignments() no network, assembles the reviewed proposal + the
#                          immutable CV coordinates into the extraction JSON
# run_assign() below composes the two for one-shot/CLI use.
# ---------------------------------------------------------------------------

def classify_markers(image_path, markers, square_cm, api_key,
                     max_output_tokens=65536, progress_cb=None):
    """Phase 1 (calls Gemini): classify each detected marker
    (surface / bottom of locus N / noise) and read the sheet's labels.
    Generates no geometry and writes nothing to disk. `image_path` must be
    the SAME rotated frame the markers were measured in (run_detect's
    marker_source_rotated.png). Returns
    {"result_dict": <parsed MarkerAssignmentResult>, "warning": str|None}
    — the shape the frontend review step expects."""
    if not markers:
        raise RuntimeError("no markers to assign — run detection first")
    if not os.path.exists(image_path):
        raise RuntimeError(f"file not found: {image_path}")

    if progress_cb:
        progress_cb(f"asking Gemini to assign {len(markers)} detected markers "
                    f"to loci (classification only — no geometry generation)...")

    client = genai.Client(api_key=api_key,
                          http_options=types.HttpOptions(timeout=240_000))
    img = Image.open(image_path)
    orig_size = img.size
    img = _cap_for_sending(img)
    if img.size != orig_size and progress_cb:
        progress_cb(f"resized {orig_size[0]}x{orig_size[1]} -> "
                    f"{img.size[0]}x{img.size[1]} before sending to Gemini")

    response = generate_with_retry(
        client,
        progress_cb=progress_cb,
        model="gemini-2.5-flash",
        contents=[img, build_prompt(markers, square_cm)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MarkerAssignmentResult,
            temperature=0.1,
            max_output_tokens=max_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
        ),
    )

    raw = response.text
    api_warning = check_response(response, raw)

    result_dict = json.loads(raw)
    n = len(result_dict.get("assignments") or [])
    if progress_cb:
        progress_cb(f"received {n} marker assignments — review them, then "
                    f"finalize to build the extraction")
    return {"result_dict": result_dict, "warning": api_warning}


def finalize_assignments(markers, result_dict, out_path):
    """Phase 2 (no network call): assemble the (possibly user-edited)
    classification `result_dict` plus the immutable CV marker coordinates
    into the FieldWallProfile extraction JSON, write it to `out_path`, and
    return (raw_json_text, warning_or_None) like the other extraction
    runners."""
    if not markers:
        raise RuntimeError("no markers to finalize — run detection first")
    if not result_dict or not (result_dict.get("assignments") or []):
        raise RuntimeError("no assignments to finalize — run classification "
                           "first")

    profile, warnings = _assemble(markers, result_dict)

    raw_json = json.dumps(profile, indent=2)
    with open(out_path, "w") as f:
        f.write(raw_json)

    warning = " | ".join(warnings) if warnings else None
    return raw_json, warning


def run_assign(image_path, markers, square_cm, out_path, api_key,
               max_output_tokens=65536, progress_cb=None):
    """One-shot convenience wrapper: classify then immediately finalize,
    with no review step in between. Preserved for CLI/script use; the
    webapp calls the two phases separately. Returns
    (raw_json_text, warning_or_None) exactly as before the split."""
    classified = classify_markers(
        image_path, markers, square_cm, api_key,
        max_output_tokens=max_output_tokens, progress_cb=progress_cb)

    raw_json, assemble_warning = finalize_assignments(
        markers, classified["result_dict"], out_path)
    if progress_cb:
        progress_cb(f"wrote {out_path}")

    parts = [w for w in (classified["warning"], assemble_warning) if w]
    warning = " | ".join(parts) if parts else None
    return raw_json, warning