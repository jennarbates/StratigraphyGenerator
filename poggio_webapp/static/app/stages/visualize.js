import { state } from "../core/state.js";
import { $content } from "../core/ui.js";

export function renderVisualize() {
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
