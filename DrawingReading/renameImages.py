import os
from google import genai
from PIL import Image
from google.genai import types
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# SCHEMA
#
# Coordinate convention:
#   x = horizontal position ALONG the face (meters, 0 at the left edge).
#   y = depth DOWNWARD from the ground surface (meters, positive down, 0 at
#       the top of the topsoil).
# These are FACE-LOCAL coordinates. Converting to site-wide X/Y/Z is a
# separate deterministic step and is never done by the LLM.
#
# NOTE: BoundaryPoint must be defined BEFORE NotableFeature, because
# NotableFeature.shapePoints references it.
# ---------------------------------------------------------------------------

class Scale(BaseModel):
    unit: str | None
    valuesMarked: list[int]
    metricConversionAssumption: str | None = None
    confidence: str | None = None


class Credits(BaseModel):
    creator: str | None
    year: str | None


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


client = genai.Client()


def ProcessImageAgentically(imagePath: str):
    if not os.path.exists(imagePath):
        print(f"file not found: {imagePath}")
        return

    print("analyzing image...")
    img = Image.open('./images/qwertyTest.png')

    imageAnalysisAgentPrompt = f"""
You are transcribing a single archaeological trench profile drawing into
structured, measurable data that will later be converted into a 3D geological
model (GemPy). Downstream software treats your numbers as real measurements, so
measurement fidelity and honest uncertainty matter far more than completeness.
A null value is always better than a plausible-sounding guess.

The dig is Poggio Civitate, Murlo, Italy. Transcribe the filePath as {imagePath}.

============================================================
COORDINATE SYSTEM  (use this exact convention for every number)
============================================================
- x = horizontal position ALONG the face, in METERS, measured from the LEFT
  edge of that face's drawn profile. The leftmost point of each face is x = 0.
  Each face has its own independent x origin.
- y = depth DOWNWARD from the ground surface, in METERS, POSITIVE DOWNWARD.
  The ground surface is y = 0; a point 40 cm below the surface is y = 0.4.
- Never use negative y. Never mix the two axes.

============================================================
STEP 1 - READ THE SCALE BAR CAREFULLY  (do this before any measuring)
============================================================
Scale bars vary between drawings. Some have a SINGLE bar; some have TWO stacked
bars (e.g. an old unit like "PECK" on one line and a metric "0 1 2 3 M" scale on
another). Do not assume which case you are in - look at what is actually printed.

- Identify every scale present and read its printed values verbatim into the
  `scale` object (unit + valuesMarked).
- If there are TWO bars, choose the METRIC one (marked in M / meters) as the
  ONLY ruler you measure with. Use it for BOTH depth (y) and horizontal (x)
  distances. Do NOT measure with a non-metric bar.
- If a non-metric bar is present, record it and, if you relate it to meters,
  put that reasoning in `scale.metricConversionAssumption` as an explicit,
  flagged assumption (e.g. "1 PECK read as ~0.2 m vs the metric bar;
  approximate"). Never silently convert; never measure the drawing with it.
- If ONLY a non-metric bar exists, measure in its units, state the unit
  honestly, and flag the conversion assumption. Do not pretend it is metric.
- Establish how many drawn units = 1 meter on the metric bar, then apply that
  same ratio consistently to every x and y. Sanity-check each face's total width
  against the bar: if a face looks ~4-5 m wide, its x values should span ~4-5,
  not compress to 3.

============================================================
STEP 2 - GRID LABELS
============================================================
Find the grid labels along the top of each face. Using the metric bar, estimate
the x-position IN METERS (from that face's left edge) of EACH label, and report
them in `gridLabelXMeters` in the same order as `gridLabels`. Grid labels are a
horizontal REFERENCE - they are NOT where you must place boundary points (see
Step 3). Boundary points may fall between, before, or after grid labels.

============================================================
STEP 3 - TRACE BOUNDARIES BY THEIR ACTUAL SHAPE  (the core task)
============================================================
For each layer, trace its bottom boundary (and its top boundary ONLY if drawn
independently and different from the layer above) as a series of (x, y) points.

CRITICAL: follow the DRAWN LINE'S SHAPE. Boundaries in these drawings undulate -
they sag into basins, rise over humps, dip into cuts. Your points must capture
that shape, so the y VALUE CHANGES from point to point along the line.

- Sample a point wherever the line BENDS: every local high, every local low,
  every clear change of slope. Put points where the geometry happens.
- Between bends, on a genuinely straight run, 2-3 points suffice.
- A grid label is worth a point only if it adds shape information; do NOT place
  a point at every grid label out of habit.
- Read each point's y off the metric bar independently. Do not copy a neighbour's
  y unless the line is truly flat there.

ANTI-FLATNESS SELF-CHECK (apply before finalizing each boundary):
  If most or all points on a boundary share the same y value, you have almost
  certainly NOT measured - you have assumed a flat line. Real boundaries here are
  rarely flat. Go back to that line, find its high and low points, and re-read
  the depths. A boundary reported as a single repeated y is a red flag that the
  measurement was skipped.

If a layer's top is simply the bottom of the layer above, leave topBoundary
null - do not duplicate the line.

============================================================
STEP 4 - LAYER INVENTORY  (do not drop layers)
============================================================
Work top to bottom and list EVERY distinct layer you can see on each face,
matching its fill pattern to the legend. Faces can legitimately differ from one
another (a narrower/deeper cut may have a different sequence) - report each face
on its own evidence rather than copying another face. But within a single face,
do not skip or merge bands that are visibly distinct. If two bands are hard to
tell apart, include both and flag the uncertainty rather than dropping one.

============================================================
STEP 5 - FEATURES  (stones, carbon lenses, pits, trench floor)
============================================================
- A feature with a traced OUTLINE (a carbon lens/streak, a pit cut, the trench-
  floor profile, the outline of a stone cluster) goes in `shapePoints` as (x, y)
  points, same convention as boundaries, capturing its real undulation. Carbon
  lenses here visibly dip and swell - trace that, do not flatten it.
- A single discrete object (one stone) goes in the numeric fields
  approxXMeters / approxYMeters / approxWidthMeters / approxHeightMeters. Put the
  NUMBERS in those fields; put only prose in `description`.
- Record each feature's position from where it is actually DRAWN, not from where
  its text label sits - labels are often offset from the thing they name (e.g. a
  "LARGE STONES" label may sit above or beside a cluster drawn lower down).
- Note which layer each feature sits in.

============================================================
STEP 6 - UNCERTAINTY  (flag, never fabricate)
============================================================
- If a point is faded, obscured, ambiguous, or runs off the drawing's edge, set
  its coordinate value(s) to null and give the reason in that point's
  `confidence` field (e.g. "line faded near grid B", "runs off right edge").
- Uncertainty lives at the point/feature level, not as a global note.

============================================================
NO INTERPRETATION BEYOND WHAT IS DRAWN
============================================================
- Do NOT infer historical context, chronology, period, or links to known events,
  buildings, fires, or destruction layers, here or at any site.
- Do NOT state what a feature "likely represents" beyond its observable physical
  description (material, shape, size, position).
- The Poggio Civitate background below is ONLY to help you read labels and
  abbreviations. It is NOT license to add interpretation. If a term is not
  written on the drawing, do not introduce it.
- Report only what is visibly depicted, labeled, or written.

============================================================
TRANSCRIPTION FIDELITY
============================================================
- Transcribe unclear/unfamiliar text, labels, abbreviations, and units EXACTLY
  as written. Do not expand or guess meanings.
- Signatures and dates are usually in the bottom corners.

============================================================
inferred_notes  (you, the vision agent, own this field)
============================================================
Because only you can see the image, YOU write inferred_notes - restricted to
METHODOLOGY and READABILITY only:
  - how you read/calibrated the scale bar and any unit conversion,
  - what was unreadable/ambiguous and how you handled it,
  - which metadata was missing and what you assumed.
NEVER put archaeological or historical interpretation in inferred_notes.

Reference terms for reading labels only (do NOT inject unless written on the
drawing): Poggio Aguzzo (necropolis); Civitate A/B/C/D and Civitatine B
(property/trench zones); Piano del Tesoro / Tesoro and its Flanks, Terraces,
and Rectangle (excavation zones); Agger (earthwork mound); Lower Building /
OC1; Courtyard.

============================================================
COMPLETENESS CHECKLIST  (your transcription MUST supply all of this)
============================================================
A separate agent will structure your description into a fixed schema. It CANNOT
see the image - if you omit something, it is lost. Confirm you provide every
item; where a value is genuinely unreadable, say so and why.

Document level:
  [ ] trench label
  [ ] scale bar(s): how many, each unit, each set of marked values
  [ ] which bar you measured with, and (if any) the non-metric conversion
      assumption
  [ ] creator and year (usually bottom corners); say "not stated" if absent
  [ ] all marginalia text, verbatim
  [ ] the legend: every visual pattern paired with its material

For EACH face:
  [ ] the face name
  [ ] the grid labels in order, and each label's x-position in meters
  [ ] the approximate total width of the face in meters (from the metric bar)

For EACH layer, top to bottom:
  [ ] name/material and the legend pattern that denotes it
  [ ] its BOTTOM boundary as (x, y) points that follow the line's real shape,
      with y varying at every bend - NOT a single repeated y
  [ ] TOP boundary only if drawn independently; else "top = bottom of above"
  [ ] any per-point uncertainty

For EACH feature:
  [ ] which layer it sits in
  [ ] traced outlines as (x, y) points; discrete objects as approx x/y/width/
      height in meters
  [ ] a short physical description (no interpretation)
  [ ] position taken from where it is DRAWN, not from its label

Methodology notes (inferred_notes): scale calibration, unreadable items, missing
metadata assumptions.

Now produce a thorough, measurement-focused transcription that follows the steps
above, face by face and layer by layer. Prioritise reading the true undulating
shape of every boundary over speed.
"""

    imageAnalysisAgentResponse = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[img, imageAnalysisAgentPrompt]
    )

    description = imageAnalysisAgentResponse.text
    print("Description: ", description)

    print("\n  Structuring Data into JSON...")

    dataStructuringAgentPrompt = f"""
Convert the archaeological trench description below into JSON matching the schema
exactly. You are a FAITHFUL TRANSCRIBER of the description - you did NOT see the
image, so never add, infer, recompute, or embellish. Copy what the description
states into the correct fields.

GENERAL RULES
- Use ONLY information present in the description. If it does not state something,
  use a real JSON null - never the string "null".
- Coordinate convention: x = meters along the face from the left edge;
  y (yCoordinateMeters) = meters positive DOWNWARD. Copy numbers verbatim; do not
  clean up, round, or flatten them.
- Boundaries: populate bottomBoundary (and topBoundary only when the description
  says the top is drawn independently) as point lists of
  {{xCoordinateMeters, yCoordinateMeters}}, carrying over any per-point confidence.
  Preserve the varying y values exactly as given - do NOT collapse them to one.
- Map visual patterns to materials via the legend.
- currentFilePath must be exactly: {imagePath}
- suggestedFilename: lowercase, underscores, no extension, trench label + year
  (e.g. trench_23_1980).
- inferred_notes: copy ONLY the methodological/readability notes already in the
  description. Do NOT invent notes or add any historical/interpretive content.
  If there are none, use an empty list or null.

FEATURES - READ THIS CAREFULLY
Each feature is EITHER a traced outline OR a discrete object. Route its numbers to
the correct fields and keep them OUT of the description string.

- Traced outline (carbon lens, pit cut, trench floor, stone-cluster outline):
  put its listed points in `shapePoints`. `description` holds prose only.

- Discrete object (a single stone): parse its approximate measurements into the
  numeric fields approxXMeters, approxYMeters, approxWidthMeters,
  approxHeightMeters. `description` holds prose only - it must NOT contain the
  coordinates or dimensions.

  WORKED EXAMPLE - given this in the description:
      Feature: Stone (discrete object)
        Layer: TOP SOIL
        Description: A large rounded stone projecting above the surface.
        approxXMeters: 0.15
        approxYMeters: 0.05
        approxWidthMeters: 0.10
        approxHeightMeters: 0.10
  emit exactly:
      {{
        "feature": "Stone",
        "description": "A large rounded stone projecting above the surface.",
        "shapePoints": null,
        "approxXMeters": 0.15,
        "approxYMeters": 0.05,
        "approxWidthMeters": 0.10,
        "approxHeightMeters": 0.10,
        "confidence": null
      }}
  The four numbers went into the numeric fields; the description kept ONLY the
  sentence. Never leave "Approx x: 0.15m ..." inside the description.

Description:
{description}
"""

    dataStructuringAgentResponse = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=dataStructuringAgentPrompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ArchaeologicalDiagram,
            temperature=0.1
        )
    )

    rawJson = dataStructuringAgentResponse.text
    print(f"here is the raw json: {rawJson} ")

    with open("output.json", "w") as f:
        f.write(rawJson)

    extractedData: ArchaeologicalDiagram = dataStructuringAgentResponse.parsed
    return extractedData


if __name__ == "__main__":
    ProcessImageAgentically('./images/qwertyTest.png')