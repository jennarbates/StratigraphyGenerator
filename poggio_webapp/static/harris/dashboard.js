const form = document.querySelector("#create-matrix-form");
const list = document.querySelector("#matrix-list");
const status = document.querySelector("#dashboard-status");

function setStatus(message, state = "") {
  status.textContent = message;
  status.dataset.state = state;
}

async function responseJson(response) {
  const payload = await response.json();
  if (!response.ok) {
    const error = new Error(payload.error || "The request failed.");
    error.status = response.status;
    throw error;
  }
  return payload;
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
    item.append(link);
    list.append(item);
  }
}

async function loadMatrices() {
  try {
    const response = await fetch("/api/harris-matrices", {
      headers: { Accept: "application/json" },
    });
    renderMatrices(await responseJson(response));
  } catch (_error) {
    list.replaceChildren();
    const errorItem = document.createElement("li");
    errorItem.className = "harris-empty harris-error";
    errorItem.textContent = "Could not load Harris matrices.";
    list.append(errorItem);
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  const submitButton = form.querySelector('button[type="submit"]');
  const data = new FormData(form);
  submitButton.disabled = true;
  setStatus("Creating…", "saving");

  try {
    const response = await fetch("/api/harris-matrices", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title: data.get("title"),
        site: data.get("site"),
        trench: data.get("trench"),
      }),
    });
    const matrix = await responseJson(response);
    window.location.assign(
      `/harris/${encodeURIComponent(matrix.matrix_id)}`,
    );
  } catch (error) {
    setStatus(error.message || "Could not create the matrix.", "error");
    submitButton.disabled = false;
  }
});

loadMatrices();
