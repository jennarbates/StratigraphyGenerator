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
        Look at this image. Transcribe everything you see in the image and describe any pictures. Be precise and include as much detail as possible. Include the filePath as {imagePath}. Accurately categorize the stratigraphy descriptions and notable features for each specific trench face (e.g. East face, South Face). If any metadata is missing, let me know and provide an inference for what it could be and why. Be as descriptive as possible with the visual patterns that might describe different elevations. Keep in mind the grid and where things are in the grid. If there are any rocks or tree stumps or stones that are visibly drawn in the layers, take note of those and which layer they are in and where.

        You are transcribing an archaeological trench profile drawing into structured data. 
        Accuracy and honesty about uncertainty matter more than completeness — a null value 
        is far better than a plausible-sounding guess.

        SCALE REFERENCE: Identify the scale bar and its marked values (e.g., 0, 1, 2, 3 
        meters). Use this as your ruler for all depth measurements. Identify the grid 
        labels along the top of the profile and use their horizontal spacing as your 
        ruler for x-position measurements.

        LAYER BOUNDARIES: For each layer, trace its top and bottom boundary as a series 
        of points along the face — NOT a single depth value. A layer's boundary is 
        rarely flat: capture the actual shape as drawn.
        - Place a point at every grid label intersection the boundary crosses.
        - Place additional points wherever the boundary visibly bends, dips, rises, 
            or forms a distinct feature (e.g., a pit, a U-shaped cut, an undulation).
        - Flat, unremarkable boundaries may need only 2-3 points. Complex or irregular 
            boundaries may need many more. Let the actual line's complexity determine 
            point count — do not force a uniform number of points across all layers.
        - Measure each point's depth against the scale bar and x-position against the 
            grid labels, as precisely as the drawing allows.

         UNCERTAINTY: If a boundary is faded, obscured, ambiguous, or extends outside 
            the visible drawing, do NOT estimate or interpolate a plausible-looking value. 
            Leave the coordinate values as null, and note the issue in a "confidence" 
            field (e.g., "boundary faded near grid square B", "line unclear, estimated 
            from adjacent points").

 NO INTERPRETATION BEYOND WHAT IS DRAWN: Do not infer historical context, site 
   chronology, archaeological period, or connections to known events, buildings, 
   or destruction layers at this or any other site. Do not guess what a feature 
   "likely represents" beyond its directly observable physical description 
   (material, shape, approximate size, position). Report only what is visibly 
   depicted, labeled, or written on the drawing itself.

If any text, label, or unit on the drawing is unclear or unfamiliar (e.g., 
   an abbreviation you don't recognize), transcribe it exactly as written rather 
   than guessing its meaning or expanding it.

Output must conform exactly to the provided schema.

        Drawing signatures and dates tend to be in the bottom corners.

        The dig that these images are from is Poggio Civitate in Murlo, Italy
        - Here are some terms that are important to Poggio Civitate:
            - Poggio Aguzzo: A neighboring hill situated just a short distance from the main Poggio Civitate settlement. It served as the site's primary necropolis (cemetery). The tombs discovered here yielded many of the grave goods now exhibited in the Murlo archaeological museum.
            - Civitate A: A modern property zone and excavation macro-area lying immediately west of the main Piano del Tesoro plateau.
            - Civitate B, Civitate C, and Civitate D: Similarly designated modern cadastral parcels or property zones used by archaeologists to group and identify excavation trenches around the hill.
            - Civitatine B: A subdivision of the broader "Civitatine" area. This is tied to historical local pathways (like the Via delle Civitate e Civitatine) and serves as a localized trench designation in the site's records.
            - The Piano del Tesoro (Main Plateau): The summit of the Poggio Civitate hill is heavily terraced and subdivided by archaeologists to track where the monumental Etruscan complexes were found.
            - Tesoro (Piano del Tesoro): The primary, flattened plateau at the very top of the hill. This is the main excavation zone where both the Orientalizing and Archaic monumental buildings were discovered.
            - Tesoro North Flank & Tesoro South Flank: Specific excavation zones positioned along the northern and southern edges of the main plateau.
            - Tesoro South Terrace, East Terrace, & North Terrace: Terraced areas extending down off the edges of the main Tesoro plateau. These flanks often contain debris, architectural terracottas, and domestic remains that washed or were pushed down from the main complexes above.
            - Tesoro Rectangle: A specific designated excavation trench or architectural grid area located on the main plateau.
            
            - Agger: An earthwork or defensive mound. When the monumental Archaic building was destroyed and ritually buried around 525 BCE, its pisé (rammed earth) walls were deliberately pulled down and scraped to the western edges of the Piano del Tesoro to form this mound. The agger effectively sealed and preserved the foundations underneath it.
            - Lower Building: Also referred to as Orientalizing Complex 1 (OC1) or the "Residence." This was a monumental building from the earlier Orientalizing period that was destroyed by a massive fire around 590–580 BCE. It is called "Lower" because its structural remains were discovered stratigraphically beneath the foundations of the later Archaic period building.
            - Courtyard: The large central open-air space of the monumental Archaic Building (built early 6th century BCE). The complex consisted of four flanking structures that completely surrounded this central, colonnaded court

            Break down the stratigraphy into distinct 'layers' and take note of their order from top to bottom, their material, and any other important information. If there are any notable features within each layer (like a rock or a tree stump) take note of that.
    
            Using the provided scale and the grid, provide an estimate of depth, size of objects, and any other useful information
    """

    imageAnalysisAgentResponse = client.models.generate_content(
        model = 'gemini-2.5-flash',
        contents= [img, imageAnalysisAgentPrompt]
    )

    description = imageAnalysisAgentResponse.text
    print(f"Description: ", description)


    print("\n  Structuring Data into JSON...")

    dataStructuringAgentPrompt = f"""
        Read the following archaeological image description and extract the relevant information to populate the JSON schema.
    
        Extraction Rules:
        - Map all visual patterns (like "stippling" or "crosshatching") to their identified materials in the legend.
        - Accurately categorize the stratigraphy descriptions and notable features for each specific trench face (e.g., East Face, South Face).
        - If there is any information that was inferred, include that as a note rather than in the other parts of the json. Include how it was inferred and why.
        - The CurrentFilePath must be recorded exactly as: {imagePath}
        - Generate a descriptive 'suggested_filename' combining the trench name and year. Use strictly lowercase letters, separate words with underscores, and do not include the file extension. (e.g., trench_23_carbon_layer_profile)
        - If you observe historical context, tentative interpretations, or extra details that do not fit into the standard categories, add them as separate strings in the inferred_notes array
        - Don't include repetitive phrasing.
        Image Description:
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

