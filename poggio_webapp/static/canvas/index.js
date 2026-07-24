import {
  CANVAS_HEIGHT_METERS,
  CANVAS_WIDTH_METERS,
  GRID_SPACING_METERS,
  PIXELS_PER_METER,
  assembleEditorSessionState,
  debounce,
  edgeMidpoint,
  hasSelfIntersection,
  isShapeClosed,
  metersToPixels,
  nearestGridPoint,
  pixelsToMeters,
  reconstructEditorState,
  selectFace,
  updateFinalizeControl,
  validateBearingDeg,
} from "./grid.mjs";

const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
const POLYGON_COLORS = [
  "#b23a48",
  "#1f6f8b",
  "#6b7f2a",
  "#8a4f9e",
  "#c4661f",
  "#24735b",
];
const DRAG_THRESHOLD_PIXELS = 4;
const FIELD_WALL_SCHEMA = "FieldWallProfile";
const AUTOSAVE_DELAY_MILLISECONDS = 2000;
const canvasContainer = document.querySelector("#face-canvas-container");
const faceTabs = document.querySelector("#face-tabs");
const activeFaceSummary = document.querySelector("#active-face-summary");
const snapToggle = document.querySelector("#snap-to-grid");
const closeShapeButton = document.querySelector("#close-shape");
const deleteVertexButton = document.querySelector("#delete-vertex");
const finalizeButton = document.querySelector("#finalize-editor");
const finalizeStatus = document.querySelector("#finalize-status");
const coordinateReport = document.querySelector("#coordinate-report");
const polygonList = document.querySelector("#polygon-list");
const polygonListEmpty = document.querySelector("#polygon-list-empty");
const metadataDialog = document.querySelector("#metadata-dialog");
const metadataForm = document.querySelector("#metadata-form");
const metadataFormHeading = document.querySelector("#metadata-form-heading");
const metadataPolygonId = document.querySelector("#metadata-polygon-id");
const materialField = document.querySelector("#material-field");
const materialSelect = document.querySelector("#material");
const fieldWallFields = document.querySelector("#fieldwall-fields");
const locusInput = document.querySelector("#locus");
const munsellHueInput = document.querySelector("#munsell-hue");
const munsellValueInput = document.querySelector("#munsell-value");
const munsellChromaInput = document.querySelector("#munsell-chroma");
const metadataNoteInput = document.querySelector("#metadata-note");
const cancelMetadataButton = document.querySelector("#cancel-metadata");
const registrationForm = document.querySelector("#grid-registration-form");
const registrationFace = document.querySelector("#grid-registration-face");
const registrationInputs = [
  ...registrationForm.querySelectorAll("[data-registration-field]"),
];
const faceSetupDialog = document.querySelector("#face-setup-dialog");
const faceSetupForm = document.querySelector("#face-setup-form");
const faceCountField = document.querySelector("#face-count-field");
const faceCountInput = document.querySelector("#face-count");
const faceNameFields = document.querySelector("#face-name-fields");
const editorRoot = document.querySelector("#editor-app");
const saveStatusControl = document.querySelector("#save-status-control");
const saveStatus = document.querySelector("#save-status");
const retrySaveButton = document.querySelector("#retry-save");

const widthPixels = metersToPixels(CANVAS_WIDTH_METERS, PIXELS_PER_METER);
const heightPixels = metersToPixels(CANVAS_HEIGHT_METERS, PIXELS_PER_METER);
const gridSpacingPixels = metersToPixels(GRID_SPACING_METERS, PIXELS_PER_METER);
const pageSearchParams = new URLSearchParams(window.location.search);

function validJobId(value) {
  const normalizedValue = typeof value === "string" ? value.trim() : "";
  return normalizedValue
    && !["null", "none", "undefined"].includes(normalizedValue.toLowerCase())
    ? normalizedValue
    : null;
}

const jobId = validJobId(
  editorRoot ? editorRoot.dataset.jobId : pageSearchParams.get("job_id"),
);
const requestedSchemaType = editorRoot
  ? editorRoot.dataset.schemaType
  : pageSearchParams.get("schema_type");
let schemaType = requestedSchemaType === FIELD_WALL_SCHEMA
  ? FIELD_WALL_SCHEMA
  : "ArchaeologicalDiagram";
let isFieldWall = schemaType === FIELD_WALL_SCHEMA;
const editorState = {
  activeFaceIndex: -1,
  faces: [],
};
let currentFace = null;
let canvas = null;
let grid = null;
let polygons = [];
let polygonMetadata = {};
let currentPolygon = null;
let selectedVertex = null;
let pointerAction = null;
let saveSequence = Promise.resolve();
let hasValidEditorSession = Boolean(jobId);
let changeRevision = 0;
let savedRevision = 0;

function showSaveState(state) {
  const messages = {
    dirty: "Not saved yet.",
    saving: "Saving…",
    saved: "All changes saved.",
    failed: "Couldn’t save.",
  };
  saveStatusControl.dataset.state = state;
  saveStatus.textContent = messages[state];
  retrySaveButton.hidden = state !== "failed" || !hasValidEditorSession;
}

function showInvalidSessionError() {
  hasValidEditorSession = false;
  const message = "Invalid editor session. Saving and finalization are disabled.";
  coordinateReport.textContent = message;
  finalizeStatus.textContent = message;
  finalizeButton.disabled = true;
  showSaveState("failed");
}

function updateEditorFinalizeControl() {
  if (!hasValidEditorSession) {
    showInvalidSessionError();
    return { canFinalize: false, message: finalizeStatus.textContent };
  }
  return updateFinalizeControl(finalizeButton, finalizeStatus, editorState);
}

function saveEditorSession({ keepalive = false } = {}) {
  if (!hasValidEditorSession) {
    showInvalidSessionError();
    return Promise.resolve(false);
  }

  saveSequence = saveSequence
    .catch(() => {})
    .then(async () => {
      persistCurrentFace();
      const revisionToSave = changeRevision;
      const state = assembleEditorSessionState(editorState, schemaType);
      showSaveState("saving");

      try {
        const response = await fetch(
          `/editor/${encodeURIComponent(jobId)}/save`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(state),
            keepalive,
          },
        );

        if (!response.ok) {
          throw new Error(`Autosave failed with status ${response.status}.`);
        }

        savedRevision = Math.max(savedRevision, revisionToSave);
        showSaveState(
          savedRevision === changeRevision ? "saved" : "dirty",
        );
        return true;
      } catch (error) {
        showSaveState("failed");
        throw error;
      }
    });

  return saveSequence;
}

function runAutosave(options) {
  return saveEditorSession(options).catch(() => false);
}

const debouncedAutosave = debounce((options) => {
  runAutosave(options);
}, AUTOSAVE_DELAY_MILLISECONDS);

function scheduleAutosave() {
  if (!hasValidEditorSession) {
    showInvalidSessionError();
    return;
  }

  changeRevision += 1;
  showSaveState("dirty");
  debouncedAutosave();
}

function saveInitialFaceSetup() {
  if (!hasValidEditorSession) {
    showInvalidSessionError();
    return;
  }

  changeRevision += 1;
  showSaveState("dirty");
  debouncedAutosave.cancel();
  runAutosave();
}

function createSvgElement(name, attributes = {}) {
  const element = document.createElementNS(SVG_NAMESPACE, name);

  for (const [attribute, value] of Object.entries(attributes)) {
    element.setAttribute(attribute, value);
  }

  return element;
}

function createPolygon(face) {
  const id = face.nextPolygonId;
  face.nextPolygonId += 1;

  return {
    id,
    color: POLYGON_COLORS[(id - 1) % POLYGON_COLORS.length],
    vertices: [],
    closed: false,
  };
}

function addGridLine(gridElement, x1, y1, x2, y2) {
  const line = document.createElementNS(SVG_NAMESPACE, "line");
  line.setAttribute("class", "grid-line");
  line.setAttribute("x1", x1);
  line.setAttribute("y1", y1);
  line.setAttribute("x2", x2);
  line.setAttribute("y2", y2);
  gridElement.append(line);
}

function createGrid() {
  const gridElement = document.createElementNS(SVG_NAMESPACE, "g");
  gridElement.setAttribute("aria-hidden", "true");

  for (let x = 0; x <= widthPixels; x += gridSpacingPixels) {
    addGridLine(gridElement, x, 0, x, heightPixels);
  }

  for (let y = 0; y <= heightPixels; y += gridSpacingPixels) {
    addGridLine(gridElement, 0, y, widthPixels, y);
  }

  return gridElement;
}

function createFaceState(name, faceIndex) {
  const faceCanvas = createSvgElement("svg", {
    id: `face-canvas-${faceIndex}`,
    class: "face-canvas",
    width: widthPixels,
    height: heightPixels,
    viewBox: `0 0 ${widthPixels} ${heightPixels}`,
    role: "img",
    "aria-label": (
      `${name}: editable 3 metre by 2 metre polygon canvas`
      + " with graph-paper grid"
    ),
    "aria-labelledby": `face-tab-${faceIndex}`,
  });
  const faceGrid = createGrid();
  const face = {
    name,
    canvas: faceCanvas,
    grid: faceGrid,
    gridRegistration: {
      originX: "",
      originY: "",
      surfaceZ: "",
      bearing_deg: "",
    },
    polygons: [],
    polygonMetadata: {},
    nextPolygonId: 1,
    currentPolygon: null,
    selectedVertex: null,
  };
  face.currentPolygon = createPolygon(face);
  face.polygons.push(face.currentPolygon);
  faceCanvas.append(faceGrid);
  faceCanvas.addEventListener("pointerdown", beginCanvasPointerAction);
  faceCanvas.addEventListener("pointermove", continueCanvasPointerAction);
  faceCanvas.addEventListener("pointerup", finishCanvasPointerAction);
  faceCanvas.addEventListener("pointercancel", cancelCanvasPointerAction);
  faceCanvas.setAttribute("hidden", "");
  canvasContainer.append(faceCanvas);
  return face;
}

function restoreFaceState(savedFace, faceIndex) {
  const face = createFaceState(savedFace.name, faceIndex);
  face.gridRegistration = {
    originX: "",
    originY: "",
    surfaceZ: "",
    bearing_deg: "",
    ...savedFace.gridRegistration,
  };
  face.polygons = (savedFace.polygons ?? []).map((polygon) => ({
    ...polygon,
    color: (
      polygon.color
      ?? POLYGON_COLORS[(polygon.id - 1) % POLYGON_COLORS.length]
    ),
    vertices: (polygon.vertices ?? []).map(({ x, y }) => ({ x, y })),
  }));
  face.polygonMetadata = savedFace.polygonMetadata ?? {};

  const largestPolygonId = face.polygons.reduce(
    (largestId, polygon) => Math.max(largestId, Number(polygon.id) || 0),
    0,
  );
  face.nextPolygonId = (
    Number.isInteger(savedFace.nextPolygonId)
    && savedFace.nextPolygonId > largestPolygonId
  )
    ? savedFace.nextPolygonId
    : largestPolygonId + 1;
  face.currentPolygon = face.polygons.find(
    (polygon) => polygon.id === savedFace.currentPolygonId,
  ) ?? face.polygons.find((polygon) => !polygon.closed);

  if (!face.currentPolygon) {
    face.currentPolygon = createPolygon(face);
    face.polygons.push(face.currentPolygon);
  }

  face.selectedVertex = savedFace.selectedVertex ?? null;
  return face;
}

function restoreEditorSession(savedState) {
  const restoredState = reconstructEditorState(savedState);

  if (restoredState.faces.length === 0) {
    return false;
  }

  canvasContainer.replaceChildren();
  editorState.faces = restoredState.faces.map(restoreFaceState);
  const requestedFaceIndex = restoredState.activeFaceIndex;
  editorState.activeFaceIndex = (
    Number.isInteger(requestedFaceIndex)
    && requestedFaceIndex >= 0
    && requestedFaceIndex < editorState.faces.length
  )
    ? requestedFaceIndex
    : 0;
  faceTabs.hidden = false;
  activateFace(editorState.activeFaceIndex);
  showSaveState("saved");
  coordinateReport.textContent = (
    `Restored ${editorState.faces.length} face`
    + `${editorState.faces.length === 1 ? "" : "s"} from autosave.`
  );
  return true;
}

function findPolygon(polygonId) {
  return polygons.find((polygon) => polygon.id === polygonId);
}

function metadataLabel(polygonId) {
  const metadata = polygonMetadata[polygonId];

  if (!metadata) {
    return "Needs metadata";
  }

  if (isFieldWall) {
    return `Locus ${metadata.locus} · ${metadata.munsell}`;
  }

  return metadata.material;
}

function renderPolygonList() {
  const closedPolygons = polygons.filter((polygon) => polygon.closed);
  polygonList.replaceChildren();
  polygonListEmpty.hidden = closedPolygons.length > 0;

  closedPolygons.forEach((polygon) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    const polygonName = document.createElement("strong");
    const label = document.createElement("span");

    button.type = "button";
    button.dataset.polygonId = polygon.id;
    button.style.setProperty("--polygon-color", polygon.color);
    polygonName.textContent = `Polygon ${polygon.id}`;
    label.textContent = metadataLabel(polygon.id);
    button.append(polygonName, label);
    item.append(button);
    polygonList.append(item);
  });
}

function persistCurrentFace() {
  if (!currentFace) {
    return;
  }

  currentFace.currentPolygon = currentPolygon;
  currentFace.selectedVertex = selectedVertex;
}

function renderFaceTabs() {
  faceTabs.replaceChildren();

  editorState.faces.forEach((face, faceIndex) => {
    const button = document.createElement("button");
    const selected = faceIndex === editorState.activeFaceIndex;
    button.id = `face-tab-${faceIndex}`;
    button.type = "button";
    button.setAttribute("role", "tab");
    button.dataset.faceIndex = faceIndex;
    button.setAttribute("aria-controls", `face-canvas-${faceIndex}`);
    button.setAttribute("aria-selected", selected ? "true" : "false");
    button.tabIndex = selected ? 0 : -1;
    button.textContent = face.name;
    faceTabs.append(button);
  });
}

function validateRegistrationInput(input) {
  input.setCustomValidity("");

  if (input.dataset.registrationField !== "bearing_deg" || input.value === "") {
    return;
  }

  try {
    validateBearingDeg(input.value);
  } catch (error) {
    input.setCustomValidity(error.message);
  }
}

function renderGridRegistration() {
  registrationFace.textContent = (
    `${currentFace.name}: enter surveyed values (no placeholder defaults).`
  );

  registrationInputs.forEach((input) => {
    const field = input.dataset.registrationField;
    input.value = currentFace.gridRegistration[field];
    validateRegistrationInput(input);
  });
}

function activateFace(faceIndex) {
  persistCurrentFace();
  pointerAction = null;

  if (metadataDialog.open) {
    metadataDialog.close();
  }

  currentFace = selectFace(editorState, faceIndex);
  polygons = currentFace.polygons;
  polygonMetadata = currentFace.polygonMetadata;
  currentPolygon = currentFace.currentPolygon;
  selectedVertex = currentFace.selectedVertex;
  canvas = currentFace.canvas;
  grid = currentFace.grid;

  editorState.faces.forEach((face, index) => {
    if (index === faceIndex) {
      face.canvas.removeAttribute("hidden");
    } else {
      face.canvas.setAttribute("hidden", "");
    }
  });

  renderFaceTabs();
  renderGridRegistration();
  renderPolygons();
  renderPolygonList();
  activeFaceSummary.textContent = (
    `${currentFace.name} · 3m × 2m · grid spacing 0.25m`
  );
  coordinateReport.textContent = (
    `${currentFace.name}: tap or click the canvas to place a vertex.`
  );
}

function parseMunsell(munsell = "") {
  const match = munsell.match(/^(\S+)\s+(\S+)\/(\S+)$/);

  return match
    ? { hue: match[1], value: match[2], chroma: match[3] }
    : { hue: "", value: "", chroma: "" };
}

function openMetadataForm(polygonId) {
  const polygon = findPolygon(polygonId);

  if (!polygon?.closed) {
    return;
  }

  const metadata = polygonMetadata[polygonId] ?? {};
  const munsell = parseMunsell(metadata.munsell);
  metadataForm.reset();
  metadataPolygonId.value = polygonId;
  metadataFormHeading.textContent = `Polygon ${polygonId} metadata`;
  materialSelect.value = metadata.material ?? "";
  locusInput.value = metadata.locus ?? "";
  munsellHueInput.value = munsell.hue;
  munsellValueInput.value = munsell.value;
  munsellChromaInput.value = munsell.chroma;
  metadataNoteInput.value = metadata.note ?? "";
  metadataDialog.showModal();
}

function selectedVertexExists() {
  if (!selectedVertex) {
    return false;
  }

  const polygon = findPolygon(selectedVertex.polygonId);
  return Boolean(polygon && polygon.vertices[selectedVertex.vertexIndex]);
}

function closedPathPoints(polygon) {
  if (!polygon.closed || polygon.vertices.length < 3) {
    return polygon.vertices;
  }

  return [...polygon.vertices, polygon.vertices[0]];
}

function renderPolygon(polygon, drawingLayer) {
  if (polygon.vertices.length === 0) {
    return;
  }

  const pathPoints = closedPathPoints(polygon);
  const shapeIsClosed = isShapeClosed(pathPoints);
  const shape = createSvgElement(shapeIsClosed ? "polygon" : "polyline", {
    class: (
      `polygon-shape${hasSelfIntersection(polygon.vertices)
        ? " self-intersecting"
        : ""}`
    ),
    points: polygon.vertices.map(({ x, y }) => `${x},${y}`).join(" "),
    stroke: polygon.color,
    fill: shapeIsClosed ? polygon.color : "none",
    "fill-opacity": shapeIsClosed ? "0.08" : "0",
  });
  drawingLayer.append(shape);

  const firstVertex = polygon.vertices[0];
  drawingLayer.append(createSvgElement("text", {
    class: "polygon-number",
    x: firstVertex.x + 10,
    y: firstVertex.y - 10,
    fill: polygon.color,
  }));
  drawingLayer.lastElementChild.textContent = polygon.id;

  const edgeCount = shapeIsClosed
    ? polygon.vertices.length
    : Math.max(0, polygon.vertices.length - 1);

  for (let edgeIndex = 0; edgeIndex < edgeCount; edgeIndex += 1) {
    const nextVertexIndex = (edgeIndex + 1) % polygon.vertices.length;
    const midpoint = edgeMidpoint(
      polygon.vertices[edgeIndex],
      polygon.vertices[nextVertexIndex],
    );
    drawingLayer.append(
      createSvgElement("circle", {
        class: "midpoint-marker",
        cx: midpoint.x,
        cy: midpoint.y,
        r: 4,
        stroke: polygon.color,
      }),
      createSvgElement("circle", {
        class: "midpoint-hit-target",
        cx: midpoint.x,
        cy: midpoint.y,
        r: 12,
        "data-role": "midpoint",
        "data-polygon-id": polygon.id,
        "data-insert-index": edgeIndex + 1,
      }),
    );
  }

  polygon.vertices.forEach((vertex, vertexIndex) => {
    const isSelected = (
      selectedVertex?.polygonId === polygon.id
      && selectedVertex.vertexIndex === vertexIndex
    );
    drawingLayer.append(
      createSvgElement("circle", {
        class: `vertex-marker${isSelected ? " selected" : ""}`,
        cx: vertex.x,
        cy: vertex.y,
        r: 6,
        stroke: polygon.color,
      }),
      createSvgElement("circle", {
        class: "vertex-hit-target",
        cx: vertex.x,
        cy: vertex.y,
        r: 18,
        "data-role": "vertex",
        "data-polygon-id": polygon.id,
        "data-vertex-index": vertexIndex,
      }),
    );
  });
}

function renderPolygons() {
  const drawingLayer = createSvgElement("g", { id: "polygon-layer" });
  polygons.forEach((polygon) => renderPolygon(polygon, drawingLayer));
  canvas.replaceChildren(grid, drawingLayer);
  deleteVertexButton.disabled = !selectedVertexExists();
  updateEditorFinalizeControl();
}

function canvasPoint(event, applySnap = true) {
  const bounds = canvas.getBoundingClientRect();
  const scaleX = widthPixels / bounds.width;
  const scaleY = heightPixels / bounds.height;
  const rawPoint = {
    x: Math.max(0, Math.min(
      widthPixels,
      (event.clientX - bounds.left) * scaleX,
    )),
    y: Math.max(0, Math.min(
      heightPixels,
      (event.clientY - bounds.top) * scaleY,
    )),
  };

  return applySnap && snapToggle.checked
    ? nearestGridPoint(rawPoint.x, rawPoint.y, gridSpacingPixels)
    : rawPoint;
}

function reportPoint(prefix, point) {
  const xMeters = pixelsToMeters(point.x, PIXELS_PER_METER);
  const yMeters = pixelsToMeters(point.y, PIXELS_PER_METER);

  coordinateReport.textContent = (
    `${prefix}: (${xMeters.toFixed(3)}m, ${yMeters.toFixed(3)}m)`
    + ` — snap ${snapToggle.checked ? "on" : "off"}`
  );
}

function movementExceededThreshold(event, action) {
  return Math.hypot(
    event.clientX - action.startClientX,
    event.clientY - action.startClientY,
  ) >= DRAG_THRESHOLD_PIXELS;
}

function modifierHeld(event) {
  return event.altKey || event.ctrlKey || event.metaKey || event.shiftKey;
}

function removeVertex(reference) {
  const polygon = findPolygon(reference.polygonId);

  if (!polygon?.vertices[reference.vertexIndex]) {
    return;
  }

  polygon.vertices.splice(reference.vertexIndex, 1);
  selectedVertex = null;
  coordinateReport.textContent = `Removed a vertex from polygon ${polygon.id}.`;
  renderPolygons();
  scheduleAutosave();
}

function beginCanvasPointerAction(event) {
  if (!event.isPrimary || (event.pointerType === "mouse" && event.button !== 0)) {
    return;
  }

  event.preventDefault();
  const targetRole = event.target.dataset.role;
  const action = {
    pointerId: event.pointerId,
    startClientX: event.clientX,
    startClientY: event.clientY,
    moved: false,
  };

  if (targetRole === "vertex") {
    const reference = {
      polygonId: Number(event.target.dataset.polygonId),
      vertexIndex: Number(event.target.dataset.vertexIndex),
    };

    if (modifierHeld(event)) {
      removeVertex(reference);
      return;
    }

    selectedVertex = reference;
    pointerAction = { ...action, kind: "vertex", reference };
    renderPolygons();
  } else if (targetRole === "midpoint") {
    pointerAction = {
      ...action,
      kind: "midpoint",
      polygonId: Number(event.target.dataset.polygonId),
      insertIndex: Number(event.target.dataset.insertIndex),
    };
  } else {
    pointerAction = { ...action, kind: "canvas" };
  }

  canvas.setPointerCapture(event.pointerId);
}

function continueCanvasPointerAction(event) {
  if (!pointerAction || event.pointerId !== pointerAction.pointerId) {
    return;
  }

  event.preventDefault();

  if (movementExceededThreshold(event, pointerAction)) {
    pointerAction.moved = true;
  }

  if (pointerAction.kind !== "vertex" || !pointerAction.moved) {
    return;
  }

  const polygon = findPolygon(pointerAction.reference.polygonId);
  const point = canvasPoint(event);

  if (!polygon?.vertices[pointerAction.reference.vertexIndex]) {
    return;
  }

  polygon.vertices[pointerAction.reference.vertexIndex] = point;
  reportPoint(`Moved polygon ${polygon.id} vertex`, point);
  renderPolygons();
  scheduleAutosave();
}

function finishCanvasPointerAction(event) {
  if (!pointerAction || event.pointerId !== pointerAction.pointerId) {
    return;
  }

  event.preventDefault();
  const action = pointerAction;
  action.moved = action.moved || movementExceededThreshold(event, action);

  if (action.kind === "canvas" && !action.moved) {
    const point = canvasPoint(event);
    currentPolygon.vertices.push(point);
    selectedVertex = {
      polygonId: currentPolygon.id,
      vertexIndex: currentPolygon.vertices.length - 1,
    };
    reportPoint(`Added polygon ${currentPolygon.id} vertex`, point);
    renderPolygons();
    scheduleAutosave();
  } else if (action.kind === "midpoint" && !action.moved) {
    const polygon = findPolygon(action.polygonId);

    if (polygon && polygon.vertices.length >= 2) {
      const startIndex = action.insertIndex - 1;
      const endIndex = action.insertIndex % polygon.vertices.length;
      const midpoint = edgeMidpoint(
        polygon.vertices[startIndex],
        polygon.vertices[endIndex],
      );
      polygon.vertices.splice(action.insertIndex, 0, midpoint);
      selectedVertex = {
        polygonId: polygon.id,
        vertexIndex: action.insertIndex,
      };
      reportPoint(`Inserted polygon ${polygon.id} vertex`, midpoint);
      renderPolygons();
      scheduleAutosave();
    }
  }

  if (canvas.hasPointerCapture(event.pointerId)) {
    canvas.releasePointerCapture(event.pointerId);
  }
  pointerAction = null;
}

function cancelCanvasPointerAction(event) {
  if (!pointerAction || event.pointerId !== pointerAction.pointerId) {
    return;
  }

  if (canvas.hasPointerCapture(event.pointerId)) {
    canvas.releasePointerCapture(event.pointerId);
  }
  pointerAction = null;
}

function configureSchemaFields() {
  materialField.hidden = isFieldWall;
  materialSelect.disabled = isFieldWall;
  fieldWallFields.hidden = !isFieldWall;
  for (const input of fieldWallFields.querySelectorAll("input")) {
    input.disabled = !isFieldWall;
  }
  faceCountField.hidden = isFieldWall;
}

closeShapeButton.addEventListener("pointerup", (event) => {
  if (
    !event.isPrimary
    || !currentPolygon
    || currentPolygon.vertices.length < 3
  ) {
    coordinateReport.textContent = "Add at least three vertices before closing.";
    return;
  }

  event.preventDefault();
  currentPolygon.closed = true;
  const intersectionWarning = hasSelfIntersection(currentPolygon.vertices)
    ? " It self-intersects; its dashed stroke marks the issue."
    : "";
  coordinateReport.textContent = (
    `Closed polygon ${currentPolygon.id}.${intersectionWarning}`
  );
  const closedPolygonId = currentPolygon.id;
  currentPolygon = createPolygon(currentFace);
  currentFace.currentPolygon = currentPolygon;
  polygons.push(currentPolygon);
  selectedVertex = null;
  renderPolygons();
  renderPolygonList();
  openMetadataForm(closedPolygonId);
  scheduleAutosave();
});

deleteVertexButton.addEventListener("pointerup", (event) => {
  if (!event.isPrimary || !selectedVertexExists()) {
    return;
  }

  event.preventDefault();
  removeVertex(selectedVertex);
});

polygonList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-polygon-id]");

  if (button) {
    openMetadataForm(Number(button.dataset.polygonId));
  }
});

metadataForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const polygonId = Number(metadataPolygonId.value);

  if (!findPolygon(polygonId)?.closed) {
    metadataDialog.close();
    return;
  }

  if (isFieldWall) {
    polygonMetadata[polygonId] = {
      locus: locusInput.value.trim(),
      munsell: (
        `${munsellHueInput.value} ${munsellValueInput.value}`
        + `/${munsellChromaInput.value}`
      ),
      note: metadataNoteInput.value.trim(),
    };
  } else {
    polygonMetadata[polygonId] = {
      material: materialSelect.value,
      note: metadataNoteInput.value.trim(),
    };
  }

  metadataDialog.close();
  renderPolygonList();
  coordinateReport.textContent = `Saved metadata for polygon ${polygonId}.`;
  scheduleAutosave();
});

cancelMetadataButton.addEventListener("click", () => {
  metadataDialog.close();
});

registrationForm.addEventListener("submit", (event) => {
  event.preventDefault();
});

registrationInputs.forEach((input) => {
  input.addEventListener("input", () => {
    if (!currentFace) {
      return;
    }

    currentFace.gridRegistration[input.dataset.registrationField] = input.value;
    validateRegistrationInput(input);
    updateEditorFinalizeControl();
    scheduleAutosave();
  });
});

finalizeButton.addEventListener("click", (event) => {
  const validation = updateEditorFinalizeControl();

  if (!validation.canFinalize) {
    event.preventDefault();
    return;
  }

  coordinateReport.textContent = validation.message;
});

faceTabs.addEventListener("click", (event) => {
  const tab = event.target.closest("button[data-face-index]");

  if (tab) {
    activateFace(Number(tab.dataset.faceIndex));
    scheduleAutosave();
  }
});

function renderFaceNameFields() {
  const existingNames = [
    ...faceNameFields.querySelectorAll("input"),
  ].map((input) => input.value);
  const requestedCount = isFieldWall
    ? 1
    : Math.max(1, Math.min(12, Number(faceCountInput.value) || 1));
  faceNameFields.replaceChildren();

  for (let faceIndex = 0; faceIndex < requestedCount; faceIndex += 1) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    label.textContent = requestedCount === 1
      ? "Face name"
      : `Face ${faceIndex + 1}`;
    input.type = "text";
    input.required = true;
    input.dataset.faceName = "";
    input.value = (
      existingNames[faceIndex]?.trim()
      || (isFieldWall ? "Wall" : `Face ${faceIndex + 1}`)
    );
    label.append(input);
    faceNameFields.append(label);
  }
}

faceCountInput.addEventListener("input", renderFaceNameFields);

faceSetupForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const nameInputs = [...faceNameFields.querySelectorAll("[data-face-name]")];
  const faceNames = nameInputs.map((input) => input.value.trim());
  const normalizedNames = faceNames.map((name) => name.toLocaleLowerCase());

  nameInputs.forEach((input) => input.setCustomValidity(""));
  const duplicateIndex = normalizedNames.findIndex((name, index) => (
    normalizedNames.indexOf(name) !== index
  ));

  if (duplicateIndex !== -1) {
    nameInputs[duplicateIndex].setCustomValidity("Face names must be unique.");
  }

  if (!faceSetupForm.reportValidity()) {
    return;
  }

  editorState.faces = faceNames.map(createFaceState);
  faceTabs.hidden = false;
  faceSetupDialog.close();
  activateFace(0);
  saveInitialFaceSetup();
});

retrySaveButton.addEventListener("click", () => {
  if (!hasValidEditorSession) {
    showInvalidSessionError();
    return;
  }

  debouncedAutosave.cancel();
  runAutosave();
});

window.addEventListener("pagehide", () => {
  if (!hasValidEditorSession || savedRevision === changeRevision) {
    return;
  }

  debouncedAutosave({ keepalive: true });
  debouncedAutosave.flush();
});

async function loadEditorSession() {
  if (!jobId) {
    return false;
  }

  const response = await fetch(
    `/editor/${encodeURIComponent(jobId)}/state`,
  );

  if (!response.ok) {
    throw new Error(`Could not load editor state (${response.status}).`);
  }

  const savedState = await response.json();

  if (Object.keys(savedState).length === 0) {
    return false;
  }

  if (
    !editorRoot
    && (
      savedState.schemaType === FIELD_WALL_SCHEMA
      || savedState.schemaType === "ArchaeologicalDiagram"
    )
  ) {
    schemaType = savedState.schemaType;
    isFieldWall = schemaType === FIELD_WALL_SCHEMA;
  }

  configureSchemaFields();
  return restoreEditorSession(savedState);
}

async function initializeEditor() {
  configureSchemaFields();
  faceCountInput.value = "1";
  renderFaceNameFields();

  if (!jobId) {
    showInvalidSessionError();
    return;
  }

  try {
    if (await loadEditorSession()) {
      return;
    }
  } catch (error) {
    console.error(error);
    showInvalidSessionError();
    return;
  }

  if (typeof faceSetupDialog.showModal === "function") {
    faceSetupDialog.showModal();
  } else {
    faceSetupDialog.setAttribute("open", "");
  }
}

initializeEditor();
