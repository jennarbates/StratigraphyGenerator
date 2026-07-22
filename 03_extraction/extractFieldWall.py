"""
extractFieldWall.py — extraction schema + prompt for MODERN FIELD RECORDING
SHEETS (hand-drawn on graph paper, in the field), as opposed to the archival
illustrator-style profile handled by renameImages.py.

Why this is a separate script, not a flag on renameImages.py
============================================================
renameImages.py's schema assumes a drawn LEGEND mapping hatch/fill patterns
to named materials (`inferredMaterial` + `visualPattern`). Modern field
sheets like this one don't draw fills at all — they label each layer with a
**Locus number**, and separately record that locus's soil color as a
**Munsell notation** (e.g. "10YR 5/3 brown") in a list at the edge of the
sheet. Forcing that into `inferredMaterial`/`visualPattern` would mean
inventing a fill-pattern description that was never drawn. Different
recording convention -> different schema, same downstream CSV shape.

Scale convention on these sheets
================================
There is usually no printed metric bar (unlike the illustrator sheets) —
scale comes from the graph-paper grid itself. The model should NOT assume a
square size; a human confirms it (this project's Trench T104 sheet: bold
grid squares = 20 cm, minor squares = 1/10 of that = 2 cm) and it gets
passed in via --square-cm, not re-derived from the drawing each time.

Coordinate system (same convention as renameImages.py, to keep convertCoords.py
reusable):
    x     = horizontal position ALONG the face, meters, 0 at the left edge.
    depth = downward from the ground surface, meters, positive down.
Any site-grid tie-in numbers written on the sheet (stake labels, elevations,
northing/easting-looking figures) are transcribed VERBATIM into
`gridTiePoints` / `marginalia` and never interpreted into x/y — what they
mean is a site-records question, not something to guess from the drawing.

Usage:
    python extractFieldWall.py IMG_9380.jpeg --square-cm 20 --out field_wall.json
"""

import os
import sys
import time

from google import genai
from google.genai import errors, types
from PIL import Image
from pydantic import BaseModel


class MunsellColor(BaseModel):
    raw: str | None          # verbatim as written, e.g. "10YR 5/3"
    colorName: str | None    # verbatim color name if given, e.g. "brown"


class Locus(BaseModel):
    locusNumber: str | None
    munsell: MunsellColor | None
    description: str | None = None   # any extra prose note by the locus
    confidence: str | None = None


class BoundaryPoint(BaseModel):
    xMeters: float | None
    depthMeters: float | None
    confidence: str | None = None


class FieldFeature(BaseModel):
    """Stone or other discrete/traced object within a locus layer. Same
    shape as renameImages.py's NotableFeature, kept separate so this
    schema has no bare `dict` fields (Gemini's structured-output schema
    converter needs real named fields, not an untyped dict)."""
    feature: str | None
    description: str | None = None
    shapePoints: list[BoundaryPoint] | None = None
    approxXMeters: float | None = None
    approxDepthMeters: float | None = None
    approxWidthMeters: float | None = None
    approxHeightMeters: float | None = None
    confidence: str | None = None


class LocusLayer(BaseModel):
    locusNumber: str | None      # ties back to Locus.locusNumber
    topBoundary: list[BoundaryPoint] | None
    bottomBoundary: list[BoundaryPoint] | None
    featuresInLayer: list[FieldFeature] | None = None


class GridTiePoint(BaseModel):
    """A stake/coordinate label written along the top or side of the wall.
    Transcribed verbatim; NOT interpreted into site coordinates here."""
    rawText: str | None
    approxXMeters: float | None = None   # where along the face it sits, if clear


class FieldWallProfile(BaseModel):
    trenchLabel: str | None            # e.g. "T104"
    faceLabel: str | None              # e.g. "southern baulk wall"
    illustrators: list[str] | None
    date: str | None                   # verbatim, e.g. "28.07.25"
    northArrowPresent: bool | None
    gridSquareCm: float | None         # passed-in, echoed back for the record
    gridTiePoints: list[GridTiePoint] | None
    loci: list[Locus] | None
    layers: list[LocusLayer] | None
    marginalia: list[str] | None       # any other verbatim text not captured above
    rawTranscription: str | None = None


client = genai.Client()


def generate_with_retry(max_attempts: int = 5, **kwargs):
    for attempt in range(max_attempts):
        try:
            return client.models.generate_content(**kwargs)
        except errors.ServerError as e:
            transient = getattr(e, "code", None) in (500, 503, 429)
            if transient and attempt < max_attempts - 1:
                wait = 2 ** attempt
                print(f"  API returned {e.code}; retrying in {wait}s "
                      f"(attempt {attempt + 1}/{max_attempts})...")
                time.sleep(wait)
            else:
                raise


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
(e.g. "10YR 5/3 brown" = hue, value/chroma, color name). This is NOT a
fill-pattern legend — do not invent a `visualPattern` description. Read each
locus's Munsell notation and color name VERBATIM into `loci[]`, exactly as
written, including hue/value/chroma punctuation. If a color name is not
given alongside the code, leave `colorName` null rather than guessing one
from the code.

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
rawTranscription (your full natural-language reading, for reference — keep
structured fields clean and numeric).

Emit ONLY the JSON conforming to the schema.
"""


def process_field_wall(image_path: str, square_cm: float, out_path: str):
    if not os.path.exists(image_path):
        print(f"file not found: {image_path}")
        return None

    print("analyzing field wall drawing...")
    img = Image.open(image_path)
    prompt = build_prompt(square_cm)

    response = generate_with_retry(
        model="gemini-2.5-flash",
        contents=[img, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FieldWallProfile,
            temperature=0.1,
            max_output_tokens=16384,
        ),
    )

    raw_json = response.text
    try:
        finish_reason = response.candidates[0].finish_reason
        if str(finish_reason).endswith("MAX_TOKENS"):
            print(f"WARNING: response was cut off by the token limit "
                  f"(finish_reason={finish_reason}). The written JSON is "
                  f"almost certainly incomplete/invalid — raise "
                  f"max_output_tokens further and re-run rather than "
                  f"trying to use this file as-is.")
    except (AttributeError, IndexError):
        pass
    with open(out_path, "w") as f:
        f.write(raw_json)
    print(f"wrote {out_path}")
    return response.parsed


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--square-cm", type=float, required=True,
                    help="real-world size of one BOLD grid square, in cm "
                         "(measure/confirm by hand — do not guess)")
    ap.add_argument("--out", default="field_wall.json")
    args = ap.parse_args()
    process_field_wall(args.image, args.square_cm, args.out)