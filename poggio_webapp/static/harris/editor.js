import { api, apiJson, responseJson } from "../shared/http.js";

import {
  addManualRelation,
  addManualUnit,
  applySavedResponse,
  createAutosaveController,
  filterUnits,
  formatSourceJobDisplay,
  groupSuggestionsByStatus,
  relationshipUnitOptions,
  removeCorrelation,
  removeRelation,
  removeUnitCascade,
  reviewSuggestionWithServer,
  saveRequestPayload,
  setCorrelation,
  summarizeUnitCascade,
  updateMatrixMetadata,
  updateUnit,
  validateMatrixPayload,
} from "./core.mjs";

const editor = document.querySelector("#harris-editor");
const metadataForm = document.querySelector("#matrix-metadata-form");
const status = document.querySelector("#save-status");
const editorError = document.querySelector("#editor-error");
const conflictPanel = document.querySelector("#conflict-panel");
const reloadButton = document.querySelector("#reload-matrix");
const metadataFields = {
  title: document.querySelector("#editor-title"),
  site: document.querySelector("#editor-site"),
  trench: document.querySelector("#editor-trench"),
  notes: document.querySelector("#editor-notes"),
};

const sourceList = document.querySelector("#source-job-list");
const importButton = document.querySelector("#import-sources");
const sourceStatus = document.querySelector("#source-status");
const importWarningRegion = document.querySelector(
  "#import-warning-region",
);
const importWarnings = document.querySelector("#import-warnings");

const unitFilter = document.querySelector("#unit-filter");
const addUnitForm = document.querySelector("#add-unit-form");
const unitTableBody = document.querySelector("#unit-table-body");
const unitEmpty = document.querySelector("#unit-empty");

const addRelationshipForm = document.querySelector(
  "#add-relationship-form",
);
const youngerSelect = document.querySelector("#younger-unit");
const olderSelect = document.querySelector("#older-unit");
const relationshipTableBody = document.querySelector(
  "#relationship-table-body",
);
const relationshipEmpty = document.querySelector("#relationship-empty");

const addCorrelationForm = document.querySelector(
  "#add-correlation-form",
);
const correlationSelect = document.querySelector("#correlation-units");
const correlationList = document.querySelector("#correlation-list");
const correlationEmpty = document.querySelector("#correlation-empty");

const reviewStatus = document.querySelector("#review-status");
const suggestionLists = {
  pending: document.querySelector("#pending-suggestions"),
  accepted: document.querySelector("#accepted-suggestions"),
  rejected: document.querySelector("#rejected-suggestions"),
};

const diagramPreview = document.querySelector("#diagram-preview");
const diagramEmpty = document.querySelector("#diagram-empty");
const diagramStatus = document.querySelector("#diagram-preview-status");
const downloadJson = document.querySelector("#download-json");
const downloadSvg = document.querySelector("#download-svg");
const printButton = document.querySelector("#print-matrix");
const printTitle = document.querySelector("#print-matrix-title");
const printFooter = document.querySelector("#print-matrix-footer");

const UNIT_TYPE_LABELS = {
  deposit: "Deposit",
  cut: "Cut",
  structure: "Structure",
  interface: "Interface",
  natural: "Natural",
  unknown: "Unknown",
};

const RELATION_KIND_LABELS = {
  above: "Above",
  cuts: "Cuts",
  fills: "Fills",
  precedes: "Precedes",
  other: "Other",
};

let currentMatrix = null;
let lastSavedMatrix = null;
let availableSources = [];
let reviewingSuggestionId = null;

function setEditorError(message = "") {
  editorError.textContent = message;
  editorError.hidden = message === "";
}

function setStatus(state, error = null) {
  const messages = {
    loading: "Loading…",
    unsaved: "Unsaved changes",
    saving: "Saving…",
    saved: "Saved",
    conflict: "Conflict: newer work exists",
    error: error?.message || "Could not save changes",
  };
  status.dataset.state = state;
  status.textContent = messages[state];
  conflictPanel.hidden = state !== "conflict";

  if (state === "error") {
    setEditorError(error?.message || "Could not save changes.");
  } else if (state === "saved") {
    setEditorError();
  }
}

function setSourceStatus(message, state = "") {
  sourceStatus.textContent = message;
  sourceStatus.dataset.state = state;
}

function setReviewStatus(message, state = "") {
  reviewStatus.textContent = message;
  reviewStatus.dataset.state = state;
}

function setDiagramStatus(message, state = "") {
  diagramStatus.textContent = message;
  diagramStatus.dataset.state = state;
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
  return Object.keys(metadataFields).some(
    field => first[field] !== second[field],
  );
}

function populateMetadata(matrix) {
  for (const [name, field] of Object.entries(metadataFields)) {
    field.value = matrix[name];
    field.disabled = false;
  }
}

function createElement(tagName, className = "", text = "") {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = text;
  return element;
}

function accessibleLabel(control, text) {
  const label = createElement("label", "visually-hidden", text);
  label.htmlFor = control.id;
  return label;
}

function objectId(prefix) {
  const bytes = new Uint8Array(6);
  globalThis.crypto.getRandomValues(bytes);
  const suffix = Array.from(
    bytes,
    byte => byte.toString(16).padStart(2, "0"),
  ).join("");
  return `${prefix}-${suffix}`;
}

function unitById(unitId) {
  return currentMatrix.units.find(unit => unit.id === unitId);
}

function unitLabel(unitId) {
  return unitById(unitId)?.label || `Missing unit ${unitId}`;
}

function unitOptionText(option) {
  return `${option.label} · ${option.value.slice(-6)}`;
}

function appendUnitOptions(select, { placeholder = false } = {}) {
  select.replaceChildren();
  if (placeholder) {
    const prompt = document.createElement("option");
    prompt.value = "";
    prompt.textContent = "Choose a unit";
    select.append(prompt);
  }
  for (const optionData of relationshipUnitOptions(
    currentMatrix.units,
  )) {
    const option = document.createElement("option");
    option.value = optionData.value;
    option.textContent = unitOptionText(optionData);
    select.append(option);
  }
}

function renderSources() {
  sourceList.replaceChildren();
  if (availableSources.length === 0) {
    sourceList.append(createElement(
      "p",
      "harris-empty",
      "No usable source drawing jobs were found.",
    ));
    importButton.disabled = true;
    return;
  }

  for (const source of availableSources) {
    const display = formatSourceJobDisplay(source);
    const item = createElement("div", "source-job");
    const checkbox = document.createElement("input");
    const label = createElement("label", "source-job-label");
    const title = createElement(
      "strong",
      "",
      `Job ${display.jobId}`,
    );
    const schema = createElement("span", "", display.schema);
    const context = createElement(
      "span",
      "",
      [
        display.trench ? `Trench ${display.trench}` : "No trench recorded",
        display.faces,
        display.unitCount,
      ].join(" · "),
    );

    checkbox.id = `source-job-${display.jobId}`;
    checkbox.type = "checkbox";
    checkbox.value = display.jobId;
    checkbox.addEventListener("change", updateImportButton);
    label.htmlFor = checkbox.id;
    label.append(title, schema, context);
    if (currentMatrix?.source_job_ids.includes(display.jobId)) {
      label.append(createElement(
        "span",
        "source-imported",
        "Already imported; select to refresh suggestions.",
      ));
    }
    item.append(checkbox, label);
    sourceList.append(item);
  }
  updateImportButton();
}

function selectedSourceIds() {
  return Array.from(
    sourceList.querySelectorAll('input[type="checkbox"]:checked'),
    checkbox => checkbox.value,
  );
}

function updateImportButton() {
  importButton.disabled = (
    currentMatrix === null
    || selectedSourceIds().length === 0
  );
}

function renderImportWarnings(warnings) {
  importWarnings.replaceChildren();
  importWarningRegion.hidden = warnings.length === 0;
  for (const warning of warnings) {
    const item = document.createElement("li");
    const code = typeof warning?.code === "string"
      ? warning.code
      : "import-warning";
    const message = typeof warning?.message === "string"
      ? warning.message
      : "The source job produced an import warning.";
    item.textContent = `${code}: ${message}`;
    importWarnings.append(item);
  }
}

function unitWarning(unit) {
  if (unit.source_refs.length === 0) {
    return "";
  }
  if (unit.source_refs.some(sourceRef => (
    sourceRef.source_label === null
    || sourceRef.source_label.trim() === ""
  ))) {
    return "Warning: this imported unit had no source label.";
  }
  const genericLabel = /^(polygon|layer|shape|unit)\s*[-_#]?\s*\d+$/i;
  if (
    genericLabel.test(unit.label.trim())
    || unit.source_refs.some(sourceRef => (
      sourceRef.source_label !== null
      && genericLabel.test(sourceRef.source_label.trim())
    ))
  ) {
    return "Warning: this imported unit has a generic label.";
  }
  return "";
}

function appendSourceRefs(cell, unit) {
  if (unit.source_refs.length === 0) {
    cell.append(createElement("span", "source-ref", "Manual unit"));
    return;
  }
  const list = createElement("ul", "source-ref-list");
  for (const sourceRef of unit.source_refs) {
    const face = sourceRef.face || "No recorded face";
    const sourceLabel = sourceRef.source_label === null
      ? "unlabeled"
      : `source label ${sourceRef.source_label}`;
    list.append(createElement(
      "li",
      "",
      (
        `Job ${sourceRef.job_id} · ${face} · `
        + `layer index ${sourceRef.layer_index} · ${sourceLabel}`
      ),
    ));
  }
  cell.append(list);
}

function unitTypeSelect(unit) {
  const select = document.createElement("select");
  select.id = `unit-type-${unit.id}`;
  for (const [value, label] of Object.entries(UNIT_TYPE_LABELS)) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = value === unit.unit_type;
    select.append(option);
  }
  select.addEventListener("change", () => {
    applyLocalChange(matrix => updateUnit(
      matrix,
      unit.id,
      { unit_type: select.value },
    ));
  });
  return select;
}

function renderUnits() {
  unitTableBody.replaceChildren();
  if (currentMatrix === null) {
    unitEmpty.hidden = false;
    return;
  }

  const visibleUnits = filterUnits(currentMatrix.units, unitFilter.value);
  unitEmpty.hidden = visibleUnits.length > 0;
  for (const unit of visibleUnits) {
    const row = document.createElement("tr");
    const identityCell = document.createElement("td");
    const descriptionCell = document.createElement("td");
    const sourceCell = document.createElement("td");
    const actionsCell = document.createElement("td");
    const labelInput = document.createElement("input");
    const descriptionInput = document.createElement("input");
    const typeSelect = unitTypeSelect(unit);
    const deleteButton = document.createElement("button");

    labelInput.id = `unit-label-${unit.id}`;
    labelInput.type = "text";
    labelInput.required = true;
    labelInput.value = unit.label;
    labelInput.addEventListener("input", () => {
      updateUnitWithoutRender(
        unit.id,
        { label: labelInput.value },
      );
    });
    labelInput.addEventListener("change", renderEditorSections);
    identityCell.append(
      accessibleLabel(labelInput, `Label for unit ${unit.label}`),
      labelInput,
      accessibleLabel(typeSelect, `Type for unit ${unit.label}`),
      typeSelect,
    );

    const warning = unitWarning(unit);
    if (warning) {
      identityCell.append(createElement(
        "span",
        "unit-warning",
        warning,
      ));
    }

    descriptionInput.id = `unit-description-${unit.id}`;
    descriptionInput.type = "text";
    descriptionInput.value = unit.description ?? "";
    descriptionInput.addEventListener("input", () => {
      updateUnitWithoutRender(
        unit.id,
        { description: descriptionInput.value.trim() || null },
      );
    });
    descriptionInput.addEventListener("change", renderEditorSections);
    descriptionCell.append(
      accessibleLabel(
        descriptionInput,
        `Description for unit ${unit.label}`,
      ),
      descriptionInput,
    );

    appendSourceRefs(sourceCell, unit);

    deleteButton.type = "button";
    deleteButton.className = "danger-button";
    deleteButton.textContent = `Delete ${unit.label}`;
    deleteButton.addEventListener("click", () => {
      const summary = summarizeUnitCascade(currentMatrix, unit.id);
      if (!globalThis.confirm(summary.message)) {
        return;
      }
      applyLocalChange(matrix => removeUnitCascade(matrix, unit.id));
    });
    actionsCell.append(deleteButton);

    row.append(identityCell, descriptionCell, sourceCell, actionsCell);
    unitTableBody.append(row);
  }
}

function renderRelationshipForm() {
  appendUnitOptions(youngerSelect, { placeholder: true });
  appendUnitOptions(olderSelect, { placeholder: true });
  const submit = addRelationshipForm.querySelector(
    'button[type="submit"]',
  );
  submit.disabled = currentMatrix.units.length < 2;
}

function renderRelationships() {
  relationshipTableBody.replaceChildren();
  relationshipEmpty.hidden = currentMatrix.relations.length > 0;
  for (const relationship of currentMatrix.relations) {
    const row = document.createElement("tr");
    const chronology = createElement(
      "td",
      "",
      (
        `${unitLabel(relationship.younger_id)} is younger than `
        + `${unitLabel(relationship.older_id)}.`
      ),
    );
    const kind = createElement(
      "td",
      "",
      RELATION_KIND_LABELS[relationship.kind] || relationship.kind,
    );
    const detail = document.createElement("td");
    const actions = document.createElement("td");
    const deleteButton = document.createElement("button");

    detail.append(createElement(
      "span",
      "record-detail",
      relationship.evidence
        ? `Evidence: ${relationship.evidence}`
        : "No evidence recorded.",
    ));
    if (relationship.notes) {
      detail.append(createElement(
        "span",
        "record-detail",
        `Notes: ${relationship.notes}`,
      ));
    }
    deleteButton.type = "button";
    deleteButton.className = "danger-button";
    deleteButton.textContent = (
      `Delete relationship from ${unitLabel(relationship.younger_id)} `
      + `to ${unitLabel(relationship.older_id)}`
    );
    deleteButton.addEventListener("click", () => {
      if (!globalThis.confirm(
        "Delete this younger-to-older relationship? "
        + "This cannot be undone.",
      )) {
        return;
      }
      applyLocalChange(matrix => removeRelation(
        matrix,
        relationship.id,
      ));
    });
    actions.append(deleteButton);
    row.append(chronology, kind, detail, actions);
    relationshipTableBody.append(row);
  }
}

function renderCorrelationForm() {
  appendUnitOptions(correlationSelect);
  const submit = addCorrelationForm.querySelector(
    'button[type="submit"]',
  );
  submit.disabled = currentMatrix.units.length < 2;
}

function renderCorrelations() {
  correlationList.replaceChildren();
  correlationEmpty.hidden = currentMatrix.correlations.length > 0;
  for (const correlation of currentMatrix.correlations) {
    const item = createElement("li", "record-list-item");
    const content = createElement("div");
    const deleteButton = document.createElement("button");
    content.append(createElement(
      "strong",
      "",
      correlation.unit_ids.map(unitLabel).join(" = "),
    ));
    if (correlation.notes) {
      content.append(createElement(
        "span",
        "record-detail",
        correlation.notes,
      ));
    }
    deleteButton.type = "button";
    deleteButton.className = "danger-button";
    deleteButton.textContent = (
      `Remove correlation for ${correlation.unit_ids
        .map(unitLabel)
        .join(", ")}`
    );
    deleteButton.addEventListener("click", () => {
      if (!globalThis.confirm(
        "Remove this correlation group? The source units will remain.",
      )) {
        return;
      }
      applyLocalChange(matrix => removeCorrelation(
        matrix,
        correlation.id,
      ));
    });
    item.append(content, deleteButton);
    correlationList.append(item);
  }
}

function suggestionDescription(suggestion) {
  if (suggestion.suggestion_type === "ordering") {
    return (
      `${unitLabel(suggestion.younger_id)} is younger than `
      + `${unitLabel(suggestion.older_id)} `
      + `(${suggestion.relation_kind}).`
    );
  }
  return (
    "Correlate "
    + suggestion.correlation_unit_ids.map(unitLabel).join(" with ")
    + "."
  );
}

function renderSuggestionGroup(statusName, suggestions) {
  const list = suggestionLists[statusName];
  list.replaceChildren();
  if (suggestions.length === 0) {
    list.append(createElement(
      "li",
      "harris-empty",
      `No ${statusName} suggestions.`,
    ));
    return;
  }

  for (const suggestion of suggestions) {
    const item = createElement("li", "suggestion-item");
    const description = createElement("strong");
    const reason = createElement("span", "record-detail");
    description.textContent = suggestionDescription(suggestion);
    reason.textContent = suggestion.reason;
    item.append(description, reason);

    if (statusName === "pending") {
      const actions = createElement("div", "suggestion-actions");
      for (const action of ["accept", "reject"]) {
        const button = document.createElement("button");
        button.type = "button";
        button.disabled = reviewingSuggestionId === suggestion.id;
        button.textContent = (
          action === "accept" ? "Accept suggestion" : "Reject suggestion"
        );
        if (action === "reject") {
          button.className = "secondary-button";
        }
        button.addEventListener("click", () => {
          reviewSuggestion(suggestion.id, action);
        });
        actions.append(button);
      }
      item.append(actions);
    }
    list.append(item);
  }
}

function renderSuggestions() {
  const grouped = groupSuggestionsByStatus(currentMatrix);
  for (const statusName of ["pending", "accepted", "rejected"]) {
    renderSuggestionGroup(statusName, grouped[statusName]);
  }
}

function renderEditorSections() {
  renderSources();
  renderUnits();
  renderRelationshipForm();
  renderRelationships();
  renderCorrelationForm();
  renderCorrelations();
  renderSuggestions();
}

function refreshSavedDiagram(matrix) {
  const matrixId = encodeURIComponent(matrix.matrix_id);
  const exportBase = `/api/harris-matrices/${matrixId}/export`;
  downloadJson.href = `${exportBase}.json`;
  downloadSvg.href = `${exportBase}.svg`;
  printTitle.textContent = matrix.title || "Untitled Harris Matrix";
  printFooter.textContent = (
    `${matrix.site || "Site not recorded"} · `
    + `${matrix.trench ? `Trench ${matrix.trench}` : "Trench not recorded"}`
    + ` · Saved revision ${matrix.revision} · ${matrix.updated_at}`
  );

  if (matrix.units.length === 0) {
    diagramPreview.hidden = true;
    diagramPreview.removeAttribute("src");
    diagramEmpty.hidden = false;
    printButton.disabled = false;
    setDiagramStatus("The saved matrix has no units.", "saved");
    return;
  }

  diagramEmpty.hidden = true;
  diagramPreview.hidden = true;
  printButton.disabled = true;
  setDiagramStatus("Loading saved diagram…", "loading");
  diagramPreview.src = (
    `${exportBase}.svg?inline=1`
    + `&revision=${encodeURIComponent(matrix.revision)}`
  );
}

diagramPreview.addEventListener("load", () => {
  diagramPreview.hidden = false;
  printButton.disabled = false;
  setDiagramStatus("Saved diagram is up to date.", "saved");
});

diagramPreview.addEventListener("error", () => {
  diagramPreview.hidden = true;
  printButton.disabled = true;
  setDiagramStatus(
    "The saved diagram could not be rendered. Check the matrix graph.",
    "error",
  );
});

function restoreLastSavedMatrix() {
  if (lastSavedMatrix === null) {
    return;
  }
  currentMatrix = validateMatrixPayload(lastSavedMatrix);
  populateMetadata(currentMatrix);
  renderEditorSections();
}

async function saveCurrentMatrix() {
  const snapshot = saveRequestPayload(currentMatrix);
  let saved;
  try {
    saved = applySavedResponse(snapshot, await apiJson(
      `/api/harris-matrices/${encodeURIComponent(snapshot.matrix_id)}`,
      snapshot,
      "PUT",
    ));
  } catch (error) {
    if (
      error?.status === 400
      && error?.payload?.code === "invalid_matrix"
    ) {
      restoreLastSavedMatrix();
    }
    throw error;
  }

  const localSnapshot = saveRequestPayload(currentMatrix);
  const changedWhileSaving = (
    JSON.stringify(localSnapshot) !== JSON.stringify(snapshot)
  );
  lastSavedMatrix = saved;
  refreshSavedDiagram(saved);
  if (changedWhileSaving) {
    localSnapshot.revision = saved.revision;
    localSnapshot.updated_at = saved.updated_at;
    currentMatrix = validateMatrixPayload(localSnapshot);
  } else {
    currentMatrix = saved;
    populateMetadata(saved);
    renderEditorSections();
  }
}

const autosave = createAutosaveController({
  delayMs: 800,
  save: saveCurrentMatrix,
  onStatus: setStatus,
});

function applyLocalChange(change) {
  if (currentMatrix === null) {
    return false;
  }
  try {
    currentMatrix = change(currentMatrix);
  } catch (error) {
    setEditorError(error.message || "The change is invalid.");
    renderEditorSections();
    return false;
  }
  setEditorError();
  renderEditorSections();
  autosave.schedule();
  return true;
}

function updateUnitWithoutRender(unitId, patch) {
  if (currentMatrix === null) {
    return;
  }
  try {
    currentMatrix = updateUnit(currentMatrix, unitId, patch);
  } catch (error) {
    setEditorError(error.message || "The unit change is invalid.");
    return;
  }
  setEditorError();
  autosave.schedule();
}

async function prepareServerAction() {
  if (autosave.status === "saving") {
    throw new Error("Wait for the current save to finish, then try again.");
  }
  if (autosave.status === "conflict") {
    throw new Error("Reload the newer matrix version before continuing.");
  }
  if (autosave.status === "unsaved") {
    await autosave.flush();
    if (autosave.status !== "saved") {
      throw new Error(status.textContent);
    }
  }
}

async function importSelectedSources() {
  const jobIds = selectedSourceIds();
  if (jobIds.length === 0) {
    setSourceStatus("Select at least one drawing job.", "error");
    return;
  }
  if (!globalThis.confirm(
    `Import ${jobIds.length} selected drawing ${
      jobIds.length === 1 ? "job" : "jobs"
    }? Source files will not be changed.`,
  )) {
    return;
  }

  importButton.disabled = true;
  setSourceStatus("Importing selected jobs…", "saving");
  try {
    await prepareServerAction();
    const before = currentMatrix;
    const payload = await apiJson(
      (
        `/api/harris-matrices/${encodeURIComponent(before.matrix_id)}`
        + "/sources"
      ),
      { job_ids: jobIds, revision: before.revision },
    );
    const warnings = Array.isArray(payload.import_warnings)
      ? payload.import_warnings
      : [];
    currentMatrix = applySavedResponse(before, payload);
    lastSavedMatrix = currentMatrix;
    populateMetadata(currentMatrix);
    renderImportWarnings(warnings);
    renderEditorSections();
    refreshSavedDiagram(currentMatrix);
    setStatus("saved");
    setSourceStatus(
      `Imported ${jobIds.length} drawing ${
        jobIds.length === 1 ? "job" : "jobs"
      }.`,
      "saved",
    );
  } catch (error) {
    if (error?.status === 409) {
      setStatus("conflict", error);
    }
    setSourceStatus(
      error.message || "Could not import the selected jobs.",
      "error",
    );
  } finally {
    updateImportButton();
  }
}

async function sendSuggestionReview(request) {
  const response = await apiJson(
    (
      `/api/harris-matrices/${encodeURIComponent(request.matrixId)}`
      + `/suggestions/${encodeURIComponent(request.suggestionId)}`
    ),
    { action: request.action, revision: request.revision },
  );
  return response;
}

async function reviewSuggestion(suggestionId, action) {
  reviewingSuggestionId = suggestionId;
  renderSuggestions();
  setReviewStatus(
    action === "accept" ? "Accepting suggestion…" : "Rejecting suggestion…",
    "saving",
  );
  try {
    await prepareServerAction();
    const before = currentMatrix;
    const reviewed = await reviewSuggestionWithServer(
      before,
      suggestionId,
      action,
      sendSuggestionReview,
    );
    currentMatrix = reviewed;
    lastSavedMatrix = reviewed;
    populateMetadata(reviewed);
    renderEditorSections();
    refreshSavedDiagram(reviewed);
    setStatus("saved");
    setReviewStatus(
      action === "accept"
        ? "Suggestion accepted."
        : "Suggestion rejected.",
      "saved",
    );
  } catch (error) {
    if (error?.status === 409) {
      setStatus("conflict", error);
    } else {
      setEditorError(error.message || "Could not review the suggestion.");
    }
    setReviewStatus(
      error.message || "Could not review the suggestion.",
      "error",
    );
  } finally {
    reviewingSuggestionId = null;
    renderSuggestions();
  }
}

for (const [name, field] of Object.entries(metadataFields)) {
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

metadataForm.addEventListener("submit", event => {
  event.preventDefault();
});

unitFilter.addEventListener("input", renderUnits);

addUnitForm.addEventListener("submit", event => {
  event.preventDefault();
  const data = new FormData(addUnitForm);
  const added = applyLocalChange(matrix => addManualUnit(
    matrix,
    {
      label: data.get("label"),
      unit_type: data.get("unit_type"),
      description: String(data.get("description")).trim() || null,
    },
    objectId("unit"),
  ));
  if (added) {
    addUnitForm.reset();
  }
});

addRelationshipForm.addEventListener("submit", event => {
  event.preventDefault();
  const data = new FormData(addRelationshipForm);
  if (data.get("younger_id") === data.get("older_id")) {
    setEditorError(
      "Younger unit and older unit must be different units.",
    );
    olderSelect.focus();
    return;
  }
  const added = applyLocalChange(matrix => addManualRelation(
    matrix,
    {
      younger_id: data.get("younger_id"),
      older_id: data.get("older_id"),
      kind: data.get("kind"),
      evidence: data.get("evidence"),
      notes: String(data.get("notes")).trim() || null,
    },
    objectId("rel"),
  ));
  if (added) {
    addRelationshipForm.reset();
  }
});

addCorrelationForm.addEventListener("submit", event => {
  event.preventDefault();
  const unitIds = Array.from(
    correlationSelect.selectedOptions,
    option => option.value,
  );
  if (new Set(unitIds).size < 2) {
    setEditorError("Select at least two distinct units to correlate.");
    correlationSelect.focus();
    return;
  }
  const data = new FormData(addCorrelationForm);
  const added = applyLocalChange(matrix => setCorrelation(
    matrix,
    unitIds,
    objectId("corr"),
    String(data.get("notes")).trim() || null,
  ));
  if (added) {
    addCorrelationForm.reset();
  }
});

importButton.addEventListener("click", importSelectedSources);

reloadButton.addEventListener("click", () => {
  globalThis.location.reload();
});

printButton.addEventListener("click", () => {
  globalThis.print();
});

async function loadMatrix() {
  setStatus("loading");
  try {
    currentMatrix = validateMatrixPayload(await api(
      `/api/harris-matrices/${encodeURIComponent(editor.dataset.matrixId)}`,
    ));
    lastSavedMatrix = currentMatrix;
    populateMetadata(currentMatrix);
    renderEditorSections();
    refreshSavedDiagram(currentMatrix);
    setStatus("saved");
  } catch (error) {
    setStatus("error", error);
  }
}

async function loadSourceJobs() {
  setSourceStatus("Loading source jobs…", "loading");
  try {
    const payload = await api("/api/harris-source-jobs");
    if (!Array.isArray(payload)) {
      throw new TypeError("Source job response must be a list.");
    }
    availableSources = payload;
    renderSources();
    setSourceStatus(
      payload.length === 0
        ? "No usable source drawing jobs found."
        : `${payload.length} usable drawing ${
          payload.length === 1 ? "job" : "jobs"
        } found.`,
      "saved",
    );
  } catch (error) {
    availableSources = [];
    renderSources();
    setSourceStatus(
      error.message || "Could not load source drawing jobs.",
      "error",
    );
  }
}

loadMatrix();
loadSourceJobs();
