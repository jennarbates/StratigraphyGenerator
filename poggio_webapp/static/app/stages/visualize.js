import { state } from "../core/state.js";
import { refreshChrome } from "../core/navigation.js";
import { $content } from "../core/ui.js";

export function renderVisualize() {
  $content.innerHTML = `
    <div class="panel">
      <div class="stage-kicker">Step 8 of 8 · Finished</div>
      <h2>View and download your work</h2>
      <p class="lede">Open the interactive view to explore the trench drawing
      and its traced layers. Your files can also be saved for later use.</p>
      <div class="plain-note">
        <span class="note-icon" aria-hidden="true">✓</span>
        <span><strong>You’ve reached the end of the guide.</strong><br>
        Opening the interactive view will not change your saved work.</span>
      </div>
      <div class="btn-row">
        <button id="openViz">Open the interactive view</button>
        ${state.extract.rawJson ? `<button class="secondary" id="dlJson">Download the traced data</button>` : ""}
      </div>
      <details class="technical-details">
        <summary>About the interactive view</summary>
        <div class="details-body">It opens in a new tab with this drawing already
        loaded. Advanced users can also compare it with a second tracing or
        load files from another job.</div>
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
}
