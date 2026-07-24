import { apiJson } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { invalidateDownstream, state } from "../core/state.js";
import { $content, banner, errorBanner } from "../core/ui.js";

export function renderNormalize() {
  $content.innerHTML = `
    <div class="panel">
      <div class="stage-kicker">Step 4 of 8</div>
      <h2>Clean up the data</h2>
      <p class="lede">This automatically fixes small formatting problems and
      removes accidental duplicates. It does not move any of the lines you traced.</p>
      <div class="plain-note">
        <span class="note-icon" aria-hidden="true">✓</span>
        <span><strong>No settings are needed.</strong><br>
        Choose the button once, then continue when the check is complete.</span>
      </div>
      <div class="btn-row"><button id="nRun">Clean up my data</button></div>
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
        ? banner("ok", `${r.log.length} small formatting change${r.log.length === 1 ? " was" : "s were"} made.`)
        : banner("ok", "No changes were needed.");
      if (r.log.length) {
        const details = document.createElement("details");
        details.className = "technical-details";
        const summary = document.createElement("summary");
        summary.textContent = "See exactly what changed";
        const box = document.createElement("div");
        box.className = "log-box";
        box.textContent = r.log.join("\n");
        details.appendChild(summary);
        details.appendChild(box);
        resEl.appendChild(details);
      }
      resEl.insertAdjacentHTML("beforeend",
        `<div class="download-list"><a class="file-link" href="${r.file_url}" download>Download cleaned data</a></div>`);
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Clean up my data";
    }
  });
}
