import { state } from "../core/state.js";
import { refreshChrome } from "../core/navigation.js";
import { $content } from "../core/ui.js";
import { api } from "../core/api.js";

async function addHarrisAction() {
  if (!state.jobId) return;

  try {
    const sources = await api("/api/harris-source-jobs");
    if (
      !Array.isArray(sources)
      || !sources.some(source => source.job_id === state.jobId)
    ) {
      return;
    }

    const actions = document.querySelector("#visualize-actions");
    if (!actions) return;
    const link = document.createElement("a");
    link.className = "button-link secondary";
    link.href = (
      `/harris?source_job=${encodeURIComponent(state.jobId)}`
    );
    link.textContent = "Create or add to a Harris Matrix";
    actions.append(link);
  } catch (_error) {
    // Source discovery is optional; leave the action absent when unavailable.
  }
}

export function renderVisualize() {
  $content.innerHTML = `
    <div class="panel">
      <div class="stage-kicker">Step 9 of 9 · Finished</div>
      <h2>View and download your work</h2>
      <p class="lede">Open the interactive view to explore the trench drawing
      and its traced layers. When this job has a completed 3D surface model,
      you can explore it there too. Your files can also be saved for later use.</p>
      <div class="plain-note">
        <span class="note-icon" aria-hidden="true">✓</span>
        <span><strong>You’ve reached the end of the guide.</strong><br>
        Opening the interactive view will not change your saved work.</span>
      </div>
      <div class="btn-row" id="visualize-actions">
        <button id="openViz">Open the interactive view</button>
        ${state.extract.rawJson ? `<button class="secondary" id="dlJson">Download the traced data</button>` : ""}
      </div>
      <details class="technical-details">
        <summary>About the interactive view</summary>
        <div class="details-body">It opens in a new tab with this drawing already
        loaded. A completed 3D model appears alongside the drawing when one
        exists. Advanced users can also compare the drawing with a second
        tracing or load files from another job.</div>
      </details>
    </div>
  `;
  document.getElementById("openViz").addEventListener("click", () => {
    window.open(state.jobId ? `/visualizer?job=${state.jobId}` : "/visualizer", "_blank");
    state.completed.visualize = true;
    refreshChrome();
  });
  const dl = document.getElementById("dlJson");
  if (dl) dl.addEventListener("click", () => {
    const blob = new Blob([state.extract.rawJson], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "traced-drawing-data.json";
    a.click();
  });
  void addHarrisAction();
}
