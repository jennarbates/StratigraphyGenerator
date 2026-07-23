"""
extract_illustrator.py — adapted from 03_extraction/renameImages.py.

Same schema and prompt as the original single-agent script. Adapted to:
  - accept an API key explicitly (rather than only reading GEMINI_API_KEY at
    import time), so the web app can pass a key entered in the browser.
  - write to an explicit output path instead of a hardcoded
    "output_single.json" in the current directory.
  - return (parsed_dict, raw_json_text) instead of only printing.
"""

import time

from google import genai
from google.genai import errors
from PIL import Image
from google.genai import types
from pydantic import BaseModel

# These are locally-generated preprocessed scans (this app's own 02_preprocess
# output, often upscaled 2x+), not untrusted uploads from the internet — raise
# PIL's default decompression-bomb cap so a legitimately large sheet doesn't
# get rejected as a suspected attack.
Image.MAX_IMAGE_PIXELS = None

# Preprocessing's upscale is tuned for keeping thin ink lines from vanishing
# on LOW-DPI scans — it has nothing to do with what Gemini needs to read the
# drawing, and an upscale factor picked for a scan can produce an enormous
# image on an already high-res photo (e.g. a 4284x5712 field photo at 3x+
# upscale). Sending that whole thing as base64 makes the request slow to the
# point of looking hung, with no accuracy benefit. Cap the longest side right
# before sending, independent of whatever upscale preprocessing used.
MAX_SEND_DIMENSION = 3072


def _cap_for_sending(img, max_dim=MAX_SEND_DIMENSION):
    w, h = img.size
    if max(w, h) <= max_dim:
        return img
    scale = max_dim / max(w, h)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


# ---------------------------------------------------------------------------
# SCHEMA (unchanged from renameImages.py)
# ---------------------------------------------------------------------------

class Scale(BaseModel):
    unit: str | None
    valuesMarked: list[int]
    metricConversionAssumption: str | None = None
    confidence: str | None = None


class Attribution(BaseModel):
    name: str | None
    role: str | None = None


class Credits(BaseModel):
    attributions: list[Attribution] | None = None
    year: str | None = None


class BoundaryPoint(BaseModel):
    xCoordinateMeters: float | None
    yCoordinateMeters: float | None
    confidence: str | None = None


class NotableFeature(BaseModel):
    feature: str | None
    description: str | None
    shapePoints: list[BoundaryPoint] | None = None
    approxXMeters: float | None = None
    approxYMeters: float | None = None
    approxWidthMeters: float | None = None
    approxHeightMeters: float | None = None
    confidence: str | None = None


class Layer(BaseModel):
    layerName: str | None
    inferredMaterial: str | None
    description: str | None
    visualPattern: str | None
    featuresInLayer: list[NotableFeature] | None
    topBoundary: list[BoundaryPoint] | None
    bottomBoundary: list[BoundaryPoint] | None


class LegendItem(BaseModel):
    visualPattern: str | None
    material: str | None


class TrenchProfile(BaseModel):
    face: str | None
    gridLabels: list[str] | None
    gridLabelXMeters: list[float | None] | None
    layers: list[Layer] | None


class Metadata(BaseModel):
    currentFilePath: str | None
    suggestedFilename: str | None
    trenchLabel: str | None
    scale: Scale | None
    credits: Credits | None
    marginalia: list[str] | None


class ArchaeologicalDiagram(BaseModel):
    metadata: Metadata | None
    trenchProfiles: list[TrenchProfile]
    legend: list[LegendItem] | None
    inferred_notes: list[str] | None = None
    rawTranscription: str | None = None


PROMPT_TEMPLATE = """
You are transcribing a single archaeological trench profile drawing DIRECTLY
into the provided JSON schema. There is no second pass - what you emit IS the
final data, and downstream software (GemPy) treats your numbers as real
measurements. Measurement fidelity and honest uncertainty matter far more than
completeness. A null value is always better than a plausible-sounding guess.

The dig is Poggio Civitate, Murlo, Italy. Set metadata.currentFilePath to
exactly {image_path}.

============================================================
COORDINATE SYSTEM
============================================================
- x = horizontal position ALONG the face, in METERS, from the LEFT edge of that
  face's profile (each face has its own x=0).
- y = depth DOWNWARD from the ground surface, in METERS, positive down; surface
  is y=0.
- Never negative y; never mix axes.

============================================================
STEP 1 - SCALE  (calibrate before measuring)
============================================================
A word next to the scale bar is NOT automatically a unit. Units are short
measurement abbreviations (M, m, cm, ft, in). A capitalized surname (e.g.
"PECK") beside a year is a PERSON'S NAME/signature, not a unit — do NOT invent a
conversion for it.
- If it is a real unit: read the bar's printed values verbatim into `scale`.
- If it is a name/signature or initials: put it in `credits.attributions` as
  {{name, role}} (role ONLY if the drawing states it, else null — don't guess a
  role). Also transcribe the raw text verbatim into `metadata.marginalia`.
- Any signature/number/date string (e.g. "NR. 7/80") goes verbatim into
  `metadata.marginalia`; don't force its meaning. If a year is clearly legible,
  also record `credits.year`.
- Measure ONLY with the metric (M) bar, for both x and y. Only a genuine second
  UNIT scale (not a name) may go in `scale.metricConversionAssumption`.
- Establish drawn-units-per-meter from the metric bar and apply it consistently.
  Sanity-check each face's total width against the bar.

============================================================
STEP 2 - GRID LABELS
============================================================
For each face, list gridLabels in order and estimate each label's x-position in
meters (from that face's left edge) into gridLabelXMeters, same order. Grid
labels are a reference, NOT where boundary points must go.

============================================================
STEP 3 - MEASURE EACH BOUNDARY INDEPENDENTLY  (most important instruction)
============================================================
For each layer, trace its bottom boundary (and top boundary only if drawn
independently) as (x, y) points that follow the DRAWN LINE'S OWN shape.

CRITICAL - do NOT trace one boundary and offset it for the others. Each layer's
boundary has its OWN shape: its own bumps, dips, pinch-outs, and thickness
changes. Adjacent layers are usually NOT parallel - the gap between two
boundaries widens and narrows along the face. Read every boundary line on its
own, directly from the drawing, even if that is slower.

Warning signs you are doing it wrong (fix before finalizing):
  - Two boundaries have the SAME up/down pattern shifted by a constant depth.
  - Every layer has the same number of points at the same x-positions.
  - The vertical gap between two layers is constant across the whole face.
Real sections almost never look like that. If your boundaries do, you have
copied a shape instead of measuring - go back and read each line separately.

Also:
  - Sample points where each line BENDS (local highs/lows, slope changes), not
    mechanically at every grid label.
  - A truly flat stretch can use 2-3 points; a complex one needs many.
  - If a layer's top = the bottom of the layer above, leave topBoundary null.
  - Read each y off the metric bar; do not copy a neighbour's y.

============================================================
STEP 4 - LAYER INVENTORY
============================================================
List EVERY distinct layer on each face, matching fill patterns to the legend.
Faces may legitimately differ from one another - read each on its own evidence.
Within a face, do not skip or merge visibly distinct bands.

============================================================
STEP 5 - FEATURES
============================================================
- Traced outline (carbon lens, pit cut, trench-floor profile, stone-cluster
  outline): put geometry in `shapePoints` as (x, y), capturing real undulation.
- Single discrete object (one stone): use approxXMeters / approxYMeters /
  approxWidthMeters / approxHeightMeters. Numbers in the numeric fields; only
  prose in `description`.
- Assign each feature to the ONE layer it primarily sits in. If it spans layers,
  pick the primary layer and say so in its description - do NOT duplicate the
  same feature into multiple layers.
- Do NOT also duplicate the trench-floor profile as both a layer bottomBoundary
  and a separate feature - choose one (prefer the layer bottomBoundary for the
  deepest layer; only add a floor feature if it differs from that boundary).
- Take a feature's position from where it is DRAWN, not from where its label sits.

============================================================
STEP 6 - UNCERTAINTY
============================================================
If a point is faded/obscured/ambiguous/off-edge, set its coordinate(s) to null
and give the reason in that point's `confidence` field. Uncertainty is per
point/feature, not global.

============================================================
NO INTERPRETATION BEYOND WHAT IS DRAWN
============================================================
Do NOT infer history, chronology, period, or links to known events/buildings/
fires here or elsewhere. Do NOT say what a feature "likely represents" beyond
its observable physical description. Site background below is ONLY to read
labels correctly, not license to interpret. Report only what is visibly drawn,
labeled, or written. Transcribe unclear text/units EXACTLY as written.

============================================================
FIELDS TO FILL
============================================================
- metadata (currentFilePath, suggestedFilename = lowercase_underscored trench+
  year e.g. trench_23_1980, trenchLabel, scale, credits, marginalia)
- trenchProfiles[] (face, gridLabels, gridLabelXMeters, layers[])
- each layer: inferredMaterial, visualPattern, featuresInLayer, topBoundary,
  bottomBoundary
- legend[]
- inferred_notes[]: METHODOLOGY/READABILITY only (scale calibration, unreadable
  items, missing-metadata assumptions). NEVER historical interpretation.
- rawTranscription: your full natural-language reading of the drawing, for
  reference. Put narrative here; keep the structured fields clean and numeric.

Reference terms for reading labels only (do NOT inject unless written): Poggio
Aguzzo; Civitate A/B/C/D; Civitatine B; Piano del Tesoro / Tesoro and its Flanks/
Terraces/Rectangle; Agger; Lower Building / OC1; Courtyard.

Emit ONLY the JSON conforming to the schema.
"""


def _generate_with_retry(client, max_attempts=5, **kwargs):
    for attempt in range(max_attempts):
        try:
            return client.models.generate_content(**kwargs)
        except errors.ServerError as e:
            transient = getattr(e, "code", None) in (500, 503, 429)
            if transient and attempt < max_attempts - 1:
                wait = 2 ** attempt
                time.sleep(wait)
            else:
                raise


def run_extraction(image_path: str, out_path: str, api_key: str,
                    max_output_tokens: int = 65536, progress_cb=None):
    """Runs the single-agent illustrator-sheet extraction.
    Returns (raw_json_text, warning_or_None)."""
    if progress_cb:
        progress_cb("analyzing image (single agent)...")

    client = genai.Client(api_key=api_key,
                           http_options=types.HttpOptions(timeout=240_000))  # 4 min
    img = Image.open(image_path)
    orig_size = img.size
    img = _cap_for_sending(img)
    if img.size != orig_size and progress_cb:
        progress_cb(f"resized {orig_size[0]}x{orig_size[1]} -> {img.size[0]}x{img.size[1]} before sending to Gemini")
    prompt = PROMPT_TEMPLATE.format(image_path=image_path)

    response = _generate_with_retry(
        client,
        model="gemini-2.5-flash",
        contents=[img, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ArchaeologicalDiagram,
            temperature=0.1,
            max_output_tokens=max_output_tokens,
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
