import {
  CANVAS_HEIGHT_METERS,
  CANVAS_WIDTH_METERS,
  GRID_SPACING_METERS,
  PIXELS_PER_METER,
  metersToPixels,
  pixelsToMeters,
} from "../canvas/grid.mjs";

const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
const POINTER_CLICK_THRESHOLD_PIXELS = 5;
const widthPixels = metersToPixels(
  CANVAS_WIDTH_METERS,
  PIXELS_PER_METER,
);
const heightPixels = metersToPixels(
  CANVAS_HEIGHT_METERS,
  PIXELS_PER_METER,
);
const gridSpacingPixels = metersToPixels(
  GRID_SPACING_METERS,
  PIXELS_PER_METER,
);

const jobSelect = document.querySelector("#job-select");
const locationPanel = document.querySelector("#location-panel");
const detailsPanel = document.querySelector("#details-panel");
const findsPanel = document.querySelector("#finds-panel");
const faceSelectField = document.querySelector("#face-select-field");
const faceInputField = document.querySelector("#face-input-field");
const faceSelect = document.querySelector("#face-select");
const faceInput = document.querySelector("#face-input");
const canvas = document.querySelector("#reference-canvas");
const pointStatus = document.querySelector("#point-status");
const form = document.querySelector("#find-form");
const xInput = document.querySelector("#find-x");
const yInput = document.querySelector("#find-y");
const elevationInput = document.querySelector("#find-elevation");
const locusInput = document.querySelector("#find-locus");
const descriptionInput = document.querySelector("#find-description");
const submitButton = document.querySelector("#submit-find");
const formStatus = document.querySelector("#form-status");
const findsList = document.querySelector("#finds-list");

let currentJobId = "";
let faces = [];
let selectedPoint = null;
let pointerStart = null;

function createSvgElement(name, attributes = {}) {
  const element = document.createElementNS(SVG_NAMESPACE, name);
  Object.entries(attributes).forEach(([attribute, value]) => {
    element.setAttribute(attribute, value);
  });
  return element;
}

function createGrid() {
  const grid = createSvgElement("g", { "aria-hidden": "true" });

  for (let x = 0; x <= widthPixels; x += gridSpacingPixels) {
    grid.append(createSvgElement("line", {
      class: "reference-grid-line",
      x1: x,
      y1: 0,
      x2: x,
      y2: heightPixels,
    }));
  }

  for (let y = 0; y <= heightPixels; y += gridSpacingPixels) {
    grid.append(createSvgElement("line", {
      class: "reference-grid-line",
      x1: 0,
      y1: y,
      x2: widthPixels,
      y2: y,
    }));
  }

  return grid;
}

function activeFace() {
  if (faces.length === 0) {
    return null;
  }
  return faces.find((face) => face.name === faceSelect.value) ?? faces[0];
}

function renderCanvas() {
  canvas.replaceChildren(createGrid());
  const face = activeFace();

  for (const polygon of face?.polygons ?? []) {
    const vertices = polygon.vertices ?? [];
    if (vertices.length === 0) {
      continue;
    }
    const color = polygon.color ?? "#7b624d";
    canvas.append(createSvgElement("polygon", {
      class: "reference-polygon",
      points: vertices.map(({ x, y }) => `${x},${y}`).join(" "),
      fill: color,
      stroke: color,
    }));
  }

  if (selectedPoint) {
    canvas.append(createSvgElement("circle", {
      class: "find-point",
      cx: selectedPoint.pixelX,
      cy: selectedPoint.pixelY,
      r: 7,
    }));
  }
}

function setSelectedPoint(point) {
  selectedPoint = point;
  xInput.value = point.x.toFixed(3);
  yInput.value = point.y.toFixed(3);
  pointStatus.textContent = (
    `Marked (${point.x.toFixed(3)}m, ${point.y.toFixed(3)}m).`
  );
  detailsPanel.hidden = false;
  renderCanvas();
}

function canvasPoint(event) {
  const bounds = canvas.getBoundingClientRect();
  const pixelX = Math.max(0, Math.min(
    widthPixels,
    (event.clientX - bounds.left) * (widthPixels / bounds.width),
  ));
  const pixelY = Math.max(0, Math.min(
    heightPixels,
    (event.clientY - bounds.top) * (heightPixels / bounds.height),
  ));

  return {
    pixelX,
    pixelY,
    x: pixelsToMeters(pixelX, PIXELS_PER_METER),
    y: pixelsToMeters(pixelY, PIXELS_PER_METER),
  };
}

function faceId() {
  return faces.length > 0 ? faceSelect.value : faceInput.value.trim();
}

function clearSelectedPoint() {
  selectedPoint = null;
  xInput.value = "";
  yInput.value = "";
  detailsPanel.hidden = true;
  pointStatus.textContent = "Tap or click the canvas to mark the find.";
  renderCanvas();
}

function savedFaces(state) {
  const availableFaces = (
    state?.resumeState?.faces
    ?? state?.editorState?.faces
  );
  return Array.isArray(availableFaces)
    ? availableFaces.filter((face) => face?.name)
    : [];
}

function configureFaces(state) {
  faces = savedFaces(state);
  faceSelect.replaceChildren();

  if (faces.length > 0) {
    for (const face of faces) {
      const option = document.createElement("option");
      option.value = face.name;
      option.textContent = face.name;
      faceSelect.append(option);
    }
    faceSelect.disabled = false;
    faceSelectField.hidden = false;
    faceInput.disabled = true;
    faceInputField.hidden = true;
  } else {
    faceSelect.disabled = true;
    faceSelectField.hidden = true;
    faceInput.disabled = false;
    faceInput.value = "";
    faceInputField.hidden = false;
  }

  clearSelectedPoint();
}

async function responseJson(response) {
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error ?? `Request failed (${response.status}).`);
  }
  return body;
}

function createCell(text) {
  const cell = document.createElement("td");
  cell.textContent = text;
  return cell;
}

function renderFinds(finds) {
  findsList.replaceChildren();

  if (finds.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-finds";
    empty.textContent = "No finds logged for this job yet.";
    findsList.append(empty);
    return;
  }

  const grouped = new Map();
  for (const find of finds) {
    const group = grouped.get(find.face_id) ?? [];
    group.push(find);
    grouped.set(find.face_id, group);
  }

  for (const [faceName, faceFinds] of grouped) {
    const group = document.createElement("section");
    const heading = document.createElement("h3");
    const tableWrap = document.createElement("div");
    const table = document.createElement("table");
    const head = document.createElement("thead");
    const body = document.createElement("tbody");
    const headingRow = document.createElement("tr");

    group.className = "find-face-group";
    heading.textContent = faceName;
    tableWrap.className = "table-wrap";
    table.className = "data-table finds-table";

    for (const label of [
      "Locus",
      "X",
      "Y",
      "Elevation",
      "Description",
      "",
    ]) {
      const header = document.createElement("th");
      header.scope = "col";
      header.textContent = label;
      headingRow.append(header);
    }
    head.append(headingRow);

    for (const find of faceFinds) {
      const row = document.createElement("tr");
      const actionCell = document.createElement("td");
      const deleteButton = document.createElement("button");

      deleteButton.type = "button";
      deleteButton.dataset.findId = find.find_id;
      deleteButton.textContent = "Delete";
      actionCell.append(deleteButton);
      row.append(
        createCell(find.locus),
        createCell(find.x),
        createCell(find.y),
        createCell(find.elevation),
        createCell(find.description),
        actionCell,
      );
      body.append(row);
    }

    table.append(head, body);
    tableWrap.append(table);
    group.append(heading, tableWrap);
    findsList.append(group);
  }
}

async function loadFinds() {
  const response = await fetch(`/finds/${encodeURIComponent(currentJobId)}`);
  renderFinds(await responseJson(response));
}

async function selectJob(jobId) {
  currentJobId = jobId;
  locationPanel.hidden = !jobId;
  detailsPanel.hidden = true;
  findsPanel.hidden = !jobId;
  formStatus.textContent = "";

  if (!jobId) {
    return;
  }

  const encodedJobId = encodeURIComponent(jobId);
  const [stateResponse, findsResponse] = await Promise.all([
    fetch(`/editor/${encodedJobId}/state`),
    fetch(`/finds/${encodedJobId}`),
  ]);
  configureFaces(await responseJson(stateResponse));
  renderFinds(await responseJson(findsResponse));

  const pageUrl = new URL(window.location);
  pageUrl.searchParams.set("job_id", jobId);
  window.history.replaceState({}, "", pageUrl);
}

canvas.addEventListener("pointerdown", (event) => {
  if (!event.isPrimary || (event.pointerType === "mouse" && event.button !== 0)) {
    return;
  }
  event.preventDefault();
  pointerStart = {
    pointerId: event.pointerId,
    clientX: event.clientX,
    clientY: event.clientY,
  };
  canvas.setPointerCapture(event.pointerId);
});

canvas.addEventListener("pointerup", (event) => {
  if (!pointerStart || event.pointerId !== pointerStart.pointerId) {
    return;
  }
  event.preventDefault();
  const distance = Math.hypot(
    event.clientX - pointerStart.clientX,
    event.clientY - pointerStart.clientY,
  );
  pointerStart = null;

  if (distance <= POINTER_CLICK_THRESHOLD_PIXELS) {
    setSelectedPoint(canvasPoint(event));
  }
});

canvas.addEventListener("pointercancel", () => {
  pointerStart = null;
});

faceSelect.addEventListener("change", clearSelectedPoint);

jobSelect.addEventListener("change", () => {
  selectJob(jobSelect.value).catch((error) => {
    formStatus.textContent = error.message;
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!selectedPoint || !faceId()) {
    formStatus.textContent = "Choose a face and mark a point first.";
    return;
  }

  submitButton.disabled = true;
  formStatus.textContent = "Saving…";
  try {
    const response = await fetch(
      `/finds/${encodeURIComponent(currentJobId)}/new`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          face_id: faceId(),
          x: selectedPoint.x,
          y: selectedPoint.y,
          elevation: Number(elevationInput.value),
          locus: locusInput.value,
          description: descriptionInput.value,
        }),
      },
    );
    await responseJson(response);
    elevationInput.value = "";
    locusInput.value = "";
    descriptionInput.value = "";
    clearSelectedPoint();
    await loadFinds();
    formStatus.textContent = "Find logged.";
  } catch (error) {
    formStatus.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
});

findsList.addEventListener("click", async (event) => {
  const deleteButton = event.target.closest("[data-find-id]");
  if (!deleteButton) {
    return;
  }

  deleteButton.disabled = true;
  formStatus.textContent = "Deleting…";
  try {
    const response = await fetch(
      `/finds/${encodeURIComponent(currentJobId)}/`
      + encodeURIComponent(deleteButton.dataset.findId),
      { method: "DELETE" },
    );
    await responseJson(response);
    await loadFinds();
    formStatus.textContent = "Find deleted.";
  } catch (error) {
    deleteButton.disabled = false;
    formStatus.textContent = error.message;
  }
});

const requestedJobId = new URLSearchParams(window.location.search).get("job_id");
if (
  requestedJobId
  && [...jobSelect.options].some((option) => option.value === requestedJobId)
) {
  jobSelect.value = requestedJobId;
  selectJob(requestedJobId).catch((error) => {
    formStatus.textContent = error.message;
  });
}
