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

export function debounce(callback, waitMilliseconds, timers = globalThis) {
  if (typeof callback !== "function") {
    throw new TypeError("Debounced callback must be a function.");
  }
  if (!Number.isFinite(waitMilliseconds) || waitMilliseconds < 0) {
    throw new RangeError("Debounce delay must be a non-negative number.");
  }

  let timeoutId;
  let pendingCall;

  function invokePending(call) {
    if (pendingCall !== call) {
      return undefined;
    }

    pendingCall = undefined;
    timeoutId = undefined;
    return callback.apply(call.context, call.args);
  }

  function debounced(...args) {
    if (pendingCall !== undefined) {
      timers.clearTimeout(timeoutId);
    }

    const call = { args, context: this };
    pendingCall = call;
    timeoutId = timers.setTimeout(() => {
      invokePending(call);
    }, waitMilliseconds);
  }

  debounced.flush = () => {
    if (pendingCall === undefined) {
      return undefined;
    }

    timers.clearTimeout(timeoutId);
    return invokePending(pendingCall);
  };

  debounced.cancel = () => {
    if (pendingCall === undefined) {
      return;
    }

    timers.clearTimeout(timeoutId);
    pendingCall = undefined;
    timeoutId = undefined;
  };

  return debounced;
}

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

export function assembleFieldWallPolygonMetadata({
  locus,
  munsell,
  note,
}) {
  return {
    locus: locus.trim(),
    munsell: munsell.trim(),
    note: note.trim(),
  };
}

export function fieldWallMetadataFormValues(metadata = {}) {
  return {
    locus: metadata.locus ?? "",
    munsell: metadata.munsell ?? "",
    note: metadata.note ?? "",
  };
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

function currentOpenPolygon(face) {
  const currentPolygonId = (
    face.currentPolygon?.id
    ?? face.currentPolygonId
  );

  return (face.polygons ?? []).find(
    (polygon) => polygon.id === currentPolygonId && !polygon.closed,
  );
}

export function undoCurrentPolygonVertex(face) {
  const polygon = currentOpenPolygon(face);

  if (!polygon || polygon.vertices.length === 0) {
    return false;
  }

  polygon.vertices.pop();

  if (
    face.selectedVertex?.polygonId === polygon.id
    && face.selectedVertex.vertexIndex >= polygon.vertices.length
  ) {
    face.selectedVertex = null;
  }

  return true;
}

export function cancelCurrentPolygon(face) {
  const polygon = currentOpenPolygon(face);

  if (!polygon) {
    return false;
  }

  const polygonIndex = face.polygons.indexOf(polygon);
  face.polygons.splice(polygonIndex, 1);
  face.currentPolygon = null;

  if (Object.prototype.hasOwnProperty.call(face, "currentPolygonId")) {
    face.currentPolygonId = null;
  }

  if (face.selectedVertex?.polygonId === polygon.id) {
    face.selectedVertex = null;
  }

  return true;
}

export function deleteClosedPolygon(face, polygonId) {
  const polygonIndex = (face.polygons ?? []).findIndex(
    (polygon) => polygon.id === polygonId && polygon.closed,
  );

  if (polygonIndex === -1) {
    return false;
  }

  face.polygons.splice(polygonIndex, 1);

  for (const metadataKey of ["polygonMetadata", "metadataByPolygonId"]) {
    const metadata = face[metadataKey];

    if (metadata) {
      delete metadata[polygonId];
    }
  }

  if (face.selectedVertex?.polygonId === polygonId) {
    face.selectedVertex = null;
  }

  return true;
}

export function allocatePolygonId(face) {
  if (!Number.isInteger(face.nextPolygonId) || face.nextPolygonId < 1) {
    throw new RangeError("Next polygon id must be a positive integer.");
  }

  const polygonId = face.nextPolygonId;
  face.nextPolygonId += 1;
  return polygonId;
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

function drawablePolygons(face) {
  return (face.polygons ?? []).filter(
    (polygon) => (polygon.vertices ?? []).length > 0,
  );
}

function polygonStackingError(face, polygons) {
  const polygonIds = new Set();

  for (const polygon of polygons) {
    if (polygonIds.has(polygon.id)) {
      return `Face "${face.name}" has duplicate polygon id ${polygon.id}; `
        + "stacking order is ambiguous.";
    }
    polygonIds.add(polygon.id);
  }

  const orderKeys = ["stackOrder", "zOrder", "zIndex"];
  const explicitOrders = polygons.map((polygon) => {
    const orderKey = orderKeys.find((key) => (
      Object.prototype.hasOwnProperty.call(polygon, key)
    ));
    return orderKey === undefined ? undefined : polygon[orderKey];
  });

  if (
    explicitOrders.some((order) => order !== undefined)
    && explicitOrders.some((order, index) => order !== index)
  ) {
    return `Face "${face.name}" polygon stack order must be unique, `
      + "contiguous, and match the saved polygon order.";
  }

  return null;
}

export function validateEditorStateForFinalize(editorState) {
  if (!editorState.faces?.length) {
    return {
      canFinalize: false,
      message: "Set up at least one face before finalizing.",
    };
  }

  for (const face of editorState.faces) {
    const polygons = drawablePolygons(face);
    const stackingError = polygonStackingError(face, polygons);

    if (stackingError) {
      return { canFinalize: false, message: stackingError };
    }

    for (const polygon of polygons) {
      if (!polygon.closed || polygon.vertices.length < 3) {
        return {
          canFinalize: false,
          message: (
            `Face "${face.name}" polygon ${polygon.id} is not closed`
            + " with at least three vertices."
          ),
        };
      }

      if (hasSelfIntersection(polygon.vertices)) {
        return {
          canFinalize: false,
          message: (
            `Face "${face.name}" polygon ${polygon.id} self-intersects.`
          ),
        };
      }
    }

    try {
      validateGridRegistration(face.gridRegistration ?? {});
    } catch (error) {
      return {
        canFinalize: false,
        message: (
          `Face "${face.name}" has incomplete grid registration: `
          + error.message
        ),
      };
    }
  }

  return {
    canFinalize: true,
    message: "All structural checks pass; ready to finalize.",
  };
}

export function updateFinalizeControl(
  finalizeButton,
  statusElement,
  editorState,
) {
  const validation = validateEditorStateForFinalize(editorState);
  finalizeButton.disabled = !validation.canFinalize;
  statusElement.textContent = validation.message;
  return validation;
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

function cloneJsonValue(value) {
  if (Array.isArray(value)) {
    return value.map(cloneJsonValue);
  }

  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, nestedValue]) => (
        [key, cloneJsonValue(nestedValue)]
      )),
    );
  }

  return value;
}

export function snapshotEditorState(editorState) {
  return {
    activeFaceIndex: editorState.activeFaceIndex,
    faces: editorState.faces.map((face) => ({
      name: face.name,
      gridRegistration: cloneJsonValue(face.gridRegistration ?? {}),
      polygons: cloneJsonValue(face.polygons ?? []),
      polygonMetadata: cloneJsonValue(
        face.polygonMetadata ?? face.metadataByPolygonId ?? {},
      ),
      nextPolygonId: face.nextPolygonId,
      currentPolygonId: face.currentPolygon?.id ?? (
        face.currentPolygonId ?? null
      ),
      selectedVertex: cloneJsonValue(face.selectedVertex ?? null),
    })),
  };
}

export function reconstructEditorState(savedState) {
  const resumableState = (
    savedState?.resumeState
    ?? savedState?.editorState
    ?? savedState
  );

  if (!resumableState || !Array.isArray(resumableState.faces)) {
    throw new TypeError("Saved editor state must include a faces array.");
  }

  return cloneJsonValue(resumableState);
}

function assembleSaveGridConfig(editorState) {
  try {
    return assembleGridConfig(editorState);
  } catch (error) {
    const faces = {};

    for (const face of editorState.faces) {
      faces[face.name] = cloneJsonValue(face.gridRegistration ?? {});
    }

    return { faces };
  }
}

export function assembleEditorSessionState(
  editorState,
  schemaType,
  documentMetadata = {},
) {
  const structuralEditorState = {
    faces: editorState.faces.map((face) => ({
      name: face.name,
      polygons: drawablePolygons(face).map((polygon, stackOrder) => ({
        id: polygon.id,
        closed: polygon.closed,
        stackOrder,
        vertices: polygon.vertices.map(({ x, y }) => ({ x, y })),
      })),
    })),
  };

  return {
    schemaType,
    finalizeState: assembleFinalizeState(
      editorState,
      schemaType,
      documentMetadata,
    ),
    gridConfig: assembleSaveGridConfig(editorState),
    editorState: structuralEditorState,
    resumeState: snapshotEditorState(editorState),
  };
}
