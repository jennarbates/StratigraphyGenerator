import {
  api,
  apiJson,
  extractWaitStatus,
  pollTask,
} from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { STRATA, invalidateDownstream, state } from "../core/state.js";
import {
  $content,
  banner,
  errorBanner,
  esc,
  renderJsonTree,
} from "../core/ui.js";

export function renderExtract() {
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
