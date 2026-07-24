import {
  CANVAS_HEIGHT_METERS,
  CANVAS_WIDTH_METERS,
  GRID_SPACING_METERS,
  PIXELS_PER_METER,
  edgeMidpoint,
  hasSelfIntersection,
  isShapeClosed,
  metersToPixels,
  nearestGridPoint,
  pixelsToMeters,
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
const canvas = document.querySelector("#face-canvas");
const snapToggle = document.querySelector("#snap-to-grid");
const closeShapeButton = document.querySelector("#close-shape");
const deleteVertexButton = document.querySelector("#delete-vertex");
const coordinateReport = document.querySelector("#coordinate-report");

const widthPixels = metersToPixels(CANVAS_WIDTH_METERS, PIXELS_PER_METER);
const heightPixels = metersToPixels(CANVAS_HEIGHT_METERS, PIXELS_PER_METER);
const gridSpacingPixels = metersToPixels(GRID_SPACING_METERS, PIXELS_PER_METER);
let nextPolygonId = 1;
let selectedVertex = null;
let pointerAction = null;

canvas.setAttribute("width", widthPixels);
canvas.setAttribute("height", heightPixels);
canvas.setAttribute("viewBox", `0 0 ${widthPixels} ${heightPixels}`);

function createSvgElement(name, attributes = {}) {
  const element = document.createElementNS(SVG_NAMESPACE, name);

  for (const [attribute, value] of Object.entries(attributes)) {
    element.setAttribute(attribute, value);
  }

  return element;
}

function createPolygon() {
  const id = nextPolygonId;
  nextPolygonId += 1;

  return {
    id,
    color: POLYGON_COLORS[(id - 1) % POLYGON_COLORS.length],
    vertices: [],
    closed: false,
  };
}

const polygons = [createPolygon()];
let currentPolygon = polygons[0];

const grid = document.createElementNS(SVG_NAMESPACE, "g");
grid.setAttribute("aria-hidden", "true");

function addGridLine(x1, y1, x2, y2) {
  const line = document.createElementNS(SVG_NAMESPACE, "line");
  line.setAttribute("class", "grid-line");
  line.setAttribute("x1", x1);
  line.setAttribute("y1", y1);
  line.setAttribute("x2", x2);
  line.setAttribute("y2", y2);
  grid.append(line);
}

for (let x = 0; x <= widthPixels; x += gridSpacingPixels) {
  addGridLine(x, 0, x, heightPixels);
}

for (let y = 0; y <= heightPixels; y += gridSpacingPixels) {
  addGridLine(0, y, widthPixels, y);
}

canvas.append(grid);

function findPolygon(polygonId) {
  return polygons.find((polygon) => polygon.id === polygonId);
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

canvas.addEventListener("pointerdown", beginCanvasPointerAction);
canvas.addEventListener("pointermove", continueCanvasPointerAction);
canvas.addEventListener("pointerup", finishCanvasPointerAction);
canvas.addEventListener("pointercancel", cancelCanvasPointerAction);

closeShapeButton.addEventListener("pointerup", (event) => {
  if (!event.isPrimary || currentPolygon.vertices.length < 3) {
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
  currentPolygon = createPolygon();
  polygons.push(currentPolygon);
  selectedVertex = null;
  renderPolygons();
});

deleteVertexButton.addEventListener("pointerup", (event) => {
  if (!event.isPrimary || !selectedVertexExists()) {
    return;
  }

  event.preventDefault();
  removeVertex(selectedVertex);
});

renderPolygons();
