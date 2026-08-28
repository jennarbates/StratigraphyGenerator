import { api, apiJson, responseJson } from "../shared/http.js";

const form = document.querySelector("#create-matrix-form");
const list = document.querySelector("#matrix-list");
const status = document.querySelector("#dashboard-status");
const sourceList = document.querySelector("#dashboard-source-job-list");
const sourceStatus = document.querySelector("#dashboard-source-status");
const requestedSourceJobId = new URLSearchParams(
  window.location.search,
).get("source_job");
const validRequestedSourceJobId = /^[0-9a-f]{12}$/.test(
  requestedSourceJobId || "",
) ? requestedSourceJobId : null;

function setStatus(message, state = "") {
  status.textContent = message;
  status.dataset.state = state;
}


function countLabel(count, singular) {
  return `${count} ${singular}${count === 1 ? "" : "s"}`;
}

function updatedLabel(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function selectedSourceIds() {
  return Array.from(
    sourceList.querySelectorAll('input[type="checkbox"]:checked'),
    checkbox => checkbox.value,
  );
}

function updateMatrixImportButtons() {
  const count = selectedSourceIds().length;
  for (const button of list.querySelectorAll(
    "[data-add-sources-to-matrix]",
  )) {
    button.disabled = count === 0;
    button.textContent = count === 1
      ? "Add selected source to this matrix"
      : `Add ${count} selected sources to this matrix`;
  }
}

function sourceContext(source) {
  const details = [
    source.schema_type === "FieldWallProfile"
      ? "Field wall"
      : "Archaeological diagram",
  ];
  if (source.trench) details.push(`Trench ${source.trench}`);
  if (Array.isArray(source.faces) && source.faces.length > 0) {
    details.push(source.faces.join(", "));
  }
  details.push(countLabel(source.unit_count, "unit"));
  return details.join(" · ");
}

function renderSources(sources) {
  sourceList.replaceChildren();
  if (sources.length === 0) {
    const empty = document.createElement("p");
    empty.className = "harris-empty";
    empty.textContent = "No usable source drawing jobs were found.";
    sourceList.append(empty);
    sourceStatus.textContent = validRequestedSourceJobId
      ? "The linked drawing is not available for matrix import."
      : "";
    sourceStatus.dataset.state = validRequestedSourceJobId ? "error" : "";
    updateMatrixImportButtons();
    return;
  }

  let matchedRequestedSource = false;
  for (const source of sources) {
    const item = document.createElement("div");
    const label = document.createElement("label");
    const title = document.createElement("strong");
    const context = document.createElement("span");

    item.className = "source-job";
    label.className = "source-job-label";
    title.textContent = `Job ${source.job_id}`;

    if (source.usable === false) {
      // Not importable; shown with the reason instead of a checkbox so the
      // operator can see why the drawing is missing from the picker.
      context.textContent = source.reason || "Not importable.";
      label.append(title, context);
      item.append(label);
      sourceList.append(item);
      continue;
    }

    const checkbox = document.createElement("input");
    checkbox.id = `dashboard-source-${source.job_id}`;
    checkbox.type = "checkbox";
    checkbox.value = source.job_id;
    checkbox.checked = source.job_id === validRequestedSourceJobId;
    checkbox.addEventListener("change", updateMatrixImportButtons);
    matchedRequestedSource ||= checkbox.checked;

    label.htmlFor = checkbox.id;
    context.textContent = sourceContext(source);
    label.append(title, context);
    item.append(checkbox, label);
    sourceList.append(item);
  }

  if (validRequestedSourceJobId) {
    sourceStatus.textContent = matchedRequestedSource
      ? "Linked drawing selected. Choose an explicit action to continue."
      : "The linked drawing is not available for matrix import.";
    sourceStatus.dataset.state = matchedRequestedSource ? "" : "error";
  } else {
    sourceStatus.textContent = "";
    sourceStatus.dataset.state = "";
  }
  updateMatrixImportButtons();
}

async function addSourcesToMatrix(matrix, button) {
  const jobIds = selectedSourceIds();
  if (jobIds.length === 0) return;

  button.disabled = true;
  setStatus("Adding selected sources…", "saving");
  try {
    await apiJson(
      `/api/harris-matrices/${encodeURIComponent(matrix.matrix_id)}/sources`,
      { job_ids: jobIds, revision: matrix.revision },
    );
    window.location.assign(
      `/harris/${encodeURIComponent(matrix.matrix_id)}`,
    );
  } catch (error) {
    setStatus(
      error.message || "Could not add the selected sources.",
      "error",
    );
    button.disabled = false;
  }
}

function renderMatrices(matrices) {
  list.replaceChildren();
  if (matrices.length === 0) {
    const empty = document.createElement("li");
    empty.className = "harris-empty";
    empty.textContent = "No Harris matrices yet. Create one to begin.";
    list.append(empty);
    return;
  }

  for (const matrix of matrices) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    const title = document.createElement("strong");
    const trench = document.createElement("span");
    const counts = document.createElement("span");
    const updated = document.createElement("time");
    const addSourcesButton = document.createElement("button");

    item.className = "matrix-list-item";
    link.href = `/harris/${encodeURIComponent(matrix.matrix_id)}`;
    title.textContent = matrix.title || "Untitled Harris Matrix";
    trench.textContent = matrix.trench
      ? `Trench ${matrix.trench}`
      : "No trench recorded";
    counts.textContent = [
      countLabel(matrix.unit_count, "unit"),
      countLabel(matrix.relation_count, "relationship"),
    ].join(" · ");
    updated.dateTime = matrix.updated_at;
    updated.textContent = `Updated ${updatedLabel(matrix.updated_at)}`;

    link.append(title, trench, counts, updated);
    addSourcesButton.type = "button";
    addSourcesButton.className = "secondary-button matrix-source-action";
    addSourcesButton.dataset.addSourcesToMatrix = matrix.matrix_id;
    addSourcesButton.disabled = true;
    addSourcesButton.textContent = "Select a source drawing to add";
    addSourcesButton.addEventListener("click", () => {
      void addSourcesToMatrix(matrix, addSourcesButton);
    });
    item.append(link, addSourcesButton);
    list.append(item);
  }
  updateMatrixImportButtons();
}

async function loadMatrices() {
  try {
    renderMatrices(await api("/api/harris-matrices"));
  } catch (_error) {
    list.replaceChildren();
    const errorItem = document.createElement("li");
    errorItem.className = "harris-empty harris-error";
    errorItem.textContent = "Could not load Harris matrices.";
    list.append(errorItem);
  }
}

async function loadSources() {
  try {
    renderSources(await api("/api/harris-source-jobs"));
  } catch (_error) {
    renderSources([]);
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  const submitButton = form.querySelector('button[type="submit"]');
  const data = new FormData(form);
  submitButton.disabled = true;
  setStatus("Creating…", "saving");

  try {
    const selectedJobIds = selectedSourceIds();
    let matrix = await apiJson("/api/harris-matrices", {
      title: data.get("title"),
      site: data.get("site"),
      trench: data.get("trench"),
    });
    if (selectedJobIds.length > 0) {
      setStatus("Importing selected sources…", "saving");
      matrix = await apiJson(
        (
          `/api/harris-matrices/`
          + `${encodeURIComponent(matrix.matrix_id)}/sources`
        ),
        { job_ids: selectedJobIds, revision: matrix.revision },
      );
    }
    window.location.assign(
      `/harris/${encodeURIComponent(matrix.matrix_id)}`,
    );
  } catch (error) {
    setStatus(error.message || "Could not create the matrix.", "error");
    submitButton.disabled = false;
  }
});

loadMatrices();
loadSources();
