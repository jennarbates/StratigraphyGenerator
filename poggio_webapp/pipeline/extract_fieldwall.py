"""
extract_fieldwall.py — adapted from 03_extraction/extractFieldWall.py.

Same schema/prompt as the original script (for modern hand-drawn field
recording sheets, Locus number + Munsell color instead of a hatch legend).
Adapted to accept an explicit API key and output path, and to return the raw
JSON / parse warnings instead of only printing.
"""

import os
import time

from google import genai
from google.genai import errors, types
from PIL import Image
from pydantic import BaseModel

from pipeline._extract_common import generate_with_retry

# See extract_illustrator.py — same rationale: locally-generated preprocessed
# scans, not untrusted uploads, so raise PIL's decompression-bomb cap.
Image.MAX_IMAGE_PIXELS = None

# See extract_illustrator.py — preprocessing's upscale is tuned for scan line
# resolution, not for what Gemini needs; cap the longest side before sending
# regardless of upscale factor so a big field photo doesn't turn into a
# multi-hundred-megapixel payload.
MAX_SEND_DIMENSION = 3072


def _cap_for_sending(img, max_dim=MAX_SEND_DIMENSION):
    w, h = img.size
    if max(w, h) <= max_dim:
        return img
    scale = max_dim / max(w, h)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


class MunsellColor(BaseModel):
    raw: str | None
    colorName: str | None


class Locus(BaseModel):
    locusNumber: str | None
    munsell: MunsellColor | None
    description: str | None = None
    confidence: str | None = None


class BoundaryPoint(BaseModel):
    xMeters: float | None
    depthMeters: float | None
    confidence: str | None = None


class FieldFeature(BaseModel):
    feature: str | None
    description: str | None = None
    shapePoints: list[BoundaryPoint] | None = None
    approxXMeters: float | None = None
    approxDepthMeters: float | None = None
    approxWidthMeters: float | None = None
    approxHeightMeters: float | None = None
    confidence: str | None = None


class LocusLayer(BaseModel):
    locusNumber: str | None
    topBoundary: list[BoundaryPoint] | None
    bottomBoundary: list[BoundaryPoint] | None
    featuresInLayer: list[FieldFeature] | None = None


class GridTiePoint(BaseModel):
    rawText: str | None
    approxXMeters: float | None = None


class FieldWallProfile(BaseModel):
    trenchLabel: str | None
    faceLabel: str | None
    illustrators: list[str] | None
    date: str | None
    northArrowPresent: bool | None
    gridSquareCm: float | None
    gridTiePoints: list[GridTiePoint] | None
    loci: list[Locus] | None
    layers: list[LocusLayer] | None
    marginalia: list[str] | None




def build_prompt(square_cm: float) -> str:
    return f"""
You are transcribing a MODERN FIELD RECORDING SHEET of a single trench wall
(baulk section), hand-drawn on graph paper, DIRECTLY into the provided JSON
schema. Downstream software treats your numbers as real measurements.
Measurement fidelity and honest uncertainty matter far more than
completeness. A null value is always better than a plausible-sounding guess.

============================================================
COORDINATE SYSTEM
============================================================
- x = horizontal position ALONG the face, in METERS, from the LEFT edge of
  the drawn wall.
- depth = downward from the ground surface, in METERS, positive down;
  surface is depth=0.
- Never negative depth; never mix axes.

============================================================
SCALE
============================================================
The bold grid squares on this sheet are {square_cm} cm per side (given by
the recorder, not something to re-derive). Minor grid lines subdivide each
bold square evenly — count them to get the subdivision, don't assume a
count. Use the grid itself as the ruler; there is no separate printed scale
bar on this kind of sheet.

============================================================
LOCUS + MUNSELL, NOT A HATCH LEGEND
============================================================
This sheet records material with a **Locus number** per layer (e.g. "Locus
3") and a **Munsell soil color** written in a list at the edge of the sheet
(e.g. "10YR 5/3 brown") in a list at the edge of the sheet (hue, value/chroma,
color name). This is NOT a fill-pattern legend — do not invent a
`visualPattern` description. Read each locus's Munsell notation and color name
VERBATIM into `loci[]`, exactly as written, including hue/value/chroma
punctuation. If a color name is not given alongside the code, leave
`colorName` null rather than guessing one from the code.

============================================================
GRID TIE-IN / COORDINATE LABELS
============================================================
Numbers or stake labels along the top or side of the wall that look like
site-grid coordinates, elevations, or survey tie-ins go VERBATIM into
`gridTiePoints[].rawText`. Do NOT interpret what they mean (northing vs.
easting vs. elevation vs. something else) — that is a site-records question
for a human, not something to infer from the drawing. Only fill
`approxXMeters` if it is unambiguous which point along the face the label
marks; otherwise leave null.

============================================================
BOUNDARIES — FIND THE MARKED POINTS, DON'T ESTIMATE A CURVE
============================================================
On this kind of sheet, each boundary line is a polyline connecting
individually-marked points: the recorder shot or measured each vertex and
marked it with a small circle/dot directly on the line, then connected the
dots with straight segments. Your job is NOT to sample the line's shape at
your own chosen intervals — it is to find every circle marker actually
drawn on each boundary and report its (x, depth) position. The line
between consecutive markers is straight by construction; you do not need
to (and should not) add extra points between them to make the curve look
smoother.

How to do this correctly:
  - Scan each boundary line specifically for small circle/dot marks sitting
    ON the line. Each one is a real measured point.
  - Report exactly one boundary point per circle marker you can actually
    see, at its real position — not one every fixed grid interval.
  - Circle spacing along a real boundary is IRREGULAR — some segments
    between markers are short, some long, depending on where the recorder
    chose to shoot a point (usually where the line bends). If your
    reported points come out evenly spaced (e.g. every 0.08m or every
    grid line), you have reverted to estimating instead of finding the
    actual markers — stop and re-scan for the real dot positions.
  - If a stretch of boundary has no visible circle markers, do not invent
    one — leave that stretch to whatever markers bound it. Undercounting
    real markers is far better than adding a fabricated one.
  - Two different loci's boundaries should almost never have circles at
    the same x-positions as each other, since each was measured
    independently. If your output shows the same x-spacing pattern
    repeating across multiple loci, that is a sign you are generating a
    template rather than reading the actual marker positions on each line
    — go back and re-examine each boundary on its own.

If a layer's top = the layer above's bottom, leave topBoundary null.

============================================================
FEATURES
============================================================
Stones and other discrete objects: use `approxXMeters`/`approxDepthMeters`/
`approxWidthMeters`/`approxHeightMeters` on the feature, same convention as
the illustrator-sheet schema. Outlined/traced features (e.g. a cut or
lens): capture their outline in `shapePoints` as (x, depth) points instead
of an approx box.

============================================================
UNCERTAINTY
============================================================
Faded, obscured, or ambiguous handwriting/geometry: set the field to null
and explain why in that item's `confidence`. Uncertainty is per point/locus,
not global — don't null out the whole drawing because one number is hard to
read.

============================================================
NO INTERPRETATION BEYOND WHAT IS DRAWN
============================================================
Do not infer chronology, period, or context relationships. Report only what
is visibly drawn, labeled, or written. Transcribe unclear text exactly as
written rather than correcting or normalizing it.

============================================================
FIELDS TO FILL
============================================================
trenchLabel, faceLabel, illustrators, date, northArrowPresent, gridSquareCm
(echo {square_cm} back), gridTiePoints[], loci[], layers[], marginalia[],

Emit ONLY the JSON conforming to the schema.
"""


def run_extraction(image_path: str, square_cm: float, out_path: str,
                    api_key: str, max_output_tokens: int = 65536, progress_cb=None):
    """Runs the field-wall extraction. Returns (raw_json_text, warning_or_None)."""
    if not os.path.exists(image_path):
        raise RuntimeError(f"file not found: {image_path}")

    if progress_cb:
        progress_cb("analyzing field wall drawing...")

    client = genai.Client(api_key=api_key,
                           http_options=types.HttpOptions(timeout=240_000))  # 4 min
    img = Image.open(image_path)
    orig_size = img.size
    img = _cap_for_sending(img)
    if img.size != orig_size and progress_cb:
        progress_cb(f"resized {orig_size[0]}x{orig_size[1]} -> {img.size[0]}x{img.size[1]} before sending to Gemini")
    prompt = build_prompt(square_cm)

    response = generate_with_retry(
        client,
        progress_cb=progress_cb,
        model="gemini-2.5-flash",
        contents=[img, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FieldWallProfile,
            temperature=0.1,
            max_output_tokens=max_output_tokens,
            # 2.5-flash "thinks" before writing any JSON by default; on a
            # dense sheet that reasoning alone can push the request past
            # Google's server-side deadline (504). Cap it — raise or drop
            # this if extraction quality visibly suffers, set 0 to disable
            # thinking entirely.
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
        ),
    )

    raw_json = response.text
    with open(out_path, "w") as f:
        f.write(raw_json)

    from pipeline._extract_common import check_response
    warning = check_response(response, raw_json)

    if progress_cb:
        progress_cb(f"wrote {out_path}")

    return raw_json, warning