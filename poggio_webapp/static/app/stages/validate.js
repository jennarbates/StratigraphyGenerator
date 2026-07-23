import { apiJson } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { state } from "../core/state.js";
import { $content, banner, errorBanner } from "../core/ui.js";

export function renderValidate() {
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
