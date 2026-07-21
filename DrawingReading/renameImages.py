import os
import time
from google import genai
from google.genai import errors
from PIL import Image
from google.genai import types
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# SCHEMA  (single-agent variant)
#
# Same coordinate convention as the two-agent version:
#   x = horizontal position ALONG the face (meters, 0 at the left edge).
#   y = depth DOWNWARD from the surface (meters, positive down, 0 at surface).
# Face-local; site-wide X/Y/Z conversion is a separate deterministic step.
#
# The one addition vs the two-agent schema is `rawTranscription` on the top
# object: since there's no separate description pass, we keep the model's own
# narrative here so nothing is lost.
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
    # Single-agent only: the model's own narrative pass, kept for reference.
    rawTranscription: str | None = None


client = genai.Client()


def generate_with_retry(max_attempts: int = 5, **kwargs):
    """Retry transient server errors (503/500/429) with exponential backoff."""
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


def ProcessImageSingleAgent(imagePath: str):
    if not os.path.exists(imagePath):
        print(f"file not found: {imagePath}")
        return

    print("analyzing image (single agent)...")
    img = Image.open(imagePath)

    prompt = f"""
You are transcribing a single archaeological trench profile drawing DIRECTLY
into the provided JSON schema. There is no second pass - what you emit IS the
final data, and downstream software (GemPy) treats your numbers as real
measurements. Measurement fidelity and honest uncertainty matter far more than
completeness. A null value is always better than a plausible-sounding guess.

The dig is Poggio Civitate, Murlo, Italy. Set metadata.currentFilePath to
exactly {imagePath}.

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

    response = generate_with_retry(
        model='gemini-2.5-flash',
        contents=[img, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ArchaeologicalDiagram,
            temperature=0.1
        )
    )

    rawJson = response.text
    print(f"here is the raw json: {rawJson} ")

    with open("output_single.json", "w") as f:
        f.write(rawJson)

    extractedData: ArchaeologicalDiagram = response.parsed
    return extractedData


if __name__ == "__main__":
    import sys
    imagePath = sys.argv[1] if len(sys.argv) > 1 else './images/qwertyTest.png'
    ProcessImageSingleAgent(imagePath)