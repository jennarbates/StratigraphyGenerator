/**
 * The canvas uses 200 pixels per metre: at this scale the fixed 3m × 2m face
 * is 600 × 400 CSS pixels, large enough to work with on a typical laptop, and
 * the default 0.25m grid lands on exact 50-pixel intervals. Keep every future
 * geometry conversion anchored to this constant so display and saved real-world
 * measurements remain consistent.
 */
export const PIXELS_PER_METER = 200;
export const CANVAS_WIDTH_METERS = 3;
export const CANVAS_HEIGHT_METERS = 2;
export const GRID_SPACING_METERS = 0.25;

export function metersToPixels(meters, pixelsPerMeter) {
  return meters * pixelsPerMeter;
}

export function pixelsToMeters(pixels, pixelsPerMeter) {
  return pixels / pixelsPerMeter;
}

/**
 * Snap to the closest grid intersection. A point exactly halfway between two
 * grid lines rounds to the line with the higher coordinate.
 */
export function nearestGridPoint(x, y, gridSpacingPixels) {
  if (gridSpacingPixels <= 0) {
    throw new RangeError("Grid spacing must be greater than zero.");
  }

  const snapCoordinate = (coordinate) => (
    Math.floor((coordinate / gridSpacingPixels) + 0.5) * gridSpacingPixels
  );

  return {
    x: snapCoordinate(x),
    y: snapCoordinate(y),
  };
}

export function edgeMidpoint(start, end) {
  return {
    x: (start.x + end.x) / 2,
    y: (start.y + end.y) / 2,
  };
}

export function isShapeClosed(points) {
  if (points.length < 4) {
    return false;
  }

  const first = points[0];
  const last = points[points.length - 1];
  return first.x === last.x && first.y === last.y;
}

function pointOnSegment(point, start, end) {
  const crossProduct = (
    ((point.y - start.y) * (end.x - start.x))
    - ((point.x - start.x) * (end.y - start.y))
  );

  if (Math.abs(crossProduct) > Number.EPSILON) {
    return false;
  }

  return (
    point.x >= Math.min(start.x, end.x)
    && point.x <= Math.max(start.x, end.x)
    && point.y >= Math.min(start.y, end.y)
    && point.y <= Math.max(start.y, end.y)
  );
}

function direction(start, end, point) {
  return (
    ((end.x - start.x) * (point.y - start.y))
    - ((end.y - start.y) * (point.x - start.x))
  );
}

function segmentsIntersect(firstStart, firstEnd, secondStart, secondEnd) {
  const firstDirection = direction(firstStart, firstEnd, secondStart);
  const secondDirection = direction(firstStart, firstEnd, secondEnd);
  const thirdDirection = direction(secondStart, secondEnd, firstStart);
  const fourthDirection = direction(secondStart, secondEnd, firstEnd);

  if (
    ((firstDirection > 0 && secondDirection < 0)
      || (firstDirection < 0 && secondDirection > 0))
    && ((thirdDirection > 0 && fourthDirection < 0)
      || (thirdDirection < 0 && fourthDirection > 0))
  ) {
    return true;
  }

  return (
    (firstDirection === 0 && pointOnSegment(secondStart, firstStart, firstEnd))
    || (secondDirection === 0 && pointOnSegment(secondEnd, firstStart, firstEnd))
    || (thirdDirection === 0 && pointOnSegment(firstStart, secondStart, secondEnd))
    || (fourthDirection === 0 && pointOnSegment(firstEnd, secondStart, secondEnd))
  );
}

export function hasSelfIntersection(vertices) {
  if (vertices.length < 4) {
    return false;
  }

  for (let firstEdge = 0; firstEdge < vertices.length; firstEdge += 1) {
    const firstEdgeEnd = (firstEdge + 1) % vertices.length;

    for (
      let secondEdge = firstEdge + 1;
      secondEdge < vertices.length;
      secondEdge += 1
    ) {
      const secondEdgeEnd = (secondEdge + 1) % vertices.length;
      const edgesAreAdjacent = (
        firstEdgeEnd === secondEdge
        || secondEdgeEnd === firstEdge
      );

      if (edgesAreAdjacent) {
        continue;
      }

      if (
        segmentsIntersect(
          vertices[firstEdge],
          vertices[firstEdgeEnd],
          vertices[secondEdge],
          vertices[secondEdgeEnd],
        )
      ) {
        return true;
      }
    }
  }

  return false;
}

export function serializePolygons(polygons, metadataByPolygonId, schemaType) {
  const fieldWall = schemaType === "FieldWallProfile";

  return polygons
    .filter((polygon) => (
      Object.prototype.hasOwnProperty.call(metadataByPolygonId, polygon.id)
    ))
    .map((polygon) => {
      const metadata = metadataByPolygonId[polygon.id];
      const serialized = {
        polygonId: polygon.id,
        geometry: polygon.vertices.map(({ x, y }) => ({ x, y })),
      };

      if (fieldWall) {
        return {
          ...serialized,
          locus: metadata.locus ?? "",
          munsell: metadata.munsell ?? "",
          note: metadata.note ?? "",
        };
      }

      return {
        ...serialized,
        material: metadata.material ?? "",
        note: metadata.note ?? "",
      };
    });
}

export function selectFace(editorState, faceIndex) {
  if (
    !Number.isInteger(faceIndex)
    || faceIndex < 0
    || faceIndex >= editorState.faces.length
  ) {
    throw new RangeError("Face index is out of range.");
  }

  editorState.activeFaceIndex = faceIndex;
  return editorState.faces[faceIndex];
}

export function validateBearingDeg(value) {
  const bearing = Number(value);

  if (value === "" || !Number.isFinite(bearing) || bearing < 0 || bearing > 360) {
    throw new RangeError("Bearing must be a number from 0 through 360.");
  }

  return bearing;
}

function validateRegistrationNumber(value, fieldName) {
  const number = Number(value);

  if (value === "" || !Number.isFinite(number)) {
    throw new TypeError(`${fieldName} must be a finite number.`);
  }

  return number;
}

export function validateGridRegistration(registration) {
  return {
    originX: validateRegistrationNumber(registration.originX, "originX"),
    originY: validateRegistrationNumber(registration.originY, "originY"),
    surfaceZ: validateRegistrationNumber(registration.surfaceZ, "surfaceZ"),
    bearing_deg: validateBearingDeg(registration.bearing_deg),
  };
}

function metadataForFace(face) {
  return face.metadataByPolygonId ?? face.polygonMetadata ?? {};
}

function polygonsWithMetadata(face) {
  const metadataByPolygonId = metadataForFace(face);

  return (face.polygons ?? [])
    .filter((polygon) => (
      polygon.closed
      && Object.prototype.hasOwnProperty.call(
        metadataByPolygonId,
        polygon.id,
      )
    ))
    .map((polygon) => ({
      polygon,
      metadata: metadataByPolygonId[polygon.id],
    }));
}

function pointCoordinate(point, finalKey, alternateFinalKey, pixelKey) {
  if (Object.prototype.hasOwnProperty.call(point, finalKey)) {
    return point[finalKey];
  }

  if (
    alternateFinalKey
    && Object.prototype.hasOwnProperty.call(point, alternateFinalKey)
  ) {
    return point[alternateFinalKey];
  }

  return pixelsToMeters(point[pixelKey], PIXELS_PER_METER);
}

function archaeologicalBoundary(points) {
  return points.map((point) => ({
    xCoordinateMeters: pointCoordinate(
      point,
      "xCoordinateMeters",
      "xMeters",
      "x",
    ),
    yCoordinateMeters: pointCoordinate(
      point,
      "yCoordinateMeters",
      "depthMeters",
      "y",
    ),
    confidence: point.confidence ?? "human-traced",
  }));
}

function fieldWallBoundary(points) {
  return points.map((point) => ({
    xMeters: pointCoordinate(
      point,
      "xMeters",
      "xCoordinateMeters",
      "x",
    ),
    depthMeters: pointCoordinate(
      point,
      "depthMeters",
      "yCoordinateMeters",
      "y",
    ),
    confidence: point.confidence ?? "human-traced",
  }));
}

function boundaryOrNull(metadata, polygon, boundaryName, serializer) {
  if (metadata[boundaryName] === null) {
    return null;
  }

  if (metadata[boundaryName] !== undefined) {
    return serializer(metadata[boundaryName]);
  }

  if (boundaryName === "topBoundary") {
    return null;
  }

  return serializer(polygon.vertices);
}

function archaeologicalLayers(face) {
  return polygonsWithMetadata(face).map(({ polygon, metadata }) => ({
    layerName: metadata.layerName ?? `Polygon ${polygon.id}`,
    inferredMaterial: (
      metadata.inferredMaterial
      ?? metadata.material
      ?? null
    ),
    description: metadata.description ?? metadata.note ?? null,
    visualPattern: metadata.visualPattern ?? null,
    featuresInLayer: metadata.featuresInLayer ?? [],
    topBoundary: boundaryOrNull(
      metadata,
      polygon,
      "topBoundary",
      archaeologicalBoundary,
    ),
    bottomBoundary: boundaryOrNull(
      metadata,
      polygon,
      "bottomBoundary",
      archaeologicalBoundary,
    ),
  }));
}

function fieldWallLayers(face) {
  return polygonsWithMetadata(face).map(({ polygon, metadata }) => ({
    locusNumber: metadata.locus ?? null,
    topBoundary: boundaryOrNull(
      metadata,
      polygon,
      "topBoundary",
      fieldWallBoundary,
    ),
    bottomBoundary: boundaryOrNull(
      metadata,
      polygon,
      "bottomBoundary",
      fieldWallBoundary,
    ),
    featuresInLayer: metadata.featuresInLayer ?? [],
  }));
}

function fieldWallLoci(face) {
  const loci = new Map();

  for (const { metadata } of polygonsWithMetadata(face)) {
    const locusNumber = metadata.locus ?? null;

    if (loci.has(locusNumber)) {
      continue;
    }

    loci.set(locusNumber, {
      locusNumber,
      munsell: metadata.munsell
        ? {
          raw: metadata.munsell,
          colorName: metadata.colorName ?? null,
        }
        : null,
      description: metadata.description ?? metadata.note ?? null,
      confidence: metadata.confidence ?? null,
    });
  }

  return [...loci.values()];
}

export function assembleFinalizeState(
  editorState,
  schemaType,
  documentMetadata = {},
) {
  if (schemaType === "FieldWallProfile") {
    const face = editorState.faces[0] ?? {
      name: "Wall",
      polygons: [],
      polygonMetadata: {},
    };

    return {
      trenchLabel: documentMetadata.trenchLabel ?? null,
      faceLabel: documentMetadata.faceLabel ?? face.name,
      illustrators: documentMetadata.illustrators ?? [],
      date: documentMetadata.date ?? null,
      northArrowPresent: documentMetadata.northArrowPresent ?? null,
      gridSquareCm: documentMetadata.gridSquareCm ?? (
        GRID_SPACING_METERS * 100
      ),
      gridTiePoints: documentMetadata.gridTiePoints ?? [],
      loci: documentMetadata.loci ?? fieldWallLoci(face),
      layers: fieldWallLayers(face),
      marginalia: documentMetadata.marginalia ?? [],
    };
  }

  if (schemaType !== "ArchaeologicalDiagram") {
    throw new TypeError(`Unsupported schema type: ${schemaType}`);
  }

  return {
    metadata: documentMetadata.metadata ?? {
      currentFilePath: "manual-editor",
      suggestedFilename: null,
      trenchLabel: null,
      scale: null,
      credits: null,
      marginalia: [],
    },
    trenchProfiles: editorState.faces.map((face) => ({
      face: face.name,
      gridLabels: face.gridLabels ?? [],
      gridLabelXMeters: face.gridLabelXMeters ?? [],
      layers: archaeologicalLayers(face),
    })),
    legend: documentMetadata.legend ?? [],
    inferred_notes: documentMetadata.inferred_notes ?? [],
    rawTranscription: (
      documentMetadata.rawTranscription
      ?? "Created with the manual editor."
    ),
  };
}

export function assembleGridConfig(editorState) {
  const faces = {};

  for (const face of editorState.faces) {
    if (Object.prototype.hasOwnProperty.call(faces, face.name)) {
      throw new TypeError(`Face names must be unique: ${face.name}`);
    }

    faces[face.name] = validateGridRegistration(face.gridRegistration);
  }

  return { faces };
}

export function assembleEditorSessionState(
  editorState,
  schemaType,
  documentMetadata = {},
) {
  return {
    finalizeState: assembleFinalizeState(
      editorState,
      schemaType,
      documentMetadata,
    ),
    gridConfig: assembleGridConfig(editorState),
  };
}
