import { apiJson } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { invalidateDownstream, state } from "../core/state.js";
import { $content, banner, errorBanner } from "../core/ui.js";

export function renderNormalize() {
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
