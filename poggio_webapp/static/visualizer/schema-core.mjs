// The browser-side canonicalizer. A canonical document passes through
// untouched; either capture shape (and old saved trenchProfiles documents)
// is mapped to the canonical form exactly as pipeline/canonical.py maps it.
// schema-core.test.mjs locks the two against committed fixtures, so keep
// every rule here in step with that module.

const CANONICAL_VERSION = 1;
const FIELD_WALL = "FieldWallProfile";
const ILLUSTRATOR = "ArchaeologicalDiagram";
const FIELD_MARKERS = [
  "faceLabel", "gridSquareCm", "gridTiePoints", "illustrators", "loci", "layers",
];

function surfaceIdFor(label, schemaType) {
  const text = String(label ?? "").trim();
  return schemaType === FIELD_WALL ? `Locus ${text}` : text;
}

function displayLabel(surface, observation) {
  if (observation && observation !== surface) return `${surface} (${observation})`;
  return surface;
}

function munsell(raw, confidence) {
  if (typeof raw === "string") {
    const text = raw.trim();
    return text ? { raw: text, colorName: null, confidence } : null;
  }
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  return {
    raw: raw.raw ?? null,
    colorName: raw.colorName ?? null,
    confidence,
  };
}

function munsellText(reading) {
  if (!reading) return null;
  const parts = [reading.raw, reading.colorName]
    .filter(part => part && String(part).trim())
    .map(part => String(part).trim());
  return parts.join(" ") || null;
}

function point(raw) {
  const mapped = {
    xMeters: raw.xCoordinateMeters ?? raw.xMeters ?? null,
    depthMeters: raw.yCoordinateMeters ?? raw.depthMeters ?? null,
    confidence: raw.confidence ?? null,
    uncertaintyCm: raw.uncertaintyCm ?? null,
  };
  if (raw.sourcePixel != null) mapped.sourcePixel = structuredClone(raw.sourcePixel);
  return mapped;
}

function boundary(raw) {
  return (raw || []).filter(p => p && typeof p === "object").map(point);
}

function feature(raw, depthKey) {
  const shape = raw.shapePoints;
  return {
    feature: raw.feature ?? null,
    description: raw.description ?? null,
    shapePoints: shape && shape.length ? boundary(shape) : null,
    approxXMeters: raw.approxXMeters ?? null,
    approxDepthMeters: raw[depthKey] ?? null,
    approxWidthMeters: raw.approxWidthMeters ?? null,
    approxHeightMeters: raw.approxHeightMeters ?? null,
    confidence: raw.confidence ?? null,
  };
}

// D1: a shared line drawn once still belongs to both layers that meet at it.
function deriveBoundaries(layers) {
  layers.forEach((layer, index) => {
    if (layer.topBoundary.length) return;
    const above = index ? layers[index - 1] : null;
    if (above && above.bottomBoundary.length) {
      layer.topBoundary = structuredClone(above.bottomBoundary);
      layer.topBoundaryDerived = true;
    }
  });
  layers.forEach((layer, index) => {
    if (layer.bottomBoundary.length) return;
    const below = index + 1 < layers.length ? layers[index + 1] : null;
    if (below && below.topBoundary.length) {
      layer.bottomBoundary = structuredClone(below.topBoundary);
      layer.bottomBoundaryDerived = true;
    }
  });
}

function wrap(d, schemaType, document, faces) {
  faces.forEach(face => deriveBoundaries(face.layers));
  return {
    canonicalVersion: CANONICAL_VERSION,
    sourceSchema: schemaType,
    source: d.source || "extraction",
    document,
    faces,
    finds: structuredClone(d.finds || []),
  };
}

function fromFieldWall(d) {
  const faceName = d.faceLabel || d.trenchLabel || "field wall";

  const loci = {};
  (d.loci || []).forEach(entry => {
    const number = String(entry.locusNumber || "").trim();
    if (number && !(number in loci)) loci[number] = entry;
  });

  const layers = (d.layers || []).map((raw, index) => {
    const number = String(raw.locusNumber || "").trim();
    const entry = loci[number] || {};
    const surface = number ? surfaceIdFor(number, FIELD_WALL) : `layer_${index}`;
    const reading = munsell(entry.munsell, entry.confidence ?? null);
    return {
      label: number || null,
      surfaceId: surface,
      displayLabel: displayLabel(surface, munsellText(reading)),
      munsell: reading,
      material: null,
      visualPattern: null,
      description: entry.description ?? null,
      topBoundary: boundary(raw.topBoundary),
      topBoundaryDerived: false,
      bottomBoundary: boundary(raw.bottomBoundary),
      bottomBoundaryDerived: false,
      features: (raw.featuresInLayer || []).map(f => feature(f, "approxDepthMeters")),
      provenance: {
        schemaType: FIELD_WALL,
        sourceFace: faceName,
        sourceLayerIndex: index,
        sourceLabel: raw.locusNumber ?? null,
      },
    };
  });

  const document = {
    trenchLabel: d.trenchLabel ?? null,
    recorders: (d.illustrators || []).map(name => ({ name, role: null })),
    date: d.date ?? null,
    marginalia: [...(d.marginalia || [])],
    northArrowPresent: d.northArrowPresent ?? null,
    scale: { gridSquareCm: d.gridSquareCm ?? null, bar: null },
    legend: [],
    rawTranscription: null,
    inferredNotes: [],
  };
  const face = {
    face: faceName,
    gridRefs: (d.gridTiePoints || []).map(tie => ({
      kind: "tiePoint",
      rawText: tie.rawText ?? null,
      xMeters: tie.approxXMeters ?? null,
    })),
    layers,
  };
  return wrap(d, FIELD_WALL, document, [face]);
}

function fromIllustrator(d) {
  const metadata = d.metadata || {};
  const credits = metadata.credits || {};

  const document = {
    trenchLabel: metadata.trenchLabel ?? null,
    recorders: (credits.attributions || []).map(a => ({
      name: a.name ?? null,
      role: a.role ?? null,
    })),
    date: credits.year ?? null,
    marginalia: [...(metadata.marginalia || [])],
    northArrowPresent: null,
    scale: { gridSquareCm: null, bar: structuredClone(metadata.scale ?? null) },
    legend: structuredClone(d.legend || []),
    rawTranscription: d.rawTranscription ?? null,
    inferredNotes: [...(d.inferred_notes || [])],
  };

  const faces = (d.trenchProfiles || []).map(profile => {
    const labels = profile.gridLabels || [];
    const positions = profile.gridLabelXMeters || [];

    const layers = (profile.layers || []).map((raw, index) => {
      const name = (raw.layerName || "").trim();
      const material = (raw.inferredMaterial || "").trim();
      const surface = name
        ? surfaceIdFor(name, ILLUSTRATOR)
        : material
          ? surfaceIdFor(material, ILLUSTRATOR)
          : `layer_${index}`;
      return {
        label: raw.layerName ?? null,
        surfaceId: surface,
        // An adapted or merged document already carries the label its own
        // medium earned; recomputing it would throw the resolution away.
        displayLabel: raw.displayLabel || displayLabel(surface, material || null),
        munsell: null,
        material: raw.inferredMaterial ?? null,
        visualPattern: raw.visualPattern ?? null,
        description: raw.description ?? null,
        topBoundary: boundary(raw.topBoundary),
        topBoundaryDerived: false,
        bottomBoundary: boundary(raw.bottomBoundary),
        bottomBoundaryDerived: false,
        features: (raw.featuresInLayer || []).map(f => feature(f, "approxYMeters")),
        provenance: {
          schemaType: ILLUSTRATOR,
          sourceFace: profile.face ?? null,
          sourceLayerIndex: index,
          sourceLabel: raw.layerName ?? null,
        },
      };
    });

    // Padded, not zipped, so a label with no position (or the reverse)
    // still reaches the reader instead of vanishing in the shorter list.
    const gridRefs = [];
    for (let i = 0; i < Math.max(labels.length, positions.length); i += 1) {
      gridRefs.push({
        kind: "gridLabel",
        rawText: i < labels.length ? labels[i] ?? null : null,
        xMeters: i < positions.length ? positions[i] ?? null : null,
      });
    }
    return { face: profile.face ?? null, gridRefs, layers };
  });

  return wrap(d, ILLUSTRATOR, document, faces);
}

export function ingest(d) {
  if (!d || typeof d !== "object") return d;
  if (d.canonicalVersion === CANONICAL_VERSION) return d;
  if (Array.isArray(d.trenchProfiles)) return fromIllustrator(d);
  if (FIELD_MARKERS.some(key => key in d)) return fromFieldWall(d);
  // Not an extraction at all (a grid config, a points CSV export, junk):
  // hand it back for the empty-state message to explain.
  return d;
}
