import {
  api,
  apiJson,
  extractWaitStatus,
  pollTask,
} from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { invalidateDownstream, state } from "../core/state.js";
import {
  $content,
  banner,
  errorBanner,
  renderJsonTree,
} from "../core/ui.js";

export function renderExtract() {
  const isField = state.sheetType === "fieldwall";
  const manualReady = state.completed.draw && state.extract.rawJson;

  $content.innerHTML = `
    <div class="panel">
      <h2>03 · AI fallback</h2>
      <p class="lede">Use this only when you prefer automatic transcription or
      need to reuse an older extraction. The recommended workflow is
      <strong>03 · Trace drawing</strong>, where the user controls every boundary
      and feature coordinate.</p>

      ${manualReady ? banner("ok",
        "A manual extraction is already installed. Running or uploading another extraction will replace it.") : ""}

      <h3>Automatic transcription with Gemini</h3>
      <p class="hint">This path analyzes the preprocessed image and may require
      substantial manual review. It does not use the boundary polygons from the
      manual tracing screen.</p>

      <label class="field">
        <span class="label-text">Gemini API key</span>
        <input type="password" id="exApiKey" placeholder="GEMINI_API_KEY" value="${state.apiKey}">
        <span class="hint">Sent only to your local server for this request.</span>
      </label>

      ${isField ? `
        <label class="field">
          <span class="label-text">Bold grid square size (cm)</span>
          <input type="number" id="exSquareCm" placeholder="e.g. 20" step="0.5" min="0.1"
                 value="${state.draw.squareCm ?? ""}">
        </label>
      ` : ""}

      <label class="field">
        <span class="label-text">Max output tokens</span>
        <input type="number" id="exMaxTokens" value="65536" step="8192" min="8192">
      </label>

      <div class="btn-row">
        <button id="exRun">Run automatic extraction</button>
      </div>

      <h3 style="margin-top:26px">Reuse a previous extraction</h3>
      <p class="hint">Upload a JSON previously produced by this pipeline. No API
      key or model call is required.</p>
      <div class="btn-row">
        <input type="file" id="exJsonFile" accept=".json,application/json" style="display:none">
        <button class="secondary" id="exUpload">Upload extraction JSON</button>
      </div>

      <div id="exError"></div>
      <div id="exLog" class="log-box" style="display:none"></div>
      <div id="exResult"></div>
    </div>
  `;

  function showExtractionResult(rawJson, okMessage, warning) {
    const resultHolder = document.getElementById("exResult");
    let data = null;
    try { data = JSON.parse(rawJson); } catch (error) { /* show raw text */ }
    resultHolder.innerHTML = "";
    if (warning) resultHolder.innerHTML += banner("warn", warning);
    resultHolder.innerHTML += banner("ok", okMessage);
    const tree = document.createElement("div");
    tree.className = "json-tree";
    if (data) tree.appendChild(renderJsonTree(data));
    else tree.textContent = rawJson;
    resultHolder.appendChild(tree);
  }

  const fileInput = document.getElementById("exJsonFile");
  document.getElementById("exUpload").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", async () => {
    const errEl = document.getElementById("exError");
    errEl.innerHTML = "";
    const file = fileInput.files[0];
    if (!file) return;

    try {
      const form = new FormData();
      form.append("file", file);
      const result = await api(`/api/jobs/${state.jobId}/extract/upload`, {
        method: "POST",
        body: form,
      });
      invalidateDownstream("extract");
      state.extract.rawJson = result.raw_json;
      state.extract.warning = null;
      if (result.sheet_type) state.sheetType = result.sheet_type;
      state.completed.extract = true;
      showExtractionResult(
        result.raw_json,
        `Installed <strong>${file.name}</strong> as this job’s extraction. Gemini was not called.`
      );
      refreshChrome();
    } catch (error) {
      errEl.innerHTML = errorBanner(error);
    } finally {
      fileInput.value = "";
    }
  });

  document.getElementById("exRun").addEventListener("click", async () => {
    const button = document.getElementById("exRun");
    const errEl = document.getElementById("exError");
    const logEl = document.getElementById("exLog");
    errEl.innerHTML = "";

    if (!state.completed.preprocess) {
      errEl.innerHTML = banner(
        "err",
        "Run 02 · Preprocess first. Automatic extraction uses the cleaned image."
      );
      return;
    }

    const apiKey = document.getElementById("exApiKey").value.trim();
    if (!apiKey) {
      errEl.innerHTML = banner("err", "A Gemini API key is required for automatic extraction.");
      return;
    }
    state.apiKey = apiKey;

    const body = { api_key: apiKey };
    const maxTokens = Number(document.getElementById("exMaxTokens").value);
    if (maxTokens) body.max_output_tokens = maxTokens;

    if (isField) {
      const squareCm = Number(document.getElementById("exSquareCm").value);
      if (!squareCm) {
        errEl.innerHTML = banner("err", "Bold grid square size is required for a field sheet.");
        return;
      }
      body.square_cm = squareCm;
    }

    button.disabled = true;
    button.innerHTML = `<span class="spinner"></span>Analyzing...`;
    logEl.style.display = "block";
    logEl.textContent = "";

    try {
      const start = await apiJson(`/api/jobs/${state.jobId}/extract`, body);
      const task = await pollTask(start.task_id, (log, elapsed) => {
        logEl.textContent = `[${elapsed}s elapsed] ${extractWaitStatus(elapsed)}\n${log.join("\n")}`;
      });
      invalidateDownstream("extract");
      state.extract.rawJson = task.raw_json;
      state.extract.warning = task.warning;
      state.completed.extract = true;
      showExtractionResult(task.raw_json, "Automatic extraction complete.", task.warning);
      refreshChrome();
    } catch (error) {
      errEl.innerHTML = errorBanner(error);
    } finally {
      button.disabled = false;
      button.textContent = "Run automatic extraction";
    }
  });

  if (state.extract.rawJson) {
    showExtractionResult(
      state.extract.rawJson,
      state.completed.draw
        ? "Current extraction was built from manual tracing."
        : "Current extraction is installed."
    );
  }
}
