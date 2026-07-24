import { apiJson } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { state } from "../core/state.js";
import { $content, banner, errorBanner } from "../core/ui.js";

export function renderValidate() {
  $content.innerHTML = `
    <div class="panel">
      <div class="stage-kicker">Step 5 of 8</div>
      <h2>Check for problems</h2>
      <p class="lede">The app will look for crossed lines, unlikely depths, and
      features outside their soil layers. It will tell you clearly if anything
      needs a person to review it.</p>

      <details class="advanced-settings">
        <summary>Checking rules (optional)</summary>
        <div class="details-body">
          <p class="hint">The recommended rules below work for most drawings.
          Change them only if your project lead gives you different values.</p>
          <div class="row">
            <label class="field">
              <span class="label-text">Allowed line overlap, in metres</span>
              <input type="number" id="vMono" value="0.02" step="0.01">
            </label>
            <label class="field">
              <span class="label-text">Allowed gap at the top, in metres</span>
              <input type="number" id="vTop" value="0.10" step="0.01">
            </label>
            <label class="field">
              <span class="label-text">Deepest expected point, in metres</span>
              <input type="number" id="vDepth" value="5.0" step="0.5">
            </label>
          </div>
        </div>
      </details>

      <div class="btn-row"><button id="vRun">Check my data</button></div>
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
      if (r.ok) state.completed.validate = true;
      else delete state.completed.validate;
      const resEl = document.getElementById("vResult");
      const counts = `${r.errors.length} serious problem${r.errors.length === 1 ? "" : "s"} and ` +
        `${r.warnings.length} item${r.warnings.length === 1 ? "" : "s"} to review.`;
      // Fabrication warnings (evenly-spaced vertices / boundaries copied down)
      // mean the geometry itself is untrustworthy even when nothing errors, so
      // don't let a zero-error run show a green all-clear.
      const fabricated = r.warnings.filter((w) =>
        w.includes("evenly spaced") || w.includes("identical boundary shapes")).length;
      resEl.innerHTML = !r.ok
        ? banner("err", `${counts} Fix the serious problems before creating the 3D model.`)
        : r.warnings.length
          ? banner("warn", fabricated
              ? `${counts} Some lines look unusually regular. Compare them with the original drawing before continuing.`
              : `${counts} Ask a knowledgeable team member to review these before continuing.`)
          : banner("ok", "No problems were found. You can continue.");
      if (r.errors.length) {
        const details = document.createElement("details");
        details.className = "technical-details";
        details.open = true;
        const summary = document.createElement("summary");
        summary.textContent = "Problems that must be fixed";
        const box = document.createElement("div");
        box.className = "log-box";
        box.style.color = "#f4c7b8";
        box.textContent = r.errors.join("\n");
        details.appendChild(summary);
        details.appendChild(box);
        resEl.appendChild(details);
      }
      if (r.warnings.length) {
        const details = document.createElement("details");
        details.className = "technical-details";
        const summary = document.createElement("summary");
        summary.textContent = "Items to review";
        const box = document.createElement("div");
        box.className = "log-box";
        box.textContent = r.warnings.join("\n");
        details.appendChild(summary);
        details.appendChild(box);
        resEl.appendChild(details);
      }
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Check my data";
    }
  });
}
