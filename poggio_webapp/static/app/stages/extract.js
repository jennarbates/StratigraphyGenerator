import {
  api,
  apiJson,
  extractWaitStatus,
  pollTask,
} from "../core/api.js";
import { goToStep, refreshChrome } from "../core/navigation.js";
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
      <div class="stage-kicker">Optional alternative</div>
      <h2>Other ways to add the drawing data</h2>
      <p class="lede">Most people should use <strong>Trace the layers</strong>.
      Use this page only if you already have a data file or have been asked to
      use automatic reading.</p>

      <div class="btn-row">
        <button class="secondary" id="exBackTrace">&larr; Return to Trace the layers</button>
      </div>

      ${manualReady ? banner("ok",
        "Traced data is already saved. Importing or automatically reading the drawing will replace it.") : ""}

      <div class="action-card">
        <h3>Import a data file you already have</h3>
        <p class="hint">Choose a JSON file previously made by this app. If you
        do not know what that means, return to “Trace the layers.”</p>
        <div class="btn-row">
          <input type="file" id="exJsonFile" accept=".json,application/json" style="display:none">
          <button class="secondary" id="exUpload">Choose an existing data file</button>
        </div>
      </div>

      <details class="advanced-settings">
        <summary>Read the drawing automatically with Gemini</summary>
        <div class="details-body">
          <div class="warning-card">
            <strong>Automatic reading can make mistakes.</strong>
            A person should carefully compare its result with the original drawing.
          </div>
          <label class="field">
            <span class="label-text">Gemini API key</span>
            <input type="password" id="exApiKey" placeholder="Paste the key here" value="${state.apiKey}">
            <span class="hint">This is a private access key supplied by Google.
            It is sent only to the local server for this one request.</span>
          </label>

          ${isField ? `
            <label class="field">
              <span class="label-text">Large grid-square size, in centimetres</span>
              <input type="number" id="exSquareCm" placeholder="For example: 20" step="0.5" min="0.1"
                     value="${state.draw.squareCm ?? ""}">
            </label>
          ` : ""}

          <details class="technical-details">
            <summary>Technical limit</summary>
            <div class="details-body">
              <label class="field">
                <span class="label-text">Maximum output tokens</span>
                <input type="number" id="exMaxTokens" value="65536" step="8192" min="8192">
              </label>
            </div>
          </details>

          <div class="btn-row">
            <button id="exRun">Read the drawing automatically</button>
          </div>
        </div>
      </details>

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
    const details = document.createElement("details");
    details.className = "technical-details";
    const summary = document.createElement("summary");
    summary.textContent = "Technical data";
    details.appendChild(summary);
    const tree = document.createElement("div");
    tree.className = "json-tree";
    if (data) tree.appendChild(renderJsonTree(data));
    else tree.textContent = rawJson;
    details.appendChild(tree);
    resultHolder.appendChild(details);
  }

  document.getElementById("exBackTrace").addEventListener("click", () => goToStep("draw"));
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
        `<strong>${file.name}</strong> is ready to use.`
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
        "Prepare the image before asking Gemini to read it."
      );
      return;
    }

    const apiKey = document.getElementById("exApiKey").value.trim();
    if (!apiKey) {
      errEl.innerHTML = banner("err", "Paste a Gemini API key before starting automatic reading.");
      return;
    }
    state.apiKey = apiKey;

    const body = { api_key: apiKey };
    const maxTokens = Number(document.getElementById("exMaxTokens").value);
    if (maxTokens) body.max_output_tokens = maxTokens;

    if (isField) {
      const squareCm = Number(document.getElementById("exSquareCm").value);
      if (!squareCm) {
        errEl.innerHTML = banner("err", "Enter the large grid-square size shown on the field sheet.");
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
      button.textContent = "Read the drawing automatically";
    }
  });

  if (state.extract.rawJson) {
    showExtractionResult(
      state.extract.rawJson,
      state.completed.draw
        ? "Your traced drawing data is ready."
        : "The imported drawing data is ready."
    );
  }
}
