/* Trench Digitization Pipeline — frontend
   Vanilla JS single-page wizard. No build step, talks to the Flask API
   in app.py. State lives in `state` below; each pipeline stage has a
   render_STAGE() function that draws its panel into #content.
*/

const STRATA = ["#9c6b3e", "#b98a4f", "#8a8c53", "#6c7a80", "#a4522f", "#5b7a9c", "#8a5ba0"];

const STEPS = [
  { id: "scan",       title: "Scan",        sub: "01_scans",              num: "01" },
  { id: "preprocess", title: "Preprocess",  sub: "02_preprocess",         num: "02" },
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
const PREREQS = {
  scan: [], preprocess: ["scan"], extract: ["preprocess"],
  normalize: ["extract"], validate: ["extract"],
  convert: ["normalize"], gempy: ["convert"], visualize: ["extract"],
};

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

function renderExtract() {
  const isField = state.sheetType === "fieldwall";
  $content.innerHTML = `
    <div class="panel">
      <h2>03 · Extraction</h2>
      <p class="lede">Calls Gemini with a structured schema to transcribe the drawing —
      ${isField ? "Locus number + Munsell color for a field sheet" : "layers matched to a drawn hatch legend"} —
      directly into JSON. This is the only network-calling stage.</p>

      <label class="field">
        <span class="label-text">Gemini API key</span>
        <input type="password" id="exApiKey" placeholder="GEMINI_API_KEY" value="${state.apiKey}">
        <span class="hint">Only sent to your own local server for this request; never stored on disk by this app.</span>
      </label>

      ${isField ? `
      <label class="field">
        <span class="label-text">Bold grid square size (cm)</span>
        <input type="number" id="exSquareCm" placeholder="e.g. 20" step="0.5" min="0.1">
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
      <div id="exError"></div>
      <div id="exLog" class="log-box" style="display:none"></div>
      <div id="exResult"></div>
    </div>
  `;

  document.getElementById("exRun").addEventListener("click", async () => {
    const btn = document.getElementById("exRun");
    const errEl = document.getElementById("exError");
    const logEl = document.getElementById("exLog");
    errEl.innerHTML = "";
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
      state.completed.extract = true;
      const resEl = document.getElementById("exResult");
      let data;
      try { data = JSON.parse(t.raw_json); } catch (e) { data = null; }
      resEl.innerHTML = "";
      if (t.warning) resEl.innerHTML += banner("warn", t.warning);
      resEl.innerHTML += banner("ok", "Extraction complete.");
      const treeHolder = document.createElement("div");
      treeHolder.className = "json-tree";
      if (data) treeHolder.appendChild(renderJsonTree(data));
      else treeHolder.textContent = t.raw_json;
      resEl.appendChild(treeHolder);
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
  scan: renderScan, preprocess: renderPreprocess, extract: renderExtract,
  normalize: renderNormalize, validate: renderValidate, convert: renderConvert,
  gempy: renderGempy, visualize: renderVisualize,
};

function render() {
  renderSidebar();
  (RENDERERS[state.current] || renderScan)();
  renderStepNav();
}

render();