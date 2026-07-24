import { apiJson } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { invalidateDownstream, state } from "../core/state.js";
import { $content, banner, errorBanner } from "../core/ui.js";

export function renderPreprocess() {
  const rec = state.scan.recommendedUpscale;
  const defaultUpscale = rec ? rec.factor : 2;
  $content.innerHTML = `
    <div class="panel">
      <div class="stage-kicker">Step 2 of 8</div>
      <h2>Prepare the image</h2>
      <p class="lede">We’ll make the drawing clearer so its lines are easier to
      trace. The recommended settings work for most drawings.</p>

      ${state.scan.isPdf ? `
        <div class="action-card">
          <h3>Which PDF page contains the drawing?</h3>
          <label class="field">
            <span class="label-text">Page number</span>
            <input type="number" id="ppPage" value="1" step="1" min="1">
            <span class="hint">For the first page, leave this as 1.</span>
          </label>
        </div>
      ` : ""}

      <details class="advanced-settings">
        <summary>Image settings (optional)</summary>
        <div class="details-body">
          <p class="hint">You can leave these settings as they are unless the
          drawing is tilted, very small, or difficult to read.</p>
          <div class="row">
            <label class="field">
              <span class="label-text">Make the image larger</span>
              <input type="number" id="ppUpscale" value="${defaultUpscale}" step="0.5" min="1">
              ${rec ? `<span class="hint">Recommended for this image: ${rec.factor}× larger.</span>` : ""}
            </label>
        ${state.scan.isPdf ? `
            <label class="field">
              <span class="label-text">PDF image quality</span>
              <input type="number" id="ppDpi" value="300" step="10">
              <span class="hint">300 is the recommended setting.</span>
            </label>` : ""}
          </div>
          <div class="checkbox-row">
            <input type="checkbox" id="ppDeskew">
            <label for="ppDeskew">Straighten a slightly tilted scan</label>
          </div>
          <div class="checkbox-row">
            <input type="checkbox" id="ppHighcontrast">
            <label for="ppHighcontrast">Also make a high-contrast copy</label>
          </div>
        </div>
      </details>

      <div class="btn-row">
        <button id="ppRun">Prepare my drawing</button>
      </div>
      <div id="ppError"></div>
      <div id="ppResult"></div>
    </div>
  `;

  document.getElementById("ppRun").addEventListener("click", async () => {
    const btn = document.getElementById("ppRun");
    const errEl = document.getElementById("ppError");
    errEl.innerHTML = "";
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>Processing...`;
    try {
      const body = {
        upscale: parseFloat(document.getElementById("ppUpscale").value),
        deskew: document.getElementById("ppDeskew").checked,
        highcontrast: document.getElementById("ppHighcontrast").checked,
      };
      if (state.scan.isPdf) {
        body.pdf_dpi = parseInt(document.getElementById("ppDpi").value, 10);
        body.pdf_page = parseInt(document.getElementById("ppPage").value, 10);
      }
      const r = await apiJson(`/api/jobs/${state.jobId}/preprocess`, body);
      state.preprocess.cleanUrl = r.outputs.clean;
      invalidateDownstream("preprocess");
      state.completed.preprocess = true;
      const resEl = document.getElementById("ppResult");
      resEl.innerHTML = `
        ${banner("ok", "The clearer working copy is ready. Your original file was not changed.")}
        <div class="section-imgs">
          <figure><img src="${r.outputs.clean}" alt="Prepared trench drawing"><figcaption>Prepared drawing</figcaption></figure>
          ${r.outputs.highcontrast ? `<figure><img src="${r.outputs.highcontrast}" alt="High-contrast copy of the drawing"><figcaption>Optional high-contrast copy</figcaption></figure>` : ""}
        </div>
        <details class="technical-details">
          <summary>Technical details</summary>
          <div class="details-body">Straightening applied: ${r.deskew_angle.toFixed(2)}°</div>
        </details>
      `;
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Prepare my drawing";
    }
  });
}
