/* Trenches page: group the per-wall drawings of one trench and build them
   into a single model.

   The build route deliberately refuses to guess registration: with no grid in
   the request it answers `needs_grid` and a starter config, and it refuses the
   untouched starter. This page mirrors that -- the first Build press fetches
   the starter into the textarea, and the operator fills in real survey values
   before pressing Build again. */

const list = document.querySelector("[data-trench-list]");
const POLL_INTERVAL_MS = 2000;

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
    throw error;
  }
  return payload;
}

function panel(text) {
  const item = document.createElement("div");
  const paragraph = document.createElement("p");
  item.className = "panel";
  paragraph.className = "lede";
  paragraph.textContent = text;
  item.append(paragraph);
  return item;
}

/* Notes and warnings come from the merge layer and the grid check. They are
   written for a person to read, so they are shown verbatim rather than
   summarised or filtered. */
function messageBanner(heading, messages, variant) {
  if (!Array.isArray(messages) || messages.length === 0) return null;
  const banner = document.createElement("div");
  const title = document.createElement("strong");
  const items = document.createElement("ul");
  banner.className = variant ? `banner ${variant}` : "banner";
  title.textContent = heading;
  for (const message of messages) {
    const item = document.createElement("li");
    item.textContent = String(message);
    items.append(item);
  }
  banner.append(title, items);
  return banner;
}

function wallReadiness(member) {
  return member.has_normalized
    ? "Ready to build"
    : "Not finished yet — open this drawing and finish it first";
}

function wallItem(member) {
  const item = document.createElement("li");
  const link = document.createElement("a");
  const name = document.createElement("strong");
  const detail = document.createElement("span");

  link.href = `/jobs/${encodeURIComponent(member.job_id)}`;
  name.textContent = member.wall_label || "No wall label recorded";
  detail.textContent = " — " + [
    `Drawing ${member.job_id}`,
    member.sheet_type || "unknown sheet type",
    wallReadiness(member),
  ].join(" · ");

  link.append(name, detail);
  item.dataset.wallReady = member.has_normalized ? "yes" : "no";
  item.append(link);
  return item;
}

async function pollTask(taskId, setStatus) {
  for (;;) {
    await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS));
    let payload;
    try {
      payload = await responseJson(await fetch(
        `/api/tasks/${encodeURIComponent(taskId)}`,
        { headers: { Accept: "application/json" } },
      ));
    } catch (error) {
      setStatus(
        error.message || "Lost contact with the build.",
        "error",
      );
      return;
    }
    if (payload.status === "done") {
      setStatus("The combined model is ready.", "ok");
      return;
    }
    if (payload.status === "error") {
      setStatus(payload.error || "The build failed.", "error");
      return;
    }
    setStatus(
      `Building the combined model… (${payload.elapsed_seconds || 0}s)`,
    );
  }
}

async function startBuild(label, section) {
  const textarea = section.querySelector("[data-grid-config]");
  const button = section.querySelector("[data-build]");
  const messages = section.querySelector("[data-messages]");
  const status = section.querySelector("[data-build-status]");

  const setStatus = (message, state = "") => {
    status.textContent = message;
    status.dataset.state = state;
  };

  messages.replaceChildren();
  const raw = textarea.value.trim();
  let grid = null;
  if (raw) {
    try {
      grid = JSON.parse(raw);
    } catch (error) {
      setStatus(
        `The grid configuration is not valid JSON: ${error.message}`,
        "error",
      );
      return;
    }
  }

  button.disabled = true;
  setStatus(
    grid
      ? "Starting the combined build…"
      : "Checking what this trench still needs…",
  );

  try {
    const payload = await responseJson(await fetch(
      `/api/trenches/${encodeURIComponent(label)}/build`,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(grid ? { grid } : {}),
      },
    ));

    messages.append(...[
      messageBanner("Grid warnings", payload.grid_warnings, "warn"),
      messageBanner("Notes", payload.notes),
    ].filter(Boolean));

    if (payload.needs_grid) {
      textarea.value = JSON.stringify(payload.starter, null, 2);
      setStatus(
        "This trench needs surveyed coordinates. Replace the placeholder "
        + "values below with real ones, then press Build again.",
        "warn",
      );
      return;
    }

    setStatus("Building the combined model…");
    await pollTask(payload.task_id, setStatus);
  } catch (error) {
    setStatus(error.message || "Could not build this trench.", "error");
  } finally {
    button.disabled = false;
  }
}

function renderTrench(label, members, index) {
  const section = document.createElement("section");
  const heading = document.createElement("h2");
  const walls = document.createElement("ul");
  const field = document.createElement("label");
  const fieldText = document.createElement("span");
  const textarea = document.createElement("textarea");
  const hint = document.createElement("span");
  const actions = document.createElement("div");
  const button = document.createElement("button");
  const status = document.createElement("span");
  const messages = document.createElement("div");

  section.className = "panel";
  section.dataset.trench = label;
  heading.textContent = `Trench ${label}`;

  walls.className = "wall-list";
  for (const member of members) walls.append(wallItem(member));

  textarea.id = `grid-config-${index}`;
  textarea.dataset.gridConfig = "";
  textarea.spellcheck = false;
  field.className = "field";
  field.htmlFor = textarea.id;
  fieldText.className = "label-text";
  fieldText.textContent = "Grid configuration (JSON)";
  hint.className = "hint";
  hint.textContent = "Leave this empty and press Build to get a starter "
    + "configuration you can fill in with surveyed values.";
  field.append(fieldText, textarea, hint);

  actions.className = "btn-row";
  button.type = "button";
  button.dataset.build = "";
  button.textContent = "Build the combined model";
  button.addEventListener("click", () => {
    void startBuild(label, section);
  });
  status.dataset.buildStatus = "";
  status.setAttribute("aria-live", "polite");
  actions.append(button, status);

  messages.dataset.messages = "";

  section.append(heading, walls, field, actions, messages);
  return section;
}

function renderTrenches(trenches) {
  const labels = Object.keys(trenches).sort();
  list.replaceChildren();
  if (labels.length === 0) {
    list.append(panel(
      "No trenches yet. Give two or more drawings the same trench label and "
      + "they will be grouped here.",
    ));
    return;
  }
  labels.forEach((label, index) => {
    list.append(renderTrench(label, trenches[label] || [], index));
  });
}

async function loadTrenches() {
  try {
    const payload = await responseJson(await fetch("/api/trenches", {
      headers: { Accept: "application/json" },
    }));
    renderTrenches(payload.trenches || {});
  } catch (_error) {
    list.replaceChildren();
    list.append(panel("Could not load the list of trenches."));
  }
}

loadTrenches();
