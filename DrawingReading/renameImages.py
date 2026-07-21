import os
from google import genai
from PIL import Image
from google.genai import types
from pydantic import BaseModel

class Scale(BaseModel):
    unit: str
    valuesMarked: list[int]
    confidence: str | None

class Credits(BaseModel):
    creator: str
    year: str

class NotableFeature(BaseModel):
    feature: str
    location: str
    shapePoints: list[BoundaryPoint] | None
    description: str


class BoundaryPoint(BaseModel):
    yCoordinateMeters: float | None
    xCoordinateMeters: float | None
    confidence: str | None

class Layer(BaseModel):
    layerName: str
    inferredMaterial: str
    description: str
    featuresInLayer: list[NotableFeature] | None
    topBoundary: list[BoundaryPoint] | None
    bottomBoundary: list[BoundaryPoint] | None

class LegendItem(BaseModel):
    visualPattern: str
    material: str

class TrenchProfile(BaseModel):
    face: str
    gridLabels: list[str]
    layers: list[Layer]

class Metadata(BaseModel):
    currentFilePath: str
    suggestedFilename: str
    trenchLabel: str
    scale: Scale
    credits: Credits
    marginalia: list[str]

class ArchaeologicalDiagram(BaseModel):
    metadata: Metadata
    trenchProfiles: list[TrenchProfile]
    legend: list[LegendItem]
    inferred_notes: list[str] | None = None


client = genai.Client()

def ProcessImageAgentically(imagePath: str):
    if not os.path.exists(imagePath):
        print("file not found: {imagePath}")
        return

    print("analyzing image...")
    img = Image.open('./images/qwertyTest.png')

    imageAnalysisAgentPrompt = f"""
        sYou are transcribing a single archaeological trench profile drawing into
structured, measurable data that will later be converted into a 3D geological
model (GemPy). Downstream software will treat your numbers as real
measurements, so accuracy and honest uncertainty matter far more than
completeness. A null value is always better than a plausible-sounding guess.
 
The dig is Poggio Civitate, Murlo, Italy. Transcribe the filePath as {imagePath}.
 
============================================================
COORDINATE SYSTEM  (use this exact convention for every number)
============================================================
- x = horizontal position ALONG the face, in METERS, measured from the LEFT
  edge of the drawn profile. The leftmost point of the profile is x = 0.
- depth = vertical distance DOWNWARD from the ground surface, in METERS,
  POSITIVE DOWNWARD. The top of the topsoil is depth = 0. A point 40 cm below
  the surface is depth = 0.4.
- Never use negative depth. Never mix the two axes.
 
============================================================
SCALE & GRID  (establish your rulers first, then measure)
============================================================
1. Find the scale bar and read its marked values (e.g. 0,1,2,3 m). This is
   your DEPTH ruler and your primary distance ruler.
2. Find the grid labels along the top of the profile. Estimate the x-position
   (in meters, from the left edge) of EACH grid label using the scale bar, and
   report them in `gridLabelXMeters` in the same order as `gridLabels`.
3. If the drawing has a non-metric or unfamiliar scale (e.g. an old "PECK"
   bar), do NOT silently convert it. Read its marked values as-is into the
   scale object, and if you relate it to meters by visual comparison, put that
   reasoning in `scale.metricConversionAssumption` as an explicit assumption
   (e.g. "1 PECK read as ~0.2 m by visual comparison to the metric bar;
   approximate"). Flag it — do not present it as established fact.
 
============================================================
LAYER BOUNDARIES  (the core of the GemPy data)
============================================================
For each layer, trace its bottom boundary (and its top boundary ONLY if that
top is drawn independently and differs from the layer above it) as a SERIES OF
POINTS across the face — never a single depth value.
- Place a point wherever the boundary crosses a grid label.
- Place extra points wherever the line visibly bends, dips, rises, or forms a
  feature (pit, U-shaped cut, undulation). Let the line's real complexity set
  the point count: a flat boundary may need 2-3 points; an irregular one many.
- Do NOT force a uniform number of points across layers.
- If a layer's top is simply the bottom of the layer above, leave its
  topBoundary null — do not duplicate the line.
- Measure each point: depth against the scale bar, x against the grid/scale.
 
============================================================
FEATURES  (stones, carbon lenses, pits, trench floor)
============================================================
- A feature with a traced outline (U-shaped carbon lens, pit cut, trench-floor
  profile, stone cluster edge) MUST have its geometry in `shapePoints` as
  (xCoordinateMeters, depthMeters) pairs — the SAME coordinate convention as
  boundaries. Do not bury coordinates inside prose.
- A single discrete object (one stone) with no meaningful traced outline: use
  approxXMeters / approxDepthMeters / approxWidthMeters / approxHeightMeters.
- Put descriptive prose in `description`; put numbers in the numeric fields.
 
============================================================
UNCERTAINTY  (flag, never fabricate)
============================================================
- If a boundary or point is faded, obscured, ambiguous, or runs off the edge
  of the drawing, set its coordinate value(s) to null and write the reason in
  that point's `confidence` field (e.g. "line faded near grid B",
  "estimated from neighbours", "runs off right edge").
- Use confidence at the point/feature level, not as a global note.
 
============================================================
NO INTERPRETATION BEYOND WHAT IS DRAWN
============================================================
- Do NOT infer historical context, chronology, period, or connections to known
  events, buildings, fires, or destruction layers here or at any site.
- Do NOT state what a feature "likely represents" beyond its directly
  observable physical description (material, shape, size, position).
- The Poggio Civitate background below is ONLY to help you read labels and
  abbreviations correctly. It is NOT license to add interpretation. If a term
  is not actually written on the drawing, do not introduce it.
- Report only what is visibly depicted, labeled, or written.
 
============================================================
TRANSCRIPTION FIDELITY
============================================================
- Transcribe any unclear/unfamiliar text, label, abbreviation, or unit EXACTLY
  as written. Do not expand or guess its meaning.
- Signatures and dates are usually in the bottom corners.
 
============================================================
inferred_notes  (you, the vision agent, own this field)
============================================================
Because only you can see the image, YOU write inferred_notes. Restrict them to
METHODOLOGY and READABILITY:
  - how a measurement or scale conversion was estimated and why,
  - what was unreadable/ambiguous and how you handled it,
  - which metadata was missing and what you assumed.
NEVER put archaeological or historical interpretation in inferred_notes.
 
Reference terms for reading labels only (do NOT inject these unless written on
the drawing): Poggio Aguzzo (necropolis); Civitate A/B/C/D and Civitatine B
(property/trench zones); Piano del Tesoro / Tesoro and its Flanks, Terraces,
and Rectangle (excavation zones); Agger (earthwork mound); Lower Building /
OC1; Courtyard.
 
============================================================
COMPLETENESS CHECKLIST  (your transcription MUST supply all of this)
============================================================
A separate agent will structure your description into a fixed schema. It CANNOT
see the image — if you omit something here, it is lost. Before you finish,
confirm your description explicitly provides every item below. Where a value is
genuinely unreadable, say so and why (do not just leave it out silently).
 
Document level:
  [ ] trench label (e.g. "T 23")
  [ ] scale bar: unit and the marked values (e.g. 0,1,2,3 m)
  [ ] if a non-metric/unfamiliar scale: its marked values as-is + your explicit
      meters assumption ("1 PECK read as ~0.2 m, approximate")
  [ ] creator and year (usually bottom corners); say "not stated" if absent
  [ ] all marginalia text, transcribed verbatim
  [ ] the legend: every visual pattern paired with its material
 
For EACH face (e.g. East, South, West):
  [ ] the face name
  [ ] the grid labels along the top, in order
  [ ] the x-position IN METERS (from left edge) of each grid label
 
For EACH layer, top to bottom:
  [ ] layer order/name and its material
  [ ] the visual pattern that denotes it
  [ ] its BOTTOM boundary as a list of (x meters, depth meters) points, with
      extra points at every bend/dip/feature — not a single depth
  [ ] its TOP boundary ONLY if drawn independently of the layer above; else
      state "top = bottom of layer above"
  [ ] any per-point uncertainty (faded, estimated, off-edge)
 
For EACH feature (stone, carbon lens, pit, trench floor):
  [ ] which layer it sits in
  [ ] traced outlines (U-shaped lens, pit cut, floor profile) as a list of
      (x meters, depth meters) points
  [ ] discrete objects (a stone) as approx x, depth, width, height in meters
  [ ] a short physical description (no interpretation)
 
Methodology notes (for inferred_notes):
  [ ] how any measurement/scale conversion was estimated
  [ ] what was unreadable/ambiguous and how you handled it
  [ ] which metadata was missing and what you assumed
 
Now produce a thorough, measurement-focused natural-language transcription that
covers every checklist item above, layer by layer and face by face.
    """

    imageAnalysisAgentResponse = client.models.generate_content(
        model = 'gemini-2.5-flash',
        contents= [img, imageAnalysisAgentPrompt]
    )

    description = imageAnalysisAgentResponse.text
    print(f"Description: ", description)


    print("\n  Structuring Data into JSON...")

    dataStructuringAgentPrompt = f"""
        Convert the archaeological trench description below into JSON matching the
schema exactly. You are a FAITHFUL TRANSCRIBER of the description — you did not
see the image, so you must not add, infer, or embellish anything.
 
Rules:
- Use ONLY information present in the description. If the description doesn't
  state something, leave it null. Never invent coordinates, confidences, or
  notes.
- Coordinate convention: x = meters along the face from the left edge;
  depth = meters positive DOWNWARD from the surface. Copy the numbers the
  description gives; do not recompute or "clean up" values.
- Boundaries: populate bottomBoundary (and topBoundary only when the
  description says the top is drawn independently) as point lists with
  xCoordinateMeters + depthMeters, carrying over any per-point confidence
  the description mentions.
- Features: if the description gives a traced outline (e.g. a U-shaped carbon
  lens with listed points), put those in `shapePoints`. If it gives a single
  location/size for a discrete object, use the approx* fields. Put descriptive
  prose in `description`.
- Map visual patterns to materials via the legend.
- CurrentFilePath must be exactly: {imagePath}
- suggestedFilename: lowercase, underscores, no extension, combining trench
  label and year (e.g. trench_23_1980).
- inferred_notes: copy ONLY the methodological/readability notes already
  present in the description. DO NOT create new notes, and DO NOT add any
  historical, chronological, or interpretive content. If the description has no
  such notes, use an empty list or null.
 
Description:
{description}
    """

    dataStructuringAgentResponse = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=dataStructuringAgentPrompt,
        config= types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ArchaeologicalDiagram,
            temperature=0.1
        )
    )

    rawJson = dataStructuringAgentResponse.text
    print(f"here is the raw json: {rawJson} ")

    ## extractedData: ArchaeologicalDiagram = dataStructuringAgentResponse.parsed
    ## print(f"here is the image data: {extractedData}")

if __name__ == "__main__":
    ProcessImageAgentically('./images/qwertyTest.png')

