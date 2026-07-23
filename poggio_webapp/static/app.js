/* Trench Digitization Pipeline — frontend
   Vanilla JS single-page wizard. No build step, talks to the Flask API
   in app.py. State lives in `state` below; each pipeline stage has a
   render_STAGE() function that draws its panel into #content.
*/

const STRATA = ["#9c6b3e", "#b98a4f", "#8a8c53", "#6c7a80", "#a4522f", "#5b7a9c", "#8a5ba0"];

const STEPS = [
  { id: "scan",       title: "Scan",        sub: "01_scans",              num: "01" },
  { id: "preprocess", title: "Preprocess",  sub: "02_preprocess",         num: "02" },
  { id: "markers",    title: "Mark vertices", sub: "03_extraction",       num: "03" },
  { id: "features",   title: "Features",    sub: "03_extraction",         num: "03" },
  { id: "draw",       title: "Draw boundaries", sub: "03_extraction",     num: "03" },
  { id: "extract",    title: "Extraction",  sub: "03_extraction",         num: "03" },
  { id: "normalize",  title: "Normalize",   sub: "04_normalize_validate", num: "04" },
  { id: "validate",   title: "Validate",    sub: "04_normalize_validate", num: "04" },
  { id: "convert",    title: "Convert coords", sub: "05_convert_coords",  num: "05" },
  { id: "gempy",      title: "3D model",    sub: "06_gempy_model",        num: "06" },
  { id: "visualize",  title: "Visualize",   sub: "07_visualizer",         num: "07" },
];

const state = {
  jobId: null,
  sheetType: "illustrator",
  current: "scan",
  completed: {},          // {stepId: true}
  scan: { url: null, isPdf: false, filename: null, dims: null, recommendedUpscale: null },
  preprocess: { cleanUrl: null },
  // CV marker detection (field sheets). Lives in global state, not render
  // closures, so navigating between steps mid-flow doesn't discard work.
  markers: { rotate: 0, clicks: [], squareCm: null, refM: null,
             previewImageUrl: null, features: [], confirmed: [],
             boundaryResult: null, classifyById: null },
  // human-in-the-loop feature inventory (both sheet types, optional)
  features: { imageUrl: null, imageKind: null, imgW: 0, imgH: 0,
              candidates: [], confirmedCount: 0, debugUrl: null },
  // human-drawn boundary geometry (both sheet types, optional)
  draw: { rotate: 0, imageUrl: null, imageKind: null, clicks: [], refM: null,
          boundaries: [], currentIdx: -1, trenchLabel: "", faceLabel: "",
          squareCm: null, lociMeta: {}, layerMeta: {}, result: null },
  extract: { rawJson: null, warning: null },
  normalize: { data: null, log: [] },
  validate: { report: null },
  convert: { gridConfig: null, result: null },
  gempy: { result: null },
  apiKey: "",
};

const $content = document.getElementById("content");
const $steps = document.getElementById("steps");
const $jobBadge = document.getElementById("jobBadge");

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  let body;
  try { body = await res.json(); } catch (e) { body = null; }
  if (!res.ok) {
    const msg = (body && (body.error || body.description)) || res.statusText;
    throw new Error(msg);
  }
  return body;
}

async function apiJson(path, payload, method = "POST") {
  return api(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
}

async function ensureJob() {
  if (state.jobId) return state.jobId;
  const r = await api("/api/jobs", { method: "POST" });
  state.jobId = r.job_id;
  $jobBadge.textContent = `job ${state.jobId}`;
  return state.jobId;
}

async function pollTask(taskId, onLog) {
  while (true) {
    const t = await api(`/api/tasks/${taskId}`);
    if (onLog) onLog(t.log || [], t.elapsed_seconds);
    if (t.status === "done") return t;
    if (t.status === "error") {
      const err = new Error(t.error);
      err.detail = t.error_detail || null;
      throw err;
    }
    await new Promise((r) => setTimeout(r, 1200));
  }
}

// How long is too long for the extraction stage? Derived from the actual
// ceilings in the code: each attempt has a 4-minute client timeout
// (http_options in extract_*.py), up to 5 attempts with backoff, capped at
// a 10-minute total retry budget (generate_with_retry). So ~11 min is the
// true worst case; anything past that means the server thread is stuck.
const EXTRACT_TYPICAL_S = 240;   // most sheets finish well inside 4 min
const EXTRACT_HARD_S = 660;      // past the retry budget -- nothing good is coming
function extractWaitStatus(elapsed) {
  if (elapsed < EXTRACT_TYPICAL_S) {
    return `Typically finishes in 1\u20134 minutes.`;
  }
  if (elapsed < EXTRACT_HARD_S) {
    return `\u26a0 Longer than typical. If the log shows "retrying", Gemini's ` +
      `servers are having trouble \u2014 the app retries automatically (max ~11 ` +
      `min total), so leave it be; re-running now would just spend more quota.`;
  }
  return `\u26a0 ${Math.round(elapsed / 60)} min is past the worst case this app ` +
    `allows (~11 min). The server thread is likely stuck \u2014 safe to close ` +
    `this tab and restart app.py. Before re-running: wait a while (each run ` +
    `re-sends the whole image and uses quota), check ` +
    `https://status.cloud.google.com, and if this keeps happening, report ` +
    `it on the project's issue tracker with the log below.`;
}

// Renders a friendly error banner with the raw traceback tucked into a
// collapsed <details> so it's available without being the message.
function errorBanner(e) {
  let html = banner("err", e.message);
  if (e.detail) {
    const pre = document.createElement("pre");
    pre.textContent = e.detail;
    html += `<details class="err-detail"><summary>Technical detail</summary>` +
            pre.outerHTML + `</details>`;
  }
  return html;
}

// ---------------------------------------------------------------------------
// sidebar
// ---------------------------------------------------------------------------

// Which steps must be completed before a given step opens. Hoisted so the
// step-nav footer can say *why* a Next button is disabled, not just grey it out.
// validate is a hard prerequisite for convert on purpose: the fabrication
// checks live there, and they're the one step this pipeline shouldn't let
// anyone breeze past on the way to a 3D model.
const PREREQS = {
  // extract opens after scan (not preprocess) so a previous extraction JSON
  // can be uploaded without re-running the image pipeline; the Gemini path
  // inside the stage still checks for preprocess itself.
  // markers likewise only needs the scan (detection runs on the raw photo,
  // not the preprocessed image) and is optional: extract does not require
  // it, since illustrator sheets and uploaded JSONs never touch it.
  // features and draw likewise open after scan and are both optional:
  // features feeds every extraction path an authoritative inventory, and
  // draw installs a finished extraction all by itself.
  scan: [], preprocess: ["scan"], markers: ["scan"], features: ["scan"],
  draw: ["scan"], extract: ["scan"],
  normalize: ["extract"], validate: ["extract"],
  convert: ["normalize", "validate"], gempy: ["convert"], visualize: ["extract"],
};

// Everything downstream of stepId in the PREREQS graph loses its completed
// flag and cached outputs. Called whenever a stage (re-)runs: without this,
// re-uploading a scan left every later step marked complete, so the sidebar
// and Next button let you jump ahead carrying results from the previous
// image — the exact step-skipping the greyed-out states are meant to stop.
const FRESH_STATE = {
  preprocess: () => ({ cleanUrl: null }),
  markers: () => ({ rotate: 0, clicks: [], squareCm: null, refM: null,
                    previewImageUrl: null, features: [], confirmed: [],
                    boundaryResult: null, classifyById: null }),
  features: () => ({ imageUrl: null, imageKind: null, imgW: 0, imgH: 0,
                     candidates: [], confirmedCount: 0, debugUrl: null }),
  draw: () => ({ rotate: 0, imageUrl: null, imageKind: null, clicks: [],
                 refM: null, boundaries: [], currentIdx: -1, trenchLabel: "",
                 faceLabel: "", squareCm: null, lociMeta: {}, layerMeta: {},
                 result: null }),
  extract: () => ({ rawJson: null, warning: null }),
  normalize: () => ({ data: null, log: [] }),
  validate: () => ({ report: null }),
  convert: () => ({ gridConfig: null, result: null }),
  gempy: () => ({ result: null }),
};

function invalidateDownstream(stepId) {
  // PREREQS is the gating graph (what must run before a step opens). For
  // staleness there's one extra edge: the server validates the normalized
  // file when it exists, so re-running normalize makes a previous
  // validation report stale even though normalize isn't required to OPEN
  // the validate step. A second edge: extract isn't GATED on markers (the
  // illustrator/upload paths never use them) but a field-sheet extraction
  // built from confirmed markers IS stale once markers re-run.
  // extract also goes stale when the confirmed feature inventory or a
  // hand-drawn build changes, since both shape the installed extraction
  const EXTRA_STALE_EDGES = { validate: ["normalize"],
                              extract: ["markers", "features", "draw"] };
  const depsOf = (id) =>
    (PREREQS[id] || []).concat(EXTRA_STALE_EDGES[id] || []);
  const stale = new Set();
  let grew = true;
  while (grew) {
    grew = false;
    for (const id of Object.keys(PREREQS)) {
      if (stale.has(id)) continue;
      const reqs = depsOf(id);
      if (reqs.includes(stepId) || reqs.some((r) => stale.has(r))) {
        stale.add(id);
        grew = true;
      }
    }
  }
  stale.forEach((id) => {
    delete state.completed[id];
    if (FRESH_STATE[id]) state[id] = FRESH_STATE[id]();
  });
  return stale;
}

function stepIndex(id) {
  return STEPS.findIndex((s) => s.id === id);
}

function stepTitle(id) {
  const s = STEPS.find((x) => x.id === id);
  return s ? `${s.num} · ${s.title}` : id;
}

function missingPrereqs(id) {
  return (PREREQS[id] || []).filter((p) => !state.completed[p]);
}

function stepEnabled(id) {
  if (stepIndex(id) === 0) return true;
  return missingPrereqs(id).length === 0;
}

function stepHasWarnings(id) {
  if (id !== "validate") return false;
  const report = state.validate && state.validate.report;
  return !!(report && report.warnings && report.warnings.length);
}

function renderSidebar() {
  $steps.innerHTML = "";
  STEPS.forEach((s, i) => {
    const el = document.createElement("div");
    const enabled = stepEnabled(s.id);
    el.className = "step" + (s.id === state.current ? " active" : "") + (!enabled ? " disabled" : "");
    el.innerHTML = `
      <div class="step-num" style="background:${STRATA[i % STRATA.length]}">${s.num}</div>
      <div class="step-label">
        <div class="step-title">${s.title}</div>
        <div class="step-sub">${s.sub}</div>
      </div>
      ${state.completed[s.id]
          ? `<div class="step-check${stepHasWarnings(s.id) ? " warn" : ""}">&#10003;</div>`
          : ""}
    `;
    if (enabled) {
      el.addEventListener("click", () => goToStep(s.id));
    }
    $steps.appendChild(el);
  });
}

// ---------------------------------------------------------------------------
// step navigation footer
// ---------------------------------------------------------------------------

function goToStep(id) {
  state.current = id;
  render();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* Appended to the bottom of every panel by render(). Removed and rebuilt each
   time so the Next button's enabled state tracks the current step's progress
   -- stages call refreshChrome() when they complete. */
function renderStepNav() {
  const existing = document.getElementById("stepNav");
  if (existing) existing.remove();

  const idx = stepIndex(state.current);
  if (idx < 0) return;

  const prev = idx > 0 ? STEPS[idx - 1] : null;
  const next = idx < STEPS.length - 1 ? STEPS[idx + 1] : null;

  const nav = document.createElement("div");
  nav.className = "step-nav";
  nav.id = "stepNav";

  if (prev) {
    const back = document.createElement("button");
    back.className = "secondary";
    back.innerHTML = `&larr; ${stepTitle(prev.id)}`;
    back.addEventListener("click", () => goToStep(prev.id));
    nav.appendChild(back);
  }

  const spacer = document.createElement("div");
  spacer.className = "step-nav-spacer";
  nav.appendChild(spacer);

  if (!next) {
    const done = document.createElement("span");
    done.className = "step-nav-hint";
    done.textContent = "last step — nothing further to run";
    nav.appendChild(done);
    $content.appendChild(nav);
    return;
  }

  const missing = missingPrereqs(next.id);
  if (missing.length) {
    const hint = document.createElement("span");
    hint.className = "step-nav-hint";
    hint.textContent = `run ${missing.map(stepTitle).join(" and ")} first`;
    nav.appendChild(hint);
  }

  const fwd = document.createElement("button");
  fwd.innerHTML = `Next: ${stepTitle(next.id)} &rarr;`;
  fwd.disabled = missing.length > 0;
  if (!fwd.disabled) fwd.addEventListener("click", () => goToStep(next.id));
  nav.appendChild(fwd);

  $content.appendChild(nav);
}

/* Sidebar + footer both reflect completion state, so they refresh together. */
function refreshChrome() {
  renderSidebar();
  renderStepNav();
}

// ---------------------------------------------------------------------------
// small render helpers
// ---------------------------------------------------------------------------

function banner(kind, text) {
  return `<div class="banner ${kind}">${text}</div>`;
}

// HTML-escape untrusted strings interpolated into innerHTML (e.g. locus
// numbers read off the sheet). Was referenced by the boundary-review legend
// but never defined — a latent ReferenceError hidden behind the old
// assign-route bug.
function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function renderJsonTree(value, key = null, depth = 0) {
  const wrap = document.createElement("div");
  if (Array.isArray(value) || (value !== null && typeof value === "object")) {
    const isArr = Array.isArray(value);
    const entries = isArr ? value.map((v, i) => [i, v]) : Object.entries(value);
    const node = document.createElement("div");
    node.className = "jt-node";
    const toggle = document.createElement("span");
    toggle.className = "jt-toggle";
    toggle.textContent = entries.length ? "▾ " : "  ";
    const label = document.createElement("span");
    label.innerHTML = (key !== null ? `<span class="jt-key">${key}:</span> ` : "") +
      (isArr ? `[${entries.length}]` : `{${entries.length}}`);
    const head = document.createElement("div");
    head.appendChild(toggle);
    head.appendChild(label);
    node.appendChild(head);

    const children = document.createElement("div");
    children.className = "jt-children jt-indent";
    entries.forEach(([k, v]) => children.appendChild(renderJsonTree(v, isArr ? null : k, depth + 1)));
    node.appendChild(children);

    if (depth > 1) {
      node.classList.add("jt-collapsed");
      toggle.textContent = "▸ ";
    }
    toggle.addEventListener("click", () => {
      node.classList.toggle("jt-collapsed");
      toggle.textContent = node.classList.contains("jt-collapsed") ? "▸ " : "▾ ";
    });
    wrap.appendChild(node);
  } else {
    let cls = "jt-null", text = "null";
    if (typeof value === "string") { cls = "jt-str"; text = `"${value}"`; }
    else if (typeof value === "number") { cls = "jt-num"; text = String(value); }
    else if (typeof value === "boolean") { cls = "jt-bool"; text = String(value); }
    wrap.innerHTML = (key !== null ? `<span class="jt-key">${key}:</span> ` : "") +
      `<span class="${cls}">${text}</span>`;
  }
  return wrap;
}

function dataTable(rows) {
  if (!rows || !rows.length) return "<p class='lede'>No rows.</p>";
  const cols = Object.keys(rows[0]);
  let html = "<div class='table-wrap'><table class='data-table'><thead><tr>";
  cols.forEach((c) => (html += `<th>${c}</th>`));
  html += "</tr></thead><tbody>";
  rows.forEach((r) => {
    html += "<tr>" + cols.map((c) => `<td>${r[c]}</td>`).join("") + "</tr>";
  });
  html += "</tbody></table></div>";
  return html;
}

// ---------------------------------------------------------------------------
// STAGE 1 — scan upload
// ---------------------------------------------------------------------------

function renderScan() {
  $content.innerHTML = `
    <div class="panel">
      <h2>01 · Scan</h2>
      <p class="lede">Upload the raw drawing: an archival illustrator sheet (hatch-pattern
      legend) or a modern hand-drawn field sheet (Locus number + Munsell color).
      Each uses a different extraction schema downstream.</p>

      <div class="sheet-type-choice">
        <div class="sheet-card ${state.sheetType === "illustrator" ? "selected" : ""}" data-type="illustrator">
          <h3>Illustrator sheet</h3>
          <p>Drawn hatch/fill legend mapped to named materials. e.g. Trench 23, 1980.</p>
        </div>
        <div class="sheet-card ${state.sheetType === "fieldwall" ? "selected" : ""}" data-type="fieldwall">
          <h3>Field recording sheet</h3>
          <p>Hand-drawn on graph paper, Locus number + Munsell soil color. e.g. T104.</p>
        </div>
      </div>

      <div class="dropzone" id="dropzone">
        <input type="file" id="fileInput" accept=".png,.jpg,.jpeg,.pdf,.tif,.tiff">
        <div id="dzLabel">Drop a scan here, or click to choose a file<br>
        <span class="hint">PNG, JPEG, TIFF, or PDF</span></div>
      </div>

      <div id="scanError"></div>
      <div id="scanPreview"></div>
    </div>
  `;

  document.querySelectorAll(".sheet-card").forEach((c) => {
    c.addEventListener("click", () => {
      state.sheetType = c.dataset.type;
      renderScan();
    });
  });

  const dz = document.getElementById("dropzone");
  const input = document.getElementById("fileInput");
  dz.addEventListener("click", () => input.click());
  ["dragenter", "dragover"].forEach((ev) =>
    dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((ev) =>
    dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("drag"); }));
  dz.addEventListener("drop", (e) => {
    if (e.dataTransfer.files.length) handleScanFile(e.dataTransfer.files[0]);
  });
  input.addEventListener("change", () => {
    if (input.files.length) handleScanFile(input.files[0]);
  });

  if (state.scan.url) renderScanPreview();
}

function renderScanPreview() {
  const el = document.getElementById("scanPreview");
  if (!el) return;
  let html = state.scan.isPdf
    ? `<p class="lede">Uploaded ${state.scan.filename} (PDF — will be rasterized during preprocessing).</p>`
    : `<img class="preview-img" src="${state.scan.url}">`;
  if (state.scan.dims) {
    html += `<p class="hint" style="margin-top:8px">${state.scan.dims.width} × ${state.scan.dims.height} px</p>`;
  }
  if (state.scan.recommendedUpscale) {
    html += banner("ok",
      `Suggested upscale for preprocessing: <strong>${state.scan.recommendedUpscale.factor}×</strong> — ${state.scan.recommendedUpscale.reason}`);
  }
  el.innerHTML = html;
}

async function handleScanFile(file) {
  const errEl = document.getElementById("scanError");
  errEl.innerHTML = "";
  try {
    await ensureJob();
    const fd = new FormData();
    fd.append("file", file);
    fd.append("sheet_type", state.sheetType);
    const r = await api(`/api/jobs/${state.jobId}/scan`, { method: "POST", body: fd });
    state.scan.url = r.scan_url;
    state.scan.isPdf = r.is_pdf;
    state.scan.filename = file.name;
    state.scan.dims = r.dimensions;
    state.scan.recommendedUpscale = r.recommended_upscale;
    invalidateDownstream("scan");
    state.completed.scan = true;
    document.getElementById("dzLabel").textContent = `${file.name} uploaded`;
    renderScanPreview();
    refreshChrome();
  } catch (e) {
    errEl.innerHTML = errorBanner(e);
  }
}

// ---------------------------------------------------------------------------
// STAGE 2 — preprocess
// ---------------------------------------------------------------------------

function renderPreprocess() {
  const rec = state.scan.recommendedUpscale;
  const defaultUpscale = rec ? rec.factor : 2;
  $content.innerHTML = `
    <div class="panel">
      <h2>02 · Preprocess</h2>
      <p class="lede">Grayscale, background-flatten, upscale, and CLAHE-sharpen the scan so
      the vision model can resolve boundary lines. The "clean" output is what gets fed forward —
      it keeps fill hatching, unlike the optional high-contrast pass.</p>

      <div class="row">
        <label class="field">
          <span class="label-text">Upscale factor</span>
          <input type="number" id="ppUpscale" value="${defaultUpscale}" step="0.5" min="1">
          ${rec ? `<span class="hint">Suggested from upload resolution (${state.scan.dims.width}×${state.scan.dims.height}px): ${rec.reason}</span>` : ""}
        </label>
        ${state.scan.isPdf ? `
        <label class="field">
          <span class="label-text">PDF DPI</span>
          <input type="number" id="ppDpi" value="300" step="10">
        </label>
        <label class="field">
          <span class="label-text">PDF page</span>
          <input type="number" id="ppPage" value="1" step="1" min="1">
        </label>` : ""}
      </div>
      <div class="checkbox-row"><input type="checkbox" id="ppDeskew"><label for="ppDeskew">Deskew (straighten slight scan rotation)</label></div>
      <div class="checkbox-row"><input type="checkbox" id="ppHighcontrast"><label for="ppHighcontrast">Also generate high-contrast pass (boundary tracing only)</label></div>

      <div class="btn-row">
        <button id="ppRun">Run preprocessing</button>
      </div>
      <div id="ppError"></div>
      <div id="ppResult"></div>
    </div>
  `;

  document.getElementById("ppRun").addEventListener("click", async () => {
    const btn = document.getElementById("ppRun");
    const errEl = document.getElementById("ppError");
    errEl.innerHTML = "";
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>Processing...`;
    try {
      const body = {
        upscale: parseFloat(document.getElementById("ppUpscale").value),
        deskew: document.getElementById("ppDeskew").checked,
        highcontrast: document.getElementById("ppHighcontrast").checked,
      };
      if (state.scan.isPdf) {
        body.pdf_dpi = parseInt(document.getElementById("ppDpi").value, 10);
        body.pdf_page = parseInt(document.getElementById("ppPage").value, 10);
      }
      const r = await apiJson(`/api/jobs/${state.jobId}/preprocess`, body);
      state.preprocess.cleanUrl = r.outputs.clean;
      invalidateDownstream("preprocess");
      state.completed.preprocess = true;
      const resEl = document.getElementById("ppResult");
      resEl.innerHTML = `
        ${banner("ok", `Deskew angle applied: ${r.deskew_angle.toFixed(2)}°`)}
        <div class="section-imgs">
          <figure><img src="${r.outputs.clean}"><figcaption>clean (feed forward)</figcaption></figure>
          ${r.outputs.highcontrast ? `<figure><img src="${r.outputs.highcontrast}"><figcaption>high-contrast (boundary only)</figcaption></figure>` : ""}
        </div>
      `;
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Run preprocessing";
    }
  });
}

// ---------------------------------------------------------------------------
// STAGE 3 — extraction
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// STAGE 3a — mark vertices (CV marker detection, field sheets only)
// ---------------------------------------------------------------------------
// The no-network half of the CV path: rotate the photo, click three
// reference points, detect the recorder's circle-marked vertices, review
// and confirm them. The Gemini half (classify + finalize) lives in the
// Extraction step. All state persists in state.markers so leaving and
// returning to this step keeps your work.

function renderMarkers() {
  const isField = state.sheetType === "fieldwall";
  const mk = state.markers;

  if (!isField) {
    $content.innerHTML = `
      <div class="panel">
        <h2>03 · Mark vertices</h2>
        <p class="lede">This step only applies to <strong>field recording
        sheets</strong>, where the recorder marks each measured vertex with a
        small circle that computer vision can find. Illustrator sheets have no
        such markers — continue straight to <strong>03 · Extraction</strong>.</p>
      </div>`;
    return;
  }

  $content.innerHTML = `
    <div class="panel">
      <h2>03 · Mark vertices</h2>
      <p class="lede">Finds the recorder's circle-marked vertices with computer
      vision — which can't invent a dot that isn't on the paper. No network
      call, no API key. The confirmed points feed the Extraction step, where
      Gemini only <em>labels</em> them.</p>

      <label class="field">
        <span class="label-text">Photo rotation</span>
        <select id="mkRotate">
          <option value="0">0° (already upright)</option>
          <option value="90">90° clockwise</option>
          <option value="180">180°</option>
          <option value="270">270° clockwise</option>
        </select>
        <span class="hint">If the photo was shot sideways, pick the rotation that makes it upright.</span>
      </label>
      <label class="field">
        <span class="label-text">Bold grid square size (cm)</span>
        <input type="number" id="mkSquareCm" placeholder="e.g. 20" step="0.5" min="0.1"
               value="${mk.squareCm ?? ""}">
        <span class="hint">Human-confirmed, not re-derived from the image — measure the sheet's bold squares by hand.</span>
      </label>
      <div class="btn-row">
        <button class="secondary" id="mkShow">1 · Show photo &amp; click reference points</button>
      </div>
      <div id="mkPickWrap" style="display:none">
        <p class="hint" id="mkPickHint"></p>
        <div style="position:relative;display:inline-block;max-width:100%">
          <img id="mkImg" style="max-width:100%;display:block;cursor:crosshair">
          <div id="mkDots" style="position:absolute;inset:0;pointer-events:none"></div>
        </div>
      </div>
      <label class="field">
        <span class="label-text">Real width between the two top corners (m)</span>
        <input type="number" id="mkRefM" step="0.5" min="0.1"
               placeholder="e.g. 4 (194 m → 190 m)" value="${mk.refM ?? ""}">
        <span class="hint">Read it off the sheet's own tie labels along the top edge.</span>
      </label>
      <div class="btn-row">
        <button class="secondary" id="mkDetect" disabled>2 · Detect markers</button>
      </div>
      <div id="mkResult"></div>

      <div id="mkReviewWrap" style="display:none">
        <h3 style="margin-top:22px">Review detected markers</h3>
        <p class="hint">Click a dot to accept/reject it — green = CV-accepted,
        red = CV-rejected, blue = manually added. Turn on "add feature" and
        click empty space to mark a vertex CV missed. (These dots are
        boundary <em>markers</em> — stones, cuts, and lenses belong in
        <strong>03 · Features</strong> instead.)</p>
        <div class="btn-row">
          <button class="secondary" id="mkAddMode">+ Add marker</button>
          <label class="hint" style="display:inline-flex;align-items:center;gap:6px;margin-left:12px">
            <input type="checkbox" id="mkShowRejected" checked>
            show rejected candidates (red)
          </label>
          <span id="mkAddModeStatus" class="hint"></span>
        </div>
        <div style="position:relative;display:inline-block;max-width:100%;margin-top:8px">
          <img id="mkReviewImg" style="max-width:100%;display:block">
          <div id="mkReviewDots" style="position:absolute;inset:0"></div>
        </div>
        <p class="hint" id="mkReviewCount"></p>
        <div class="btn-row">
          <button id="mkConfirm">3 · Confirm markers</button>
        </div>
      </div>

      <div id="mkConfirmed"></div>
      <div id="mkError"></div>
    </div>
  `;

  // clicks[0]=top-left (origin), [1]=top-right, [2]=lowest point of the wall
  const CLICK_LABELS = [
    "Click the wall's TOP-LEFT corner (x=0, depth=0).",
    "Now click the wall's TOP-RIGHT corner.",
    "Now click the LOWEST point of the drawn wall.",
    "All 3 points set — adjust by clicking again from the start, or continue below.",
  ];
  const COLORS = ["#c0269a", "#d17a1f", "#2a7ab5"];
  let addMode = false;

  const hintEl = () => document.getElementById("mkPickHint");
  const errEl = () => document.getElementById("mkError");

  document.getElementById("mkRotate").value = String(mk.rotate);
  document.getElementById("mkSquareCm").addEventListener("change", (ev) => {
    mk.squareCm = parseFloat(ev.target.value) || null;
  });
  document.getElementById("mkRefM").addEventListener("change", (ev) => {
    mk.refM = parseFloat(ev.target.value) || null;
  });

  function showConfirmedBanner() {
    document.getElementById("mkConfirmed").innerHTML = mk.confirmed.length
      ? banner("ok", `<strong>${mk.confirmed.length}</strong> markers confirmed — ` +
                     `continue to <strong>03 · Extraction</strong> to classify and ` +
                     `build the extraction.`)
      : "";
  }

  function drawDots() {
    const img = document.getElementById("mkImg");
    const dots = document.getElementById("mkDots");
    dots.innerHTML = "";
    const sx = img.clientWidth / img.naturalWidth;
    const sy = img.clientHeight / img.naturalHeight;
    mk.clicks.forEach((c, i) => {
      const d = document.createElement("div");
      d.style.cssText = `position:absolute;width:14px;height:14px;border-radius:50%;
        border:3px solid ${COLORS[i]};background:rgba(255,255,255,.5);
        transform:translate(-50%,-50%);left:${c[0]*sx}px;top:${c[1]*sy}px`;
      dots.appendChild(d);
    });
    hintEl().textContent = CLICK_LABELS[mk.clicks.length];
    document.getElementById("mkDetect").disabled = mk.clicks.length < 3;
  }

  function showPickWrap() {
    const img = document.getElementById("mkImg");
    img.src = mk.previewImageUrl + "&t=" + Date.now();  // bust cache on rotation change
    document.getElementById("mkPickWrap").style.display = "block";
    img.onload = drawDots;
    window.addEventListener("resize", drawDots);
  }

  document.getElementById("mkShow").addEventListener("click", async () => {
    errEl().innerHTML = "";
    try {
      mk.rotate = parseInt(document.getElementById("mkRotate").value, 10);
      const r = await apiJson(`/api/jobs/${state.jobId}/markers/preview`, { rotate: mk.rotate });
      mk.previewImageUrl = r.image_url;
      mk.clicks = [];
      showPickWrap();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  document.getElementById("mkImg")?.addEventListener("click", (ev) => {
    const img = ev.target;
    const rect = img.getBoundingClientRect();
    const px = (ev.clientX - rect.left) * img.naturalWidth / rect.width;
    const py = (ev.clientY - rect.top) * img.naturalHeight / rect.height;
    if (mk.clicks.length >= 3) mk.clicks = [];
    mk.clicks.push([Math.round(px), Math.round(py)]);
    drawDots();
  });

  document.getElementById("mkDetect").addEventListener("click", async () => {
    errEl().innerHTML = "";
    const resEl = document.getElementById("mkResult");
    const sc = parseFloat(document.getElementById("mkSquareCm").value);
    const refM = parseFloat(document.getElementById("mkRefM").value);
    if (!sc) { errEl().innerHTML = banner("err", "Bold grid square size (cm) is required — see the field above."); return; }
    if (!refM) { errEl().innerHTML = banner("err", "Real width between the top corners is required."); return; }
    mk.squareCm = sc; mk.refM = refM;
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/markers/detect`, {
        square_cm: sc, ref_meters: refM,
        origin_px: mk.clicks[0], ref_px: mk.clicks[1], bottom_px_y: mk.clicks[2][1],
        rotate: parseInt(document.getElementById("mkRotate").value, 10),
      });
      resEl.innerHTML =
        banner("ok", `Found <strong>${r.n_accepted}</strong> candidate features inside the wall ` +
          `(${r.n_rejected_in_box} rejected by size/shape filters, of which the ` +
          `${r.rejected.length} nearest misses are shown in red; scale ${r.px_per_m} px/m). ` +
          `Review them below — CV's filters aren't always right, and it can't ` +
          `mark a vertex that never got a filled-in dot.`) +
        `<div class="btn-row"><a class="secondary" style="text-decoration:none" ` +
        `href="${r.debug_image_url}" target="_blank"><button class="secondary">` +
        `Open raw debug image</button></a>` +
        `<a href="${r.csv_url}" download><button class="secondary">Download markers.csv</button></a></div>`;

      mk.features = [
        ...r.markers.map(m => ({ ...m, accepted: true, manual: false })),
        ...r.rejected.map(m => ({ ...m, accepted: false, manual: false })),
      ];
      // a fresh detection makes any previously confirmed set (and anything
      // built from it) stale — the server has already overwritten markers_path
      mk.confirmed = []; mk.boundaryResult = null; mk.classifyById = null;
      delete state.completed.markers;
      invalidateDownstream("markers");
      addMode = false;
      document.getElementById("mkAddMode").textContent = "+ Add marker";
      document.getElementById("mkAddModeStatus").textContent = "";
      showConfirmedBanner();
      showReviewWrap();
      refreshChrome();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  function showReviewWrap() {
    document.getElementById("mkReviewWrap").style.display = "block";
    const img = document.getElementById("mkReviewImg");
    img.src = mk.previewImageUrl + "&t=" + Date.now();
    img.onload = drawReviewDots;
    window.addEventListener("resize", drawReviewDots);
  }

  function drawReviewDots() {
    const img = document.getElementById("mkReviewImg");
    const dots = document.getElementById("mkReviewDots");
    dots.innerHTML = "";
    const sx = img.clientWidth / img.naturalWidth;
    const sy = img.clientHeight / img.naturalHeight;
    const showRejected = document.getElementById("mkShowRejected").checked;
    mk.features.forEach((f) => {
      if (!showRejected && !f.accepted && !f.manual) return;
      const d = document.createElement("div");
      // clamp in SCREEN pixels: small enough to never cover the drawing,
      // big enough to stay clickable regardless of image scale
      const r = Math.min(Math.max(((f.diam_px || 20) / 2) * Math.max(sx, sy), 6), 24);
      const color = f.manual ? "#2a7ab5" : (f.accepted ? "#3f9142" : "#c0392b");
      d.style.cssText = `position:absolute;width:${r*2}px;height:${r*2}px;border-radius:50%;
        transform:translate(-50%,-50%);left:${f.pixel_x*sx}px;top:${f.pixel_y*sy}px;
        border:3px solid ${color};background:rgba(255,255,255,.15);
        cursor:pointer;box-sizing:border-box;`;
      d.title = f.manual ? "manually added — click to remove"
                          : `circularity ${f.circularity} — click to ${f.accepted ? "reject" : "accept"}`;
      d.addEventListener("click", (ev) => {
        ev.stopPropagation();
        if (f.manual) { mk.features = mk.features.filter(x => x !== f); }
        else { f.accepted = !f.accepted; }
        drawReviewDots();
      });
      dots.appendChild(d);
    });
    const nAccepted = mk.features.filter(f => f.accepted).length;
    document.getElementById("mkReviewCount").textContent =
      `${nAccepted} of ${mk.features.length} markers accepted.`;
  }

  document.getElementById("mkShowRejected").addEventListener("change", drawReviewDots);

  document.getElementById("mkAddMode").addEventListener("click", () => {
    addMode = !addMode;
    document.getElementById("mkAddMode").textContent =
      addMode ? "+ Add marker (click the image; click here to stop)" : "+ Add marker";
    document.getElementById("mkAddModeStatus").textContent =
      addMode ? "Click anywhere on the image to place a marker." : "";
  });

  document.getElementById("mkReviewDots").addEventListener("click", (ev) => {
    if (!addMode) return;
    const img = document.getElementById("mkReviewImg");
    const rect = img.getBoundingClientRect();
    const px = (ev.clientX - rect.left) * img.naturalWidth / rect.width;
    const py = (ev.clientY - rect.top) * img.naturalHeight / rect.height;
    mk.features.push({ pixel_x: Math.round(px), pixel_y: Math.round(py),
                       diam_px: 20, circularity: 1, accepted: true, manual: true });
    drawReviewDots();
  });

  document.getElementById("mkConfirm").addEventListener("click", async () => {
    errEl().innerHTML = "";
    const accepted = mk.features.filter(f => f.accepted);
    if (!accepted.length) {
      errEl().innerHTML = banner("err", "Accept at least one marker before confirming.");
      return;
    }
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/markers/confirm`, { markers: accepted });
      mk.confirmed = r.markers;
      mk.boundaryResult = null;
      mk.classifyById = null;
      invalidateDownstream("markers");
      state.completed.markers = true;
      showConfirmedBanner();
      refreshChrome();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  // --- restore whatever was in progress when the user last left this step ---
  if (mk.previewImageUrl) showPickWrap();
  if (mk.previewImageUrl && mk.features.length) showReviewWrap();
  showConfirmedBanner();
}

// ---------------------------------------------------------------------------
// 03 · Features — the person selects, labels, and draws the feature
// inventory (stones, cuts, lenses). CV only proposes candidates and claims
// nothing; nothing here is a feature until a person says so.
// ---------------------------------------------------------------------------

const FEATURE_TYPES = ["rock/stone", "cut", "lens", "void", "other feature"];

function renderFeatures() {
  const ft = state.features;
  $content.innerHTML = `
    <div class="panel">
      <h2>03 · Features <span class="hint">(optional)</span></h2>
      <p class="lede">Features are the objects <em>inside</em> layers (stones,
      cuts, lenses, voids), as opposed to markers, which are boundary vertices.
      Here CV proposes closed-contour candidates and <strong>you</strong> decide:
      accept, reject, re-label, or draw boxes it missed. The confirmed inventory
      is authoritative for every extraction path: Gemini tracing must reproduce
      it exactly, and the no-network paths attach it verbatim. No API key needed
      on this step.</p>
      <div class="btn-row">
        <button class="secondary" id="ftDetect">1 · Detect feature candidates</button>
      </div>
      <div id="ftInfo"></div>
      <div id="ftReviewWrap" style="display:none">
        <p class="hint">Click a box to accept/reject it. Amber dashed =
        CV proposal (not yet a feature), green = accepted, blue = drawn by you.
        Label every accepted feature in the list below.</p>
        <div class="btn-row">
          <button class="secondary" id="ftDrawMode">+ Draw a feature box</button>
          <span id="ftDrawStatus" class="hint"></span>
        </div>
        <div id="ftImgWrap" style="position:relative;display:inline-block;max-width:100%;margin-top:8px">
          <img id="ftImg" style="max-width:100%;display:block">
          <div id="ftBoxes" style="position:absolute;inset:0"></div>
        </div>
        <p class="hint" id="ftCount"></p>
        <div id="ftList"></div>
        <div class="btn-row">
          <button id="ftConfirm">2 · Confirm feature inventory</button>
        </div>
      </div>
      <div id="ftConfirmed"></div>
      <div id="ftError"></div>
    </div>
  `;

  const errEl = () => document.getElementById("ftError");
  let drawMode = false, dragStart = null, dragBox = null;

  function accepted() { return ft.candidates.filter(c => c.accepted); }

  function showConfirmedBanner() {
    document.getElementById("ftConfirmed").innerHTML = ft.confirmedCount
      ? banner("ok", `<strong>${ft.confirmedCount}</strong> features confirmed — ` +
               `they will be included in whichever extraction path you use ` +
               `(<strong>03 · Extraction</strong> or <strong>03 · Draw boundaries</strong>).`)
      : "";
  }

  function scale() {
    const img = document.getElementById("ftImg");
    return [img.clientWidth / img.naturalWidth, img.clientHeight / img.naturalHeight];
  }

  function drawBoxes() {
    const boxes = document.getElementById("ftBoxes");
    boxes.innerHTML = "";
    const [sx, sy] = scale();
    ft.candidates.forEach((c) => {
      const d = document.createElement("div");
      const color = c.manual ? "#2a7ab5" : (c.accepted ? "#3f9142" : "#c98a1b");
      d.style.cssText = `position:absolute;left:${c.x*sx}px;top:${c.y*sy}px;` +
        `width:${c.width*sx}px;height:${c.height*sy}px;box-sizing:border-box;` +
        `border:3px ${c.accepted || c.manual ? "solid" : "dashed"} ${color};` +
        `cursor:pointer;`;
      d.title = c.manual ? `${c.feature_type} (drawn by you) — click to remove`
                         : `score ${c.score ?? "-"} — click to ${c.accepted ? "reject" : "accept"}`;
      d.addEventListener("click", (ev) => {
        ev.stopPropagation();
        if (drawMode) return;
        if (c.manual) { ft.candidates = ft.candidates.filter(x => x !== c); }
        else { c.accepted = !c.accepted; }
        drawBoxes(); renderList();
      });
      boxes.appendChild(d);
    });
    document.getElementById("ftCount").textContent =
      `${accepted().length} of ${ft.candidates.length} candidates accepted as features.`;
  }

  function renderList() {
    const list = document.getElementById("ftList");
    const rows = accepted();
    if (!rows.length) { list.innerHTML = ""; return; }
    list.innerHTML = `<h3 style="margin-top:16px">Accepted features</h3>` +
      rows.map((c, i) => `
        <div class="btn-row" style="align-items:center;gap:8px" data-fi="${i}">
          <span class="hint" style="min-width:34px">F${i + 1}</span>
          <select data-role="type">${FEATURE_TYPES.map(t =>
            `<option ${t === c.feature_type ? "selected" : ""}>${t}</option>`).join("")}
          </select>
          <input data-role="desc" placeholder="description (optional)"
                 value="${esc(c.description || "")}" style="flex:1;min-width:180px">
          <span class="hint">${c.manual ? "drawn by you" : "CV proposal"}</span>
        </div>`).join("");
    list.querySelectorAll("[data-fi]").forEach((row) => {
      const c = rows[parseInt(row.dataset.fi, 10)];
      row.querySelector('[data-role="type"]').addEventListener("change",
        (ev) => { c.feature_type = ev.target.value; });
      row.querySelector('[data-role="desc"]').addEventListener("change",
        (ev) => { c.description = ev.target.value; });
    });
  }

  function showReview() {
    document.getElementById("ftReviewWrap").style.display = "block";
    const img = document.getElementById("ftImg");
    img.src = ft.imageUrl + "&t=" + Date.now();
    img.onload = () => { drawBoxes(); renderList(); };
    window.addEventListener("resize", drawBoxes);
  }

  document.getElementById("ftDetect").addEventListener("click", async () => {
    errEl().innerHTML = "";
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/features/detect`, {});
      ft.imageUrl = r.image_url; ft.imageKind = r.image_kind;
      ft.imgW = r.image_width; ft.imgH = r.image_height;
      ft.debugUrl = r.debug_image_url;
      ft.candidates = r.features.map(f => ({ ...f, accepted: false, manual: false,
                                             description: "" }));
      ft.confirmedCount = 0;
      delete state.completed.features;
      invalidateDownstream("features");
      document.getElementById("ftInfo").innerHTML =
        banner("ok", `CV proposed <strong>${r.candidate_count}</strong> closed-contour ` +
          `candidates on the <strong>${r.image_kind}</strong> image. None of them is a ` +
          `feature until you accept it — and you can reject all of them and only ` +
          `draw your own.`) +
        `<div class="btn-row"><a href="${r.debug_image_url}" target="_blank">` +
        `<button class="secondary">Open numbered debug image</button></a></div>`;
      showConfirmedBanner();
      showReview();
      refreshChrome();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  document.getElementById("ftDrawMode").addEventListener("click", () => {
    drawMode = !drawMode;
    document.getElementById("ftDrawMode").textContent =
      drawMode ? "+ Draw a feature box (drag on the image; click here to stop)"
               : "+ Draw a feature box";
    document.getElementById("ftDrawStatus").textContent =
      drawMode ? "Press, drag, and release to outline a feature." : "";
  });

  const boxesEl = () => document.getElementById("ftBoxes");
  function evToNatural(ev) {
    const img = document.getElementById("ftImg");
    const rect = img.getBoundingClientRect();
    return [(ev.clientX - rect.left) * img.naturalWidth / rect.width,
            (ev.clientY - rect.top) * img.naturalHeight / rect.height];
  }
  document.getElementById("ftImgWrap").addEventListener("mousedown", (ev) => {
    if (!drawMode) return;
    ev.preventDefault();
    dragStart = evToNatural(ev);
    dragBox = document.createElement("div");
    dragBox.style.cssText = "position:absolute;border:2px dashed #2a7ab5;pointer-events:none";
    boxesEl().appendChild(dragBox);
  });
  document.getElementById("ftImgWrap").addEventListener("mousemove", (ev) => {
    if (!drawMode || !dragStart) return;
    const [nx, ny] = evToNatural(ev);
    const [sx, sy] = scale();
    const x = Math.min(dragStart[0], nx), y = Math.min(dragStart[1], ny);
    const w = Math.abs(nx - dragStart[0]), h = Math.abs(ny - dragStart[1]);
    dragBox.style.left = (x * sx) + "px"; dragBox.style.top = (y * sy) + "px";
    dragBox.style.width = (w * sx) + "px"; dragBox.style.height = (h * sy) + "px";
  });
  document.getElementById("ftImgWrap").addEventListener("mouseup", (ev) => {
    if (!drawMode || !dragStart) return;
    const [nx, ny] = evToNatural(ev);
    const x = Math.min(dragStart[0], nx), y = Math.min(dragStart[1], ny);
    const w = Math.abs(nx - dragStart[0]), h = Math.abs(ny - dragStart[1]);
    dragStart = null;
    if (dragBox) { dragBox.remove(); dragBox = null; }
    if (w < 6 || h < 6) return;  // a click, not a drag
    ft.candidates.push({ x: Math.round(x), y: Math.round(y),
                         width: Math.round(w), height: Math.round(h),
                         feature_type: "rock/stone", description: "",
                         accepted: true, manual: true });
    drawBoxes(); renderList();
  });

  document.getElementById("ftConfirm").addEventListener("click", async () => {
    errEl().innerHTML = "";
    const rows = accepted();
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/features/confirm`, {
        features: rows.map(c => ({
          x: c.x, y: c.y, width: c.width, height: c.height,
          feature_type: c.feature_type, description: c.description,
          points: c.points || null, manual: c.manual,
        })),
      });
      ft.confirmedCount = r.n_confirmed;
      invalidateDownstream("features");
      state.completed.features = true;
      showConfirmedBanner();
      refreshChrome();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  if (ft.imageUrl && ft.candidates.length) showReview();
  showConfirmedBanner();
}

// ---------------------------------------------------------------------------
// 03 · Draw boundaries — the person draws the geometry directly on a
// calibrated image. Deterministic assembly, no model, no API key: the
// strongest anti-fabrication path in the pipeline.
// ---------------------------------------------------------------------------

function renderDraw() {
  const dw = state.draw;
  const isField = state.sheetType === "fieldwall";
  const nameLabel = isField ? "locus number" : "layer name";
  const isPdf = state.scan.isPdf;

  $content.innerHTML = `
    <div class="panel">
      <h2>03 · Draw boundaries <span class="hint">(optional)</span></h2>
      <p class="lede">Draw the boundary geometry yourself: click the drawn lines
      on a calibrated image, and the extraction is assembled deterministically —
      no model touches the geometry, no network call, no API key. Use this when
      a sheet is beyond what CV or Gemini reads reliably, or when you simply
      want full control. Building here installs the extraction directly; the
      Extraction step is then optional.</p>

      ${isPdf ? `
      <p class="hint">This scan is a PDF, so drawing happens on the
      <strong>preprocessed</strong> image${state.preprocess.cleanUrl ? "" :
      " — run <strong>02 · Preprocess</strong> first"}.</p>
      <div class="btn-row"><button class="secondary" id="dwShow"
        ${state.preprocess.cleanUrl ? "" : "disabled"}>1 · Show image</button></div>
      ` : `
      <label class="field">
        <span class="label-text">Image rotation</span>
        <select id="dwRotate">
          <option value="0">0° (already upright)</option>
          <option value="90">90° clockwise</option>
          <option value="180">180°</option>
          <option value="270">270° clockwise</option>
        </select>
      </label>
      <div class="btn-row"><button class="secondary" id="dwShow">1 · Show image</button></div>
      `}

      <div id="dwWrap" style="display:none">
        <p class="hint" id="dwHint"></p>
        <div class="btn-row">
          <button class="secondary" id="dwRecal">Recalibrate (clear the 3 reference clicks)</button>
        </div>
        <label class="field">
          <span class="label-text">Real width between the two top corners (m)</span>
          <input type="number" id="dwRefM" step="0.5" min="0.1"
                 placeholder="e.g. 4 (194 m → 190 m)" value="${dw.refM ?? ""}">
          <span class="hint">Read it off the sheet's own tie labels or scale bar.</span>
        </label>
        <div id="dwTools" style="display:none">
          <h3 style="margin-top:18px">Boundaries</h3>
          <p class="hint">Select a boundary, then click along its drawn line —
          each click adds a vertex. The surface line is the wall's top edge;
          every other boundary is the <em>bottom</em> of one ${isField ? "locus" : "layer"}.</p>
          <div class="btn-row">
            <button class="secondary" id="dwNewSurface">+ Surface line</button>
            <input id="dwName" placeholder="${nameLabel}" style="width:140px">
            <button class="secondary" id="dwNewBottom">+ Bottom boundary</button>
            <button class="secondary" id="dwUndo">Undo last point</button>
            <button class="secondary" id="dwDelete">Delete selected boundary</button>
          </div>
          <div id="dwChips" class="btn-row" style="flex-wrap:wrap"></div>
        </div>
        <div id="dwImgWrap" style="position:relative;display:inline-block;max-width:100%;margin-top:8px">
          <img id="dwImg" style="max-width:100%;display:block;cursor:crosshair">
          <svg id="dwSvg" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none"></svg>
        </div>
      </div>

      <div id="dwMetaWrap" style="display:none">
        <h3 style="margin-top:18px">Sheet details</h3>
        <div class="btn-row">
          <input id="dwTrench" placeholder="trench label (e.g. T104)" value="${esc(dw.trenchLabel)}">
          <input id="dwFace" placeholder="face label (e.g. south baulk)" value="${esc(dw.faceLabel)}">
          ${isField ? `<input type="number" id="dwSquareCm" step="0.5" min="0.1"
            placeholder="grid square (cm)" value="${dw.squareCm ?? ""}" style="width:150px">` : ""}
        </div>
        <div id="dwMeta"></div>
        <div class="btn-row">
          <button id="dwBuild">2 · Build extraction from drawn boundaries</button>
        </div>
      </div>

      <div id="dwResult"></div>
      <div id="dwError"></div>
    </div>
  `;

  const CAL_LABELS = [
    "Click the drawing's TOP-LEFT corner (x=0, depth=0).",
    "Now click the TOP-RIGHT corner.",
    "Now click the LOWEST point of the drawing.",
    "Calibrated. Select or create a boundary below, then click along its line.",
  ];
  const CAL_COLORS = ["#c0269a", "#d17a1f", "#2a7ab5"];
  const errEl = () => document.getElementById("dwError");
  const calibReady = () => dw.clicks.length >= 3 && dw.refM;

  function bottoms() { return dw.boundaries.filter(b => b.kind === "bottom"); }

  function redraw() {
    const img = document.getElementById("dwImg");
    const svg = document.getElementById("dwSvg");
    if (!img || !img.naturalWidth) return;
    svg.setAttribute("viewBox", `0 0 ${img.naturalWidth} ${img.naturalHeight}`);
    svg.setAttribute("preserveAspectRatio", "none");
    const r = Math.max(4, img.naturalWidth / 220);
    let out = "";
    dw.clicks.forEach((c, i) => {
      out += `<circle cx="${c[0]}" cy="${c[1]}" r="${r}" fill="rgba(255,255,255,.5)"
                stroke="${CAL_COLORS[i]}" stroke-width="${r * 0.6}"/>`;
    });
    dw.boundaries.forEach((b, i) => {
      const color = b.kind === "surface" ? "#2a7ab5" : STRATA[i % STRATA.length];
      const sel = i === dw.currentIdx;
      if (b.points.length > 1) {
        out += `<polyline points="${b.points.map(p => p.join(",")).join(" ")}"
                  fill="none" stroke="${color}" stroke-width="${r * (sel ? 0.9 : 0.5)}"
                  ${sel ? "" : `stroke-opacity="0.65"`}/>`;
      }
      b.points.forEach(p => {
        out += `<circle cx="${p[0]}" cy="${p[1]}" r="${r * (sel ? 0.9 : 0.6)}"
                  fill="${color}"/>`;
      });
    });
    svg.innerHTML = out;
    const hint = document.getElementById("dwHint");
    if (hint) hint.textContent = CAL_LABELS[Math.min(dw.clicks.length, 3)];
    drawChips();
    renderMeta();
  }

  function drawChips() {
    const chips = document.getElementById("dwChips");
    if (!chips) return;
    document.getElementById("dwTools").style.display = calibReady() ? "block" : "none";
    document.getElementById("dwMetaWrap").style.display =
      (calibReady() && bottoms().length) ? "block" : "none";
    chips.innerHTML = "";
    dw.boundaries.forEach((b, i) => {
      const el = document.createElement("button");
      el.className = "secondary";
      el.style.cssText = i === dw.currentIdx ? "outline:3px solid #2a7ab5" : "";
      el.textContent = (b.kind === "surface" ? "surface" :
        `${isField ? "locus" : "layer"} ${b.name}`) + ` (${b.points.length} pts)`;
      el.addEventListener("click", () => { dw.currentIdx = i; redraw(); });
      chips.appendChild(el);
    });
  }

  function renderMeta() {
    const holder = document.getElementById("dwMeta");
    if (!holder) return;
    const store = isField ? dw.lociMeta : dw.layerMeta;
    holder.innerHTML = bottoms().map(b => `
      <div class="btn-row" style="align-items:center;gap:8px" data-name="${esc(b.name)}">
        <span class="hint" style="min-width:90px">${isField ? "locus" : "layer"} ${esc(b.name)}</span>
        <input data-role="a" placeholder="${isField ? "Munsell (e.g. 10YR 5/3)" : "material (e.g. clay fill)"}"
               value="${esc((store[b.name] || {}).a || "")}">
        <input data-role="b" placeholder="description (optional)" style="flex:1;min-width:160px"
               value="${esc((store[b.name] || {}).b || "")}">
      </div>`).join("");
    holder.querySelectorAll("[data-name]").forEach(row => {
      const name = row.dataset.name;
      ["a", "b"].forEach(k => {
        row.querySelector(`[data-role="${k}"]`).addEventListener("change", (ev) => {
          store[name] = store[name] || {};
          store[name][k] = ev.target.value;
        });
      });
    });
  }

  function showImage() {
    document.getElementById("dwWrap").style.display = "block";
    const img = document.getElementById("dwImg");
    img.src = dw.imageUrl + (dw.imageUrl.includes("?") ? "&" : "?") + "t=" + Date.now();
    img.onload = redraw;
    window.addEventListener("resize", redraw);
  }

  document.getElementById("dwShow")?.addEventListener("click", async () => {
    errEl().innerHTML = "";
    try {
      if (isPdf) {
        dw.imageUrl = state.preprocess.cleanUrl;
        dw.imageKind = "clean";
      } else {
        dw.rotate = parseInt(document.getElementById("dwRotate").value, 10);
        const r = await apiJson(`/api/jobs/${state.jobId}/markers/preview`,
                                { rotate: dw.rotate });
        dw.imageUrl = r.image_url;
        dw.imageKind = "rotated";
      }
      dw.clicks = []; dw.boundaries = []; dw.currentIdx = -1;
      showImage();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  document.getElementById("dwRefM").addEventListener("change", (ev) => {
    dw.refM = parseFloat(ev.target.value) || null;
    redraw();
  });
  document.getElementById("dwRecal").addEventListener("click", () => {
    dw.clicks = []; redraw();
  });

  document.getElementById("dwImgWrap")?.addEventListener("click", (ev) => {
    const img = document.getElementById("dwImg");
    if (!img || ev.target !== img) return;
    const rect = img.getBoundingClientRect();
    const px = Math.round((ev.clientX - rect.left) * img.naturalWidth / rect.width);
    const py = Math.round((ev.clientY - rect.top) * img.naturalHeight / rect.height);
    if (dw.clicks.length < 3) {
      dw.clicks.push([px, py]);
    } else if (calibReady() && dw.currentIdx >= 0) {
      dw.boundaries[dw.currentIdx].points.push([px, py]);
    }
    redraw();
  });

  document.getElementById("dwNewSurface").addEventListener("click", () => {
    let i = dw.boundaries.findIndex(b => b.kind === "surface");
    if (i < 0) { dw.boundaries.push({ kind: "surface", name: null, points: [] });
                 i = dw.boundaries.length - 1; }
    dw.currentIdx = i; redraw();
  });
  document.getElementById("dwNewBottom").addEventListener("click", () => {
    const name = document.getElementById("dwName").value.trim();
    if (!name) { errEl().innerHTML = banner("err", `Give the new boundary a ${nameLabel} first.`); return; }
    errEl().innerHTML = "";
    dw.boundaries.push({ kind: "bottom", name, points: [] });
    dw.currentIdx = dw.boundaries.length - 1;
    document.getElementById("dwName").value = "";
    redraw();
  });
  document.getElementById("dwUndo").addEventListener("click", () => {
    if (dw.currentIdx >= 0) dw.boundaries[dw.currentIdx].points.pop();
    redraw();
  });
  document.getElementById("dwDelete").addEventListener("click", () => {
    if (dw.currentIdx < 0) return;
    dw.boundaries.splice(dw.currentIdx, 1);
    dw.currentIdx = -1; redraw();
  });

  document.getElementById("dwTrench").addEventListener("change",
    (ev) => { dw.trenchLabel = ev.target.value; });
  document.getElementById("dwFace").addEventListener("change",
    (ev) => { dw.faceLabel = ev.target.value; });
  document.getElementById("dwSquareCm")?.addEventListener("change",
    (ev) => { dw.squareCm = parseFloat(ev.target.value) || null; });

  document.getElementById("dwBuild").addEventListener("click", async () => {
    errEl().innerHTML = "";
    if (!calibReady()) { errEl().innerHTML = banner("err", "Finish calibration first (3 clicks + the real width)."); return; }
    if (!bottoms().length) { errEl().innerHTML = banner("err", "Draw at least one bottom boundary."); return; }
    const payload = {
      image: dw.imageKind,
      calibration: { origin_px: dw.clicks[0], ref_px: dw.clicks[1],
                     lowest_px: dw.clicks[2], ref_meters: dw.refM },
      boundaries: dw.boundaries.filter(b => b.points.length >= 2),
      trenchLabel: dw.trenchLabel, faceLabel: dw.faceLabel,
    };
    if (isField) {
      payload.square_cm = dw.squareCm;
      payload.loci = bottoms().map(b => ({
        locusNumber: b.name,
        munsellRaw: (dw.lociMeta[b.name] || {}).a || null,
        description: (dw.lociMeta[b.name] || {}).b || null,
      }));
    } else {
      payload.layerInfo = Object.fromEntries(bottoms().map(b => [b.name, {
        inferredMaterial: (dw.layerMeta[b.name] || {}).a || null,
        description: (dw.layerMeta[b.name] || {}).b || null,
      }]));
    }
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/boundaries/manual`, payload);
      dw.result = r;
      state.extract.rawJson = r.raw_json;
      state.extract.warning = null;
      invalidateDownstream("draw");
      state.completed.draw = true;
      state.completed.extract = true;
      const resEl = document.getElementById("dwResult");
      resEl.innerHTML = "";
      (r.warnings || []).forEach(w => { resEl.innerHTML += banner("warn", esc(w)); });
      resEl.innerHTML += banner("ok",
        "Extraction assembled from your drawn boundaries and installed — " +
        "no model touched the geometry. Continue to <strong>04 · Normalize</strong>.");
      const tree = document.createElement("div");
      tree.className = "json-tree";
      tree.appendChild(renderJsonTree(JSON.parse(r.raw_json)));
      resEl.appendChild(tree);
      refreshChrome();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  // restore in-progress work when navigating back to this step
  if (dw.imageUrl) showImage();
}

function renderExtract() {
  const isField = state.sheetType === "fieldwall";
  $content.innerHTML = `
    <div class="panel">
      <h2>03 · Extraction</h2>
      <p class="lede">Calls Gemini with a structured schema to transcribe the drawing —
      ${isField ? "Locus number + Munsell color for a field sheet" : "layers matched to a drawn hatch legend"} —
      directly into JSON. This is the only network-calling stage.</p>
      <div id="exFeatures">${state.features.confirmedCount ? banner("ok",
        `<strong>${state.features.confirmedCount}</strong> human-confirmed features from ` +
        `<strong>03 · Features</strong> are in force: Gemini tracing is instructed to ` +
        `reproduce exactly that inventory, and the CV-marker path attaches it with no ` +
        `network call.`) : ""}</div>

      <label class="field">
        <span class="label-text">Gemini API key</span>
        <input type="password" id="exApiKey" placeholder="GEMINI_API_KEY" value="${state.apiKey}">
        <span class="hint">Only sent to your own local server for this request; never stored on disk by this app.</span>
      </label>

      ${isField ? `
      <label class="field">
        <span class="label-text">Bold grid square size (cm)</span>
        <input type="number" id="exSquareCm" placeholder="e.g. 20" step="0.5" min="0.1" value="${state.markers.squareCm ?? ""}">
        <span class="hint">Human-confirmed, not re-derived from the image — measure the sheet's bold squares by hand.</span>
      </label>` : ""}

      <label class="field">
        <span class="label-text">Max output tokens</span>
        <input type="number" id="exMaxTokens" value="65536" step="8192" min="8192">
        <span class="hint">If extraction produces invalid/truncated JSON on a drawing with many
        layers or boundary points, raise this and re-run.</span>
      </label>

      <div class="btn-row">
        <button id="exRun">Run extraction</button>
      </div>

      <p class="lede" style="margin-top:18px">Or reuse a JSON from a previous run —
      no Gemini call, no API key needed. Accepts anything this pipeline produced:
      a download from the Visualize step or an artifact recovered from git history
      (e.g. <code>output_section001.json</code>).</p>
      <div class="btn-row">
        <input type="file" id="exJsonFile" accept=".json,application/json" style="display:none">
        <button class="secondary" id="exUpload">Upload previous extraction JSON</button>
      </div>

      ${isField ? `
      <h2 style="margin-top:26px">Build from confirmed CV markers (recommended)</h2>
      <p class="lede">Gemini tracing keeps fabricating boundary geometry on these sheets
      (even spacing, copy-pasted layers). This path instead uses the circle-marked
      vertices you confirmed in <strong>03 · Mark vertices</strong> — CV can't invent
      a dot that isn't on the paper — and has Gemini only <em>label</em> those fixed
      points and read the loci/Munsell text. It never touches coordinates.</p>
      <div id="mkStatus"></div>

      <div id="mkAssignWrap">
        <div class="btn-row">
          <button id="mkAssign">1 · Classify boundaries with Gemini</button>
        </div>
      </div>

      <div id="mkBoundaryReviewWrap" style="display:none">
        <h3 style="margin-top:22px">Review boundary assignment</h3>
        <p class="hint">Each dot is colored by Gemini's proposed classification.
        Click a dot to cycle it: noise → surface → bottom of locus 1 → bottom
        of locus 2 → … → back to noise. The line geometry is assembled
        deterministically from whatever classification is showing when you
        finalize — nothing here calls Gemini again.</p>
        <div style="position:relative;display:inline-block;max-width:100%;margin-top:8px">
          <img id="mkBoundaryImg" style="max-width:100%;display:block">
          <div id="mkBoundaryDots" style="position:absolute;inset:0"></div>
        </div>
        <div id="mkLegend" class="hint" style="margin-top:8px"></div>
        <div class="btn-row">
          <button id="mkFinalize">2 · Finalize boundaries &amp; build extraction</button>
        </div>
      </div>
      ` : ""}

      <div id="exError"></div>
      <div id="exLog" class="log-box" style="display:none"></div>
      <div id="exResult"></div>
    </div>
  `;

  function showExtractionResult(rawJson, okMessage, warning) {
    const resEl = document.getElementById("exResult");
    let data = null;
    try { data = JSON.parse(rawJson); } catch (e) { /* show raw below */ }
    resEl.innerHTML = "";
    if (warning) resEl.innerHTML += banner("warn", warning);
    resEl.innerHTML += banner("ok", okMessage);
    const treeHolder = document.createElement("div");
    treeHolder.className = "json-tree";
    if (data) treeHolder.appendChild(renderJsonTree(data));
    else treeHolder.textContent = rawJson;
    resEl.appendChild(treeHolder);
  }

  const fileInput = document.getElementById("exJsonFile");
  document.getElementById("exUpload").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", async () => {
    const errEl = document.getElementById("exError");
    errEl.innerHTML = "";
    const f = fileInput.files[0];
    if (!f) return;
    try {
      const fd = new FormData();
      fd.append("file", f);
      const r = await api(`/api/jobs/${state.jobId}/extract/upload`,
                          { method: "POST", body: fd });
      state.extract.rawJson = r.raw_json;
      state.extract.warning = null;
      if (r.sheet_type) state.sheetType = r.sheet_type;
      invalidateDownstream("extract");
      state.completed.extract = true;
      showExtractionResult(r.raw_json,
        `Installed <strong>${f.name}</strong> as this job's extraction ` +
        `(${r.sheet_type} schema) — Gemini was not called.`);
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      fileInput.value = "";  // allow re-selecting the same file
    }
  });

  // --- build from confirmed CV markers (field sheets only) ------------------
  // Detection/review/confirm now lives in its own step (03 · Mark vertices,
  // renderMarkers below); this half is the network-calling part: Gemini
  // classifies the already-confirmed points, the user reviews, finalize
  // assembles deterministically.
  if (isField) {
    const mk = state.markers;
    const errEl = () => document.getElementById("exError");

    function refreshMarkerStatus() {
      const st = document.getElementById("mkStatus");
      const btn = document.getElementById("mkAssign");
      if (!mk.confirmed.length) {
        st.innerHTML = banner("warn",
          "No confirmed markers yet — run <strong>03 · Mark vertices</strong> first. " +
          "(The plain Gemini tracing above still works without them, but its " +
          "geometry can't be trusted on these sheets.)");
        btn.disabled = true;
      } else {
        st.innerHTML = banner("ok",
          `<strong>${mk.confirmed.length}</strong> confirmed markers ready ` +
          `(from 03 · Mark vertices).`);
        btn.disabled = false;
      }
    }

    function lociNumbers() {
      return [...new Set(
        Object.values(mk.classifyById || {})
          .filter(a => a.kind === "bottom" && a.locusNumber)
          .map(a => String(a.locusNumber))
      )].sort();
    }

    function kindColor(a, loci) {
      if (!a || a.kind === "noise") return "#9aa39a";
      if (a.kind === "surface") return "#222";
      const idx = loci.indexOf(String(a.locusNumber || ""));
      return STRATA[(idx >= 0 ? idx : 0) % STRATA.length];
    }

    function renderBoundaryReview() {
      document.getElementById("mkBoundaryReviewWrap").style.display = "block";
      const img = document.getElementById("mkBoundaryImg");
      img.src = mk.previewImageUrl + "&t=" + Date.now();
      img.onload = drawBoundaryDots;
      window.addEventListener("resize", drawBoundaryDots);
      drawBoundaryDots();
      const loci = lociNumbers();
      const legendItems = loci.map((n, i) =>
        `<span style="color:${STRATA[i % STRATA.length]}">●</span> locus ${esc(n)}`).join(" &nbsp; ");
      document.getElementById("mkLegend").innerHTML =
        `<strong>Legend:</strong> <span style="color:#9aa39a">●</span> noise &nbsp; ` +
        `<span style="color:#222">●</span> surface ${loci.length ? "&nbsp; " + legendItems : ""}` +
        (mk.boundaryResult.warning ? banner("warn", mk.boundaryResult.warning) : "");
    }

    function drawBoundaryDots() {
      const img = document.getElementById("mkBoundaryImg");
      const dots = document.getElementById("mkBoundaryDots");
      dots.innerHTML = "";
      const sx = img.clientWidth / img.naturalWidth;
      const sy = img.clientHeight / img.naturalHeight;
      const loci = lociNumbers();
      mk.confirmed.forEach((m) => {
        const a = mk.classifyById[m.id];
        const d = document.createElement("div");
        const r = Math.max((m.diam_px || 20) / 2, 8) * Math.max(sx, sy);
        d.style.cssText = `position:absolute;width:${r*2}px;height:${r*2}px;border-radius:50%;
          transform:translate(-50%,-50%);left:${m.pixel_x*sx}px;top:${m.pixel_y*sy}px;
          border:3px solid ${kindColor(a, loci)};background:rgba(255,255,255,.2);
          cursor:pointer;box-sizing:border-box;`;
        d.title = a.kind === "bottom" ? `bottom of locus ${a.locusNumber} — click to cycle`
                                       : `${a.kind} — click to cycle`;
        d.addEventListener("click", (ev) => {
          ev.stopPropagation();
          cycleClassification(m.id);
          drawBoundaryDots();
        });
        dots.appendChild(d);
      });
    }

    function cycleClassification(markerId) {
      const loci = lociNumbers();
      const a = mk.classifyById[markerId];
      const seq = ["noise", "surface", ...loci.map(n => "bottom:" + n)];
      const cur = a.kind === "bottom" ? "bottom:" + a.locusNumber : a.kind;
      let idx = seq.indexOf(cur);
      idx = (idx + 1) % seq.length;
      const next = seq[idx];
      if (next.startsWith("bottom:")) {
        a.kind = "bottom"; a.locusNumber = next.slice(7);
      } else {
        a.kind = next; a.locusNumber = null;
      }
    }

    document.getElementById("mkAssign").addEventListener("click", async () => {
      errEl().innerHTML = "";
      const btn = document.getElementById("mkAssign");
      const logEl = document.getElementById("exLog");
      const apiKey = document.getElementById("exApiKey").value.trim();
      if (!apiKey) { errEl().innerHTML = banner("err", "API key is required (top of this panel)."); return; }
      if (!mk.confirmed.length) { errEl().innerHTML = banner("err", "Confirm markers in 03 · Mark vertices first."); return; }
      state.apiKey = apiKey;
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner"></span>Classifying...`;
      logEl.style.display = "block"; logEl.textContent = "";
      try {
        const r = await apiJson(`/api/jobs/${state.jobId}/markers/assign`, { api_key: apiKey });
        const t = await pollTask(r.task_id, (log, elapsed) => {
          logEl.textContent = `[${elapsed}s elapsed]\n` + log.join("\n");
        });
        mk.boundaryResult = t.result;  // {result_dict, warning}
        mk.classifyById = {};
        const byId = {};
        (mk.boundaryResult.result_dict.assignments || []).forEach(a => { byId[a.markerId] = a; });
        mk.confirmed.forEach(m => {
          const a = byId[m.id];
          mk.classifyById[m.id] = a ? { kind: a.kind, locusNumber: a.locusNumber || null }
                                     : { kind: "noise", locusNumber: null };
        });
        renderBoundaryReview();
      } catch (e) {
        errEl().innerHTML = errorBanner(e);
      } finally {
        btn.disabled = false;
        btn.textContent = "1 · Classify boundaries with Gemini";
      }
    });

    document.getElementById("mkFinalize").addEventListener("click", async () => {
      errEl().innerHTML = "";
      const btn = document.getElementById("mkFinalize");
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner"></span>Finalizing...`;
      try {
        const assignments = mk.confirmed.map(m => ({
          markerId: m.id, kind: mk.classifyById[m.id].kind,
          locusNumber: mk.classifyById[m.id].locusNumber,
        }));
        const finalResult = { ...mk.boundaryResult.result_dict, assignments };
        const r = await apiJson(`/api/jobs/${state.jobId}/markers/finalize`, { result: finalResult });
        state.extract.rawJson = r.raw_json;
        state.extract.warning = r.warning;
        state.sheetType = "fieldwall";
        invalidateDownstream("extract");
        state.completed.extract = true;
        showExtractionResult(r.raw_json,
          "Extraction built from CV markers — features and boundary assignment " +
          "were both reviewed by hand before assembly.", r.warning);
        refreshChrome();
      } catch (e) {
        errEl().innerHTML = errorBanner(e);
      } finally {
        btn.disabled = false;
        btn.textContent = "2 · Finalize boundaries & build extraction";
      }
    });

    refreshMarkerStatus();
    // restore a classification in progress if the user navigated away mid-review
    if (mk.boundaryResult && mk.classifyById && mk.confirmed.length) {
      renderBoundaryReview();
    }
  }

  document.getElementById("exRun").addEventListener("click", async () => {
    const btn = document.getElementById("exRun");
    const errEl = document.getElementById("exError");
    const logEl = document.getElementById("exLog");
    errEl.innerHTML = "";
    if (!state.completed.preprocess) {
      errEl.innerHTML = banner("err", "Run preprocess first (stage 02) — Gemini extraction " +
        "works on the cleaned image. To skip Gemini entirely, upload a previous " +
        "extraction JSON below instead.");
      return;
    }
    const apiKey = document.getElementById("exApiKey").value.trim();
    if (!apiKey) { errEl.innerHTML = banner("err", "API key is required."); return; }
    state.apiKey = apiKey;

    const body = { api_key: apiKey };
    const maxTokens = parseInt(document.getElementById("exMaxTokens").value, 10);
    if (maxTokens) body.max_output_tokens = maxTokens;
    if (isField) {
      const sc = parseFloat(document.getElementById("exSquareCm").value);
      if (!sc) { errEl.innerHTML = banner("err", "square-cm is required for field sheets."); return; }
      body.square_cm = sc;
    }

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>Analyzing...`;
    logEl.style.display = "block";
    logEl.textContent = "";
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/extract`, body);
      const t = await pollTask(r.task_id, (log, elapsed) => {
        logEl.textContent = `[${elapsed}s elapsed] ${extractWaitStatus(elapsed)}\n` +
          log.join("\n");
      });
      state.extract.rawJson = t.raw_json;
      state.extract.warning = t.warning;
      invalidateDownstream("extract");
      state.completed.extract = true;
      showExtractionResult(t.raw_json, "Extraction complete.", t.warning);
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Run extraction";
    }
  });
}

// ---------------------------------------------------------------------------
// STAGE 4a — normalize
// ---------------------------------------------------------------------------

function renderNormalize() {
  $content.innerHTML = `
    <div class="panel">
      <h2>04 · Normalize</h2>
      <p class="lede">Fixes literal "null" strings and de-duplicates floor / cross-layer
      features. Non-destructive — every change is logged.</p>
      <div class="btn-row"><button id="nRun">Run normalizer</button></div>
      <div id="nError"></div>
      <div id="nResult"></div>
    </div>
  `;

  document.getElementById("nRun").addEventListener("click", async () => {
    const btn = document.getElementById("nRun");
    const errEl = document.getElementById("nError");
    errEl.innerHTML = "";
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>Normalizing...`;
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/normalize`, {});
      state.normalize.data = r.data;
      state.normalize.log = r.log;
      invalidateDownstream("normalize");
      state.completed.normalize = true;
      const resEl = document.getElementById("nResult");
      resEl.innerHTML = r.log.length
        ? banner("warn", `${r.log.length} change(s) applied — see log below.`)
        : banner("ok", "No changes needed.");
      if (r.log.length) {
        const box = document.createElement("div");
        box.className = "log-box";
        box.textContent = r.log.join("\n");
        resEl.appendChild(box);
      }
      resEl.innerHTML += `<div class="download-list"><a class="file-link" href="${r.file_url}" download>output_clean.json</a></div>`;
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Run normalizer";
    }
  });
}

// ---------------------------------------------------------------------------
// STAGE 4b — validate
// ---------------------------------------------------------------------------

function renderValidate() {
  $content.innerHTML = `
    <div class="panel">
      <h2>04 · Validate</h2>
      <p class="lede">Sanity-checks the JSON: monotonic layer stacking, depth plausibility,
      feature containment. ERRORs would corrupt the GemPy model; WARNINGs are worth a human look.</p>

      <div class="row">
        <label class="field">
          <span class="label-text">Monotonic tolerance (m)</span>
          <input type="number" id="vMono" value="0.02" step="0.01">
        </label>
        <label class="field">
          <span class="label-text">Top continuity tolerance (m)</span>
          <input type="number" id="vTop" value="0.10" step="0.01">
        </label>
        <label class="field">
          <span class="label-text">Max plausible depth (m)</span>
          <input type="number" id="vDepth" value="5.0" step="0.5">
        </label>
      </div>

      <div class="btn-row"><button id="vRun">Run validator</button></div>
      <div id="vError"></div>
      <div id="vResult"></div>
    </div>
  `;

  document.getElementById("vRun").addEventListener("click", async () => {
    const btn = document.getElementById("vRun");
    const errEl = document.getElementById("vError");
    errEl.innerHTML = "";
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>Validating...`;
    try {
      const body = {
        monotonic_tolerance: parseFloat(document.getElementById("vMono").value),
        top_continuity_tolerance: parseFloat(document.getElementById("vTop").value),
        max_depth: parseFloat(document.getElementById("vDepth").value),
      };
      const r = await apiJson(`/api/jobs/${state.jobId}/validate`, body);
      state.validate.report = r;
      state.completed.validate = true;
      const resEl = document.getElementById("vResult");
      const counts = `${r.errors.length} error(s), ${r.warnings.length} warning(s).`;
      // Fabrication warnings (evenly-spaced vertices / boundaries copied down)
      // mean the geometry itself is untrustworthy even when nothing errors, so
      // don't let a zero-error run show a green all-clear.
      const fabricated = r.warnings.filter((w) =>
        w.includes("evenly spaced") || w.includes("identical boundary shapes")).length;
      resEl.innerHTML = !r.ok
        ? banner("err", counts)
        : r.warnings.length
          ? banner("warn", fabricated
              ? `${counts} ${fabricated} of them flag fabricated geometry — read these before building a model.`
              : `${counts} Worth a look before continuing.`)
          : banner("ok", counts);
      if (r.errors.length) {
        const box = document.createElement("div");
        box.className = "log-box";
        box.style.color = "#f4c7b8";
        box.textContent = r.errors.join("\n");
        resEl.appendChild(box);
      }
      if (r.warnings.length) {
        const box = document.createElement("div");
        box.className = "log-box";
        box.textContent = r.warnings.join("\n");
        resEl.appendChild(box);
      }
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Run validator";
    }
  });
}

// ---------------------------------------------------------------------------
// STAGE 5 — convert coords
// ---------------------------------------------------------------------------

function renderConvert() {
  $content.innerHTML = `
    <div class="panel">
      <h2>05 · Convert coordinates</h2>
      <p class="lede">Converts each face's local (x, depth) into site-wide (X, Y, Z) using a
      grid-registration config. <strong>This needs real survey data</strong> — the starter
      values below are placeholders that line faces up end-to-end for a pipeline smoke-test only.</p>
      <div id="cvError"></div>
      <div id="cvForm">Loading starter grid config…</div>
      <div id="cvResult"></div>
    </div>
  `;

  loadGridConfig();
}

async function loadGridConfig() {
  const formEl = document.getElementById("cvForm");
  const errEl = document.getElementById("cvError");
  try {
    const cfg = await api(`/api/jobs/${state.jobId}/gridconfig/starter`);
    state.convert.gridConfig = cfg;
    renderGridConfigForm(cfg);
  } catch (e) {
    formEl.innerHTML = "";
    errEl.innerHTML = errorBanner(e);
  }
}

function renderGridConfigForm(cfg) {
  const formEl = document.getElementById("cvForm");
  const faces = Object.keys(cfg.faces || {});
  let html = `<p class="hint">${cfg._comment}</p>`;
  html += `<div class="table-wrap grid-config-table"><table class="data-table"><thead><tr>
    <th>face</th><th>originX</th><th>originY</th><th>surfaceZ</th><th>bearing_deg</th>
  </tr></thead><tbody>`;
  faces.forEach((f) => {
    const c = cfg.faces[f];
    html += `<tr data-face="${f}">
      <td>${f}</td>
      <td><input type="number" step="0.1" class="gc-originX" value="${c.originX}"></td>
      <td><input type="number" step="0.1" class="gc-originY" value="${c.originY}"></td>
      <td><input type="number" step="0.1" class="gc-surfaceZ" value="${c.surfaceZ}"></td>
      <td><input type="number" step="0.1" class="gc-bearing" value="${c.bearing_deg}"></td>
    </tr>`;
  });
  html += `</tbody></table></div>
    <div class="btn-row"><button id="cvRun">Convert coordinates</button></div>`;
  formEl.innerHTML = html;

  document.getElementById("cvRun").addEventListener("click", async () => {
    const btn = document.getElementById("cvRun");
    const errEl = document.getElementById("cvError");
    errEl.innerHTML = "";
    const grid = { _comment: cfg._comment, faces: {} };
    document.querySelectorAll("#cvForm tr[data-face]").forEach((tr) => {
      const face = tr.dataset.face;
      grid.faces[face] = {
        originX: parseFloat(tr.querySelector(".gc-originX").value),
        originY: parseFloat(tr.querySelector(".gc-originY").value),
        surfaceZ: parseFloat(tr.querySelector(".gc-surfaceZ").value),
        bearing_deg: parseFloat(tr.querySelector(".gc-bearing").value),
      };
    });
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>Converting...`;
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/convert`, { grid_config: grid });
      state.convert.result = r;
      invalidateDownstream("convert");
      state.completed.convert = true;
      const resEl = document.getElementById("cvResult");
      let html = banner("ok", `Wrote ${r.n_points} interface point(s), ${r.n_orientations} orientation seed(s).`);
      if (r.missing_faces.length) html += banner("warn", `No grid config for: ${r.missing_faces.join(", ")} — skipped.`);
      html += `<div class="download-list">
        <a class="file-link" href="${r.points_csv_url}" download>points.csv</a>
        <a class="file-link" href="${r.orientations_csv_url}" download>points_orientations.csv</a>
      </div>`;
      html += dataTable(r.rows_preview);
      resEl.innerHTML = html;
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Convert coordinates";
    }
  });
}

// ---------------------------------------------------------------------------
// STAGE 6 — gempy
// ---------------------------------------------------------------------------

function renderGempy() {
  $content.innerHTML = `
    <div class="panel">
      <h2>06 · Build 3D model</h2>
      <p class="lede">Builds the GemPy model (one conformable series, order inferred from
      mean Z per surface unless overridden), computes it, and renders cross-sections.
      Requires <code>gempy</code> and <code>gempy_viewer</code> installed on this server.</p>

      <div class="row">
        <label class="field">
          <span class="label-text">Resolution (nx ny nz)</span>
          <input type="text" id="gpRes" value="50 50 30">
        </label>
        <label class="field">
          <span class="label-text">Section direction</span>
          <select id="gpDir"><option value="y">y</option><option value="x">x</option><option value="z">z</option></select>
        </label>
        <label class="field">
          <span class="label-text">Vertical exaggeration</span>
          <input type="number" id="gpVe" value="5.0" step="0.5">
        </label>
      </div>
      <label class="field">
        <span class="label-text">Series order override (optional)</span>
        <input type="text" id="gpSeries" placeholder="Topsoil;Fill;Virgin Soil (semicolon-separated, youngest first)">
        <span class="hint">Leave blank to auto-infer from mean Z per surface.</span>
      </label>

      <div class="btn-row"><button id="gpRun">Build model</button></div>
      <div id="gpError"></div>
      <div id="gpLog" class="log-box" style="display:none"></div>
      <div id="gpResult"></div>
    </div>
  `;

  document.getElementById("gpRun").addEventListener("click", async () => {
    const btn = document.getElementById("gpRun");
    const errEl = document.getElementById("gpError");
    const logEl = document.getElementById("gpLog");
    errEl.innerHTML = "";
    const res = document.getElementById("gpRes").value.trim().split(/\s+/).map(Number);
    const body = {
      resolution: res.length === 3 ? res : [50, 50, 30],
      section_direction: document.getElementById("gpDir").value,
      vertical_exaggeration: parseFloat(document.getElementById("gpVe").value),
    };
    const series = document.getElementById("gpSeries").value.trim();
    if (series) body.series_order = series;

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>Building (this can take a while)...`;
    logEl.style.display = "block";
    logEl.textContent = "";
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/gempy`, body);
      const t = await pollTask(r.task_id, (log, elapsed) => {
        logEl.textContent = `[${elapsed}s elapsed]\n` + log.join("\n");
      });
      const urls = await api(`/api/jobs/${state.jobId}/gempy/result/${r.task_id}`);
      state.gempy.result = urls;
      state.completed.gempy = true;
      const resEl = document.getElementById("gpResult");
      let html = banner("ok", `Stratigraphic order (young → old): ${urls.series_order.join(" → ")}`);
      if (urls.single_face_note) html += banner("warn", urls.single_face_note);
      html += `<div class="section-imgs">`;
      if (urls.outputs.section) html += `<figure><img src="${urls.outputs.section}"><figcaption>cross-section</figcaption></figure>`;
      if (urls.outputs.section_zoom) html += `<figure><img src="${urls.outputs.section_zoom}"><figcaption>zoomed (middle layers)</figcaption></figure>`;
      html += `</div>`;
      html += `<div class="download-list">`;
      if (urls.outputs.model) html += `<a class="file-link" href="${urls.outputs.model}" download>model.gempy</a>`;
      if (urls.outputs.lith_block) html += `<a class="file-link" href="${urls.outputs.lith_block}" download>lith_block.npz</a>`;
      (urls.outputs.meshes || []).forEach((m, i) => { html += `<a class="file-link" href="${m}" download>mesh ${i + 1}</a>`; });
      html += `</div>`;
      resEl.innerHTML = html;
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Build model";
    }
  });
}

// ---------------------------------------------------------------------------
// STAGE 7 — visualize
// ---------------------------------------------------------------------------

function renderVisualize() {
  $content.innerHTML = `
    <div class="panel">
      <h2>07 · Visualize</h2>
      <p class="lede">Standalone HTML viewer for inspecting the digitized profile, including
      A/B compare between two extraction runs against the original scan — handy since
      independent extraction runs can disagree and are easiest to reconcile by eye.</p>
      <div class="btn-row">
        <button id="openViz">Open visualizer</button>
        ${state.extract.rawJson ? `<button class="secondary" id="dlJson">Download extraction JSON</button>` : ""}
      </div>
      <p class="hint">Opens in a new tab with this job's scan and extraction
      pre-loaded from the server. The file pickers still work for loading a
      second run to A/B compare, or files from another job.</p>
    </div>
  `;
  document.getElementById("openViz").addEventListener("click", () =>
    window.open(state.jobId ? `/visualizer?job=${state.jobId}` : "/visualizer", "_blank"));
  const dl = document.getElementById("dlJson");
  if (dl) dl.addEventListener("click", () => {
    const blob = new Blob([state.extract.rawJson], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "extraction.json";
    a.click();
  });
}

// ---------------------------------------------------------------------------
// router
// ---------------------------------------------------------------------------

const RENDERERS = {
  scan: renderScan, preprocess: renderPreprocess, markers: renderMarkers,
  features: renderFeatures, draw: renderDraw,
  extract: renderExtract,
  normalize: renderNormalize, validate: renderValidate, convert: renderConvert,
  gempy: renderGempy, visualize: renderVisualize,
};

function render() {
  renderSidebar();
  (RENDERERS[state.current] || renderScan)();
  renderStepNav();
}

render();