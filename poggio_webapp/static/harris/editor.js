import {
  applySavedResponse,
  createAutosaveController,
  saveRequestPayload,
  updateMatrixMetadata,
  validateMatrixPayload,
} from "./core.mjs";

const editor = document.querySelector("#harris-editor");
const form = document.querySelector("#matrix-metadata-form");
const status = document.querySelector("#save-status");
const conflictPanel = document.querySelector("#conflict-panel");
const reloadButton = document.querySelector("#reload-matrix");
const fields = {
  title: document.querySelector("#editor-title"),
  site: document.querySelector("#editor-site"),
  trench: document.querySelector("#editor-trench"),
  notes: document.querySelector("#editor-notes"),
};

let currentMatrix = null;

function setStatus(state) {
  const messages = {
    loading: "Loading…",
    unsaved: "Unsaved changes",
    saving: "Saving…",
    saved: "Saved",
    conflict: "Conflict: newer work exists",
    error: "Could not save changes",
  };
  status.dataset.state = state;
  status.textContent = messages[state];
  conflictPanel.hidden = state !== "conflict";
}

async function responseJson(response) {
  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }
  if (!response.ok) {
    const error = new Error(payload.error || "The request failed.");
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

function metadataFrom(matrix) {
  return {
    title: matrix.title,
    site: matrix.site,
    trench: matrix.trench,
    notes: matrix.notes,
  };
}

function metadataChanged(first, second) {
  return Object.keys(fields).some(field => first[field] !== second[field]);
}

function populateFields(matrix) {
  for (const [name, field] of Object.entries(fields)) {
    field.value = matrix[name];
    field.disabled = false;
  }
}

async function saveCurrentMatrix() {
  const snapshot = saveRequestPayload(currentMatrix);
  const response = await fetch(
    `/api/harris-matrices/${encodeURIComponent(snapshot.matrix_id)}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(snapshot),
    },
  );
  const saved = applySavedResponse(snapshot, await responseJson(response));
  const localMetadata = metadataFrom(currentMatrix);

  if (metadataChanged(localMetadata, metadataFrom(snapshot))) {
    currentMatrix = updateMatrixMetadata(saved, localMetadata);
  } else {
    currentMatrix = saved;
    populateFields(saved);
  }
}

const autosave = createAutosaveController({
  delayMs: 800,
  save: saveCurrentMatrix,
  onStatus: setStatus,
});

for (const [name, field] of Object.entries(fields)) {
  field.addEventListener("input", () => {
    if (currentMatrix === null) {
      return;
    }
    currentMatrix = updateMatrixMetadata(
      currentMatrix,
      { [name]: field.value },
    );
    autosave.schedule();
  });
}

form.addEventListener("submit", event => {
  event.preventDefault();
});

reloadButton.addEventListener("click", () => {
  window.location.reload();
});

async function loadMatrix() {
  setStatus("loading");
  try {
    const response = await fetch(
      `/api/harris-matrices/${encodeURIComponent(editor.dataset.matrixId)}`,
      { headers: { Accept: "application/json" } },
    );
    currentMatrix = validateMatrixPayload(await responseJson(response));
    populateFields(currentMatrix);
    setStatus("saved");
  } catch (_error) {
    setStatus("error");
  }
}

loadMatrix();
