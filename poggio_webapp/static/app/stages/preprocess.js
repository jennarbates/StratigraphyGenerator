import { apiJson } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { invalidateDownstream, state } from "../core/state.js";
import { $content, banner, errorBanner } from "../core/ui.js";

export function renderPreprocess() {
  const rec = state.scan.recommendedUpscale;
  const defaultUpscale = rec ? rec.factor : 2;
  $content.innerHTML = `
    <div class="panel">
      <h2>02 · Preprocess</h2>
      <p class="lede">Grayscale, background-flatten, upscale, and CLAHE-sharpen the scan so
      the vision model can resolve boundary lines. The "clean" output is what gets fed forward —
      it keeps fill hatching, unlike the optional high-contrast pass.</p>

      <div class="row">
        <label class="field">
          <span class="label-text">Upscale factor</span>
          <input type="number" id="ppUpscale" value="${defaultUpscale}" step="0.5" min="1">
          ${rec ? `<span class="hint">Suggested from upload resolution (${state.scan.dims.width}×${state.scan.dims.height}px): ${rec.reason}</span>` : ""}
        </label>
        ${state.scan.isPdf ? `
        <label class="field">
          <span class="label-text">PDF DPI</span>
          <input type="number" id="ppDpi" value="300" step="10">
        </label>
        <label class="field">
          <span class="label-text">PDF page</span>
          <input type="number" id="ppPage" value="1" step="1" min="1">
        </label>` : ""}
      </div>
      <div class="checkbox-row"><input type="checkbox" id="ppDeskew"><label for="ppDeskew">Deskew (straighten slight scan rotation)</label></div>
      <div class="checkbox-row"><input type="checkbox" id="ppHighcontrast"><label for="ppHighcontrast">Also generate high-contrast pass (boundary tracing only)</label></div>

      <div class="btn-row">
        <button id="ppRun">Run preprocessing</button>
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
        ${banner("ok", `Deskew angle applied: ${r.deskew_angle.toFixed(2)}°`)}
        <div class="section-imgs">
          <figure><img src="${r.outputs.clean}"><figcaption>clean (feed forward)</figcaption></figure>
          ${r.outputs.highcontrast ? `<figure><img src="${r.outputs.highcontrast}"><figcaption>high-contrast (boundary only)</figcaption></figure>` : ""}
        </div>
      `;
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Run preprocessing";
    }
  });
}
