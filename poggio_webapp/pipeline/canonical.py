"""One canonical section document that both capture schemas map into.

A field recording sheet and an illustrator sheet are two renderings of the
same trench wall. Everything downstream reads this shape instead of the
capture shape, so no consumer has to know which medium recorded a section.

Two mappings here are wider than the table in the parity plan, because
losslessness is enforced by a test and the narrower mapping dropped data:
`recorders` carries `{name, role}` objects rather than bare names, and a
locus entry's `confidence` rides inside `munsell`.
"""

from copy import deepcopy

CANONICAL_VERSION = 1

FIELD_WALL = "FieldWallProfile"
ILLUSTRATOR = "ArchaeologicalDiagram"

# The deepest drawn line on a section is the limit of excavation, not a
# deposit. It is modelled so the lowest unit has a floor, and named so
# nothing mistakes it for a locus.
BASE_SURFACE_ID = "Trench base"

# A field sheet declares itself by any of these, present even when null. The
# old detectors required layers[] to be a populated list, which is how a
# sheet with `layers: null` fell out of Harris source discovery in silence.
_FIELD_MARKERS = frozenset(
    {"faceLabel", "gridSquareCm", "gridTiePoints", "illustrators", "loci", "layers"}
)

IGNORED_CAPTURE_KEYS = frozenset(
    {
        # Writing-review UI only; already excluded from the model dump.
        "textCandidates",
        # Where the scan sat on the illustrator's own disk.
        "metadata.currentFilePath",
        "metadata.suggestedFilename",
    }
)

# Copied through untouched, so their inner keys need no individual mapping.
VERBATIM_CAPTURE_KEYS = frozenset({"finds", "legend", "metadata.scale"})

_POINT_KEYS = (
    "xMeters",
    "depthMeters",
    "xCoordinateMeters",
    "yCoordinateMeters",
    "confidence",
    "uncertaintyCm",
    "sourcePixel",
)


def _boundary_keys(prefix):
    return {prefix} | {f"{prefix}[].{key}" for key in _POINT_KEYS}


def _feature_keys(prefix, depth_key):
    named = (
        "feature",
        "description",
        "shapePoints",
        "approxXMeters",
        depth_key,
        "approxWidthMeters",
        "approxHeightMeters",
        "confidence",
    )
    return (
        {prefix}
        | {f"{prefix}[].{key}" for key in named}
        | _boundary_keys(f"{prefix}[].shapePoints")
    )


_FIELD_CAPTURE_KEYS = frozenset(
    {
        "trenchLabel",
        "faceLabel",
        "illustrators",
        "date",
        "northArrowPresent",
        "gridSquareCm",
        "gridTiePoints",
        "gridTiePoints[].rawText",
        "gridTiePoints[].approxXMeters",
        "loci",
        "loci[].locusNumber",
        "loci[].munsell",
        "loci[].munsell.raw",
        "loci[].munsell.colorName",
        "loci[].description",
        "loci[].confidence",
        "layers",
        "layers[].locusNumber",
        "layers[].featuresInLayer",
        "marginalia",
        "source",
    }
    | _boundary_keys("layers[].topBoundary")
    | _boundary_keys("layers[].bottomBoundary")
    | _feature_keys("layers[].featuresInLayer", "approxDepthMeters")
)

_ILLUSTRATOR_LAYER = "trenchProfiles[].layers[]"

_ILLUSTRATOR_CAPTURE_KEYS = frozenset(
    {
        "metadata",
        "metadata.trenchLabel",
        "metadata.credits",
        "metadata.credits.year",
        "metadata.credits.attributions",
        "metadata.credits.attributions[].name",
        "metadata.credits.attributions[].role",
        "metadata.marginalia",
        "trenchProfiles",
        "trenchProfiles[].face",
        "trenchProfiles[].gridLabels",
        "trenchProfiles[].gridLabelXMeters",
        "trenchProfiles[].layers",
        f"{_ILLUSTRATOR_LAYER}.layerName",
        f"{_ILLUSTRATOR_LAYER}.inferredMaterial",
        f"{_ILLUSTRATOR_LAYER}.description",
        f"{_ILLUSTRATOR_LAYER}.displayLabel",
        f"{_ILLUSTRATOR_LAYER}.visualPattern",
        "inferred_notes",
        "rawTranscription",
        "source",
    }
    | _boundary_keys(f"{_ILLUSTRATOR_LAYER}.topBoundary")
    | _boundary_keys(f"{_ILLUSTRATOR_LAYER}.bottomBoundary")
    | _feature_keys(f"{_ILLUSTRATOR_LAYER}.featuresInLayer", "approxYMeters")
)


def capture_keys(schema_type):
    """Every capture key this module maps, as dotted paths with [] for lists."""
    if schema_type == FIELD_WALL:
        return _FIELD_CAPTURE_KEYS
    if schema_type == ILLUSTRATOR:
        return _ILLUSTRATOR_CAPTURE_KEYS
    raise ValueError(f"unknown schema type {schema_type!r}")


def detect_schema(doc):
    """Which capture schema a document is, by one rule for the whole tree."""
    if isinstance(doc.get("trenchProfiles"), list):
        return ILLUSTRATOR
    if _FIELD_MARKERS.intersection(doc):
        return FIELD_WALL
    raise ValueError(
        "document matches neither capture schema: no trenchProfiles[] "
        "and no field-wall fields"
    )


def surface_id_for(label, schema_type):
    """The stable identity of a layer's model surface, never its colour.

    GemPy fuses interface points into one surface by exact string match on
    this value, so whatever is inside it is part of the deposit's identity.
    A Munsell reading is an observation about a deposit, not a name for one.
    """
    text = "" if label is None else str(label).strip()
    if not text:
        raise ValueError("label is required")
    if schema_type == FIELD_WALL:
        return f"Locus {text}"
    if schema_type == ILLUSTRATOR:
        return text
    raise ValueError(f"unknown schema type {schema_type!r}")


def is_canonical(doc):
    return isinstance(doc, dict) and doc.get("canonicalVersion") == CANONICAL_VERSION


def canonicalize(doc):
    """Map either capture schema onto the canonical document.

    Returns (canonical, warnings). Never writes; persistence is the caller's.
    """
    if is_canonical(doc):
        return deepcopy(doc), []

    schema_type = detect_schema(doc)
    warnings = []
    if schema_type == FIELD_WALL:
        document, faces = _from_field_wall(doc, warnings)
    else:
        document, faces = _from_illustrator(doc, warnings)

    for face in faces:
        _derive_boundaries(face["layers"], warnings)

    return {
        "canonicalVersion": CANONICAL_VERSION,
        "sourceSchema": schema_type,
        "source": doc.get("source") or "extraction",
        "document": document,
        "faces": faces,
        "finds": deepcopy(doc.get("finds") or []),
    }, warnings


def _point(raw):
    """Both legacy key pairs in, one truthful pair out: x along, depth down."""
    x = raw.get("xCoordinateMeters")
    if x is None:
        x = raw.get("xMeters")
    depth = raw.get("yCoordinateMeters")
    if depth is None:
        depth = raw.get("depthMeters")

    point = {
        "xMeters": x,
        "depthMeters": depth,
        "confidence": raw.get("confidence"),
        "uncertaintyCm": raw.get("uncertaintyCm"),
    }
    if raw.get("sourcePixel") is not None:
        point["sourcePixel"] = deepcopy(raw["sourcePixel"])
    return point


def _boundary(raw):
    return [_point(p) for p in raw or [] if isinstance(p, dict)]


def _feature(raw, depth_key):
    shape = raw.get("shapePoints")
    return {
        "feature": raw.get("feature"),
        "description": raw.get("description"),
        "shapePoints": _boundary(shape) if shape else None,
        "approxXMeters": raw.get("approxXMeters"),
        "approxDepthMeters": raw.get(depth_key),
        "approxWidthMeters": raw.get("approxWidthMeters"),
        "approxHeightMeters": raw.get("approxHeightMeters"),
        "confidence": raw.get("confidence"),
    }


def _display_label(surface, observation):
    """Identity first, the medium's observation in parentheses after it."""
    if observation and observation != surface:
        return f"{surface} ({observation})"
    return surface


def _munsell(raw, confidence):
    if isinstance(raw, str):
        text = raw.strip()
        return (
            {"raw": text, "colorName": None, "confidence": confidence} if text else None
        )
    if not isinstance(raw, dict):
        return None
    return {
        "raw": raw.get("raw"),
        "colorName": raw.get("colorName"),
        "confidence": confidence,
    }


def _munsell_text(munsell):
    if not munsell:
        return None
    parts = [munsell.get("raw"), munsell.get("colorName")]
    return " ".join(str(p).strip() for p in parts if p and str(p).strip()) or None


def _derive_boundaries(layers, warnings):
    """D1: a shared line drawn once still belongs to both layers that meet at it."""
    for index, layer in enumerate(layers):
        if layer["topBoundary"]:
            continue
        above = layers[index - 1] if index else None
        if above and above["bottomBoundary"]:
            layer["topBoundary"] = deepcopy(above["bottomBoundary"])
            layer["topBoundaryDerived"] = True
            warnings.append(
                f"{layer['surfaceId']} has no top boundary of its own; "
                f"derived it from the bottom of {above['surfaceId']}"
            )
        else:
            warnings.append(
                f"{layer['surfaceId']} has no top boundary and nothing above "
                "it to derive one from"
            )

    for index, layer in enumerate(layers):
        if layer["bottomBoundary"]:
            continue
        below = layers[index + 1] if index + 1 < len(layers) else None
        if below and below["topBoundary"]:
            layer["bottomBoundary"] = deepcopy(below["topBoundary"])
            layer["bottomBoundaryDerived"] = True
            warnings.append(
                f"{layer['surfaceId']} has no bottom boundary of its own; "
                f"derived it from the top of {below['surfaceId']}"
            )
        else:
            warnings.append(
                f"{layer['surfaceId']} has no bottom boundary and nothing "
                "below it to derive one from"
            )


def _from_field_wall(doc, warnings):
    face_name = doc.get("faceLabel") or doc.get("trenchLabel") or "field wall"

    # Duplicate locus numbers happen (T104 has two entries numbered 5); take
    # the first and say so rather than merging two readings into one.
    loci = {}
    for entry in doc.get("loci") or []:
        number = str(entry.get("locusNumber") or "").strip()
        if not number:
            continue
        if number in loci:
            warnings.append(
                f"locus {number} is listed more than once in loci[]; "
                "keeping the first reading"
            )
            continue
        loci[number] = entry

    layers = []
    claimed = set()
    for index, raw in enumerate(doc.get("layers") or []):
        number = str(raw.get("locusNumber") or "").strip()
        entry = loci.get(number) or {}
        claimed.add(number)

        if number:
            surface = surface_id_for(number, FIELD_WALL)
        else:
            surface = f"layer_{index}"
            warnings.append(
                f"layer at index {index} has no locusNumber, named {surface!r}"
            )

        munsell = _munsell(entry.get("munsell"), entry.get("confidence"))
        layers.append(
            {
                "label": number or None,
                "surfaceId": surface,
                "displayLabel": _display_label(surface, _munsell_text(munsell)),
                "munsell": munsell,
                "material": None,
                "visualPattern": None,
                "description": entry.get("description"),
                "topBoundary": _boundary(raw.get("topBoundary")),
                "topBoundaryDerived": False,
                "bottomBoundary": _boundary(raw.get("bottomBoundary")),
                "bottomBoundaryDerived": False,
                "features": [
                    _feature(f, "approxDepthMeters")
                    for f in raw.get("featuresInLayer") or []
                ],
                "provenance": {
                    "schemaType": FIELD_WALL,
                    "sourceFace": face_name,
                    "sourceLayerIndex": index,
                    "sourceLabel": raw.get("locusNumber"),
                },
            }
        )

    for number in loci:
        if number not in claimed:
            warnings.append(
                f"locus {number} is described in loci[] but no layer uses it, "
                "so its reading reaches nothing"
            )

    document = {
        "trenchLabel": doc.get("trenchLabel"),
        "recorders": [
            {"name": name, "role": None} for name in doc.get("illustrators") or []
        ],
        "date": doc.get("date"),
        "marginalia": list(doc.get("marginalia") or []),
        "northArrowPresent": doc.get("northArrowPresent"),
        "scale": {"gridSquareCm": doc.get("gridSquareCm"), "bar": None},
        "legend": [],
        "rawTranscription": None,
        "inferredNotes": [],
    }
    face = {
        "face": face_name,
        "gridRefs": [
            {
                "kind": "tiePoint",
                "rawText": tie.get("rawText"),
                "xMeters": tie.get("approxXMeters"),
            }
            for tie in doc.get("gridTiePoints") or []
        ],
        "layers": layers,
    }
    return document, [face]


def _from_illustrator(doc, warnings):
    metadata = doc.get("metadata") or {}
    credits = metadata.get("credits") or {}

    document = {
        "trenchLabel": metadata.get("trenchLabel"),
        "recorders": [
            {"name": a.get("name"), "role": a.get("role")}
            for a in credits.get("attributions") or []
        ],
        "date": credits.get("year"),
        "marginalia": list(metadata.get("marginalia") or []),
        "northArrowPresent": None,
        "scale": {"gridSquareCm": None, "bar": deepcopy(metadata.get("scale"))},
        "legend": deepcopy(doc.get("legend") or []),
        "rawTranscription": doc.get("rawTranscription"),
        "inferredNotes": list(doc.get("inferred_notes") or []),
    }

    faces = []
    for profile in doc.get("trenchProfiles") or []:
        face_name = profile.get("face")
        labels = profile.get("gridLabels") or []
        positions = profile.get("gridLabelXMeters") or []

        layers = []
        for index, raw in enumerate(profile.get("layers") or []):
            name = (raw.get("layerName") or "").strip()
            material = (raw.get("inferredMaterial") or "").strip()

            if name:
                surface = surface_id_for(name, ILLUSTRATOR)
            elif material:
                surface = surface_id_for(material, ILLUSTRATOR)
            else:
                surface = f"layer_{index}"
                warnings.append(
                    f"layer at index {index} has no layerName or "
                    f"inferredMaterial, named {surface!r}"
                )

            layers.append(
                {
                    "label": raw.get("layerName"),
                    "surfaceId": surface,
                    # A merged or adapted document already carries the label
                    # its own medium earned; recomputing it from the material
                    # would throw away a Munsell reading the merge resolved.
                    "displayLabel": raw.get("displayLabel")
                    or _display_label(surface, material or None),
                    "munsell": None,
                    "material": raw.get("inferredMaterial"),
                    "visualPattern": raw.get("visualPattern"),
                    "description": raw.get("description"),
                    "topBoundary": _boundary(raw.get("topBoundary")),
                    "topBoundaryDerived": False,
                    "bottomBoundary": _boundary(raw.get("bottomBoundary")),
                    "bottomBoundaryDerived": False,
                    "features": [
                        _feature(f, "approxYMeters")
                        for f in raw.get("featuresInLayer") or []
                    ],
                    "provenance": {
                        "schemaType": ILLUSTRATOR,
                        "sourceFace": face_name,
                        "sourceLayerIndex": index,
                        "sourceLabel": raw.get("layerName"),
                    },
                }
            )

        faces.append(
            {
                "face": face_name,
                # Padded to the longer of the two lists rather than zipped, so
                # a label with no position (or a position with no label) still
                # reaches the validator instead of vanishing in the shorter one.
                "gridRefs": [
                    {
                        "kind": "gridLabel",
                        "rawText": labels[i] if i < len(labels) else None,
                        "xMeters": positions[i] if i < len(positions) else None,
                    }
                    for i in range(max(len(labels), len(positions)))
                ],
                "layers": layers,
            }
        )

    return document, faces
