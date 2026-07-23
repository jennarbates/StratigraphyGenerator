import { api, apiJson, pollTask } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { state } from "../core/state.js";
import { $content, banner, errorBanner } from "../core/ui.js";

export function renderGempy() {
  $content.innerHTML = `
    <div class="panel">
      <h2>06 · Build 3D model</h2>
      <p class="lede">Builds the GemPy model (one conformable series, order inferred from
      mean Z per surface unless overridden), computes it, and renders cross-sections.
      Requires <code>gempy</code> and <code>gempy_viewer</code> installed on this server.</p>

      <div class="row">
        <label class="field">
          <span class="label-text">Resolution (nx ny nz)</span>
          <input type="text" id="gpRes" value="50 50 30">
        </label>
        <label class="field">
          <span class="label-text">Section direction</span>
          <select id="gpDir"><option value="y">y</option><option value="x">x</option><option value="z">z</option></select>
        </label>
        <label class="field">
          <span class="label-text">Vertical exaggeration</span>
          <input type="number" id="gpVe" value="5.0" step="0.5">
        </label>
      </div>
      <label class="field">
        <span class="label-text">Series order override (optional)</span>
        <input type="text" id="gpSeries" placeholder="Topsoil;Fill;Virgin Soil (semicolon-separated, youngest first)">
        <span class="hint">Leave blank to auto-infer from mean Z per surface.</span>
      </label>

      <div class="btn-row"><button id="gpRun">Build model</button></div>
      <div id="gpError"></div>
      <div id="gpLog" class="log-box" style="display:none"></div>
      <div id="gpResult"></div>
    </div>
  `;

  document.getElementById("gpRun").addEventListener("click", async () => {
    const btn = document.getElementById("gpRun");
    const errEl = document.getElementById("gpError");
    const logEl = document.getElementById("gpLog");
    errEl.innerHTML = "";
    const res = document.getElementById("gpRes").value.trim().split(/\s+/).map(Number);
    const body = {
      resolution: res.length === 3 ? res : [50, 50, 30],
      section_direction: document.getElementById("gpDir").value,
      vertical_exaggeration: parseFloat(document.getElementById("gpVe").value),
    };
    const series = document.getElementById("gpSeries").value.trim();
    if (series) body.series_order = series;

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>Building (this can take a while)...`;
    logEl.style.display = "block";
    logEl.textContent = "";
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/gempy`, body);
      const t = await pollTask(r.task_id, (log, elapsed) => {
        logEl.textContent = `[${elapsed}s elapsed]\n` + log.join("\n");
      });
      const urls = await api(`/api/jobs/${state.jobId}/gempy/result/${r.task_id}`);
      state.gempy.result = urls;
      state.completed.gempy = true;
      const resEl = document.getElementById("gpResult");
      let html = banner("ok", `Stratigraphic order (young → old): ${urls.series_order.join(" → ")}`);
      if (urls.single_face_note) html += banner("warn", urls.single_face_note);
      html += `<div class="section-imgs">`;
      if (urls.outputs.section) html += `<figure><img src="${urls.outputs.section}"><figcaption>cross-section</figcaption></figure>`;
      if (urls.outputs.section_zoom) html += `<figure><img src="${urls.outputs.section_zoom}"><figcaption>zoomed (middle layers)</figcaption></figure>`;
      html += `</div>`;
      html += `<div class="download-list">`;
      if (urls.outputs.model) html += `<a class="file-link" href="${urls.outputs.model}" download>model.gempy</a>`;
      if (urls.outputs.lith_block) html += `<a class="file-link" href="${urls.outputs.lith_block}" download>lith_block.npz</a>`;
      (urls.outputs.meshes || []).forEach((m, i) => { html += `<a class="file-link" href="${m}" download>mesh ${i + 1}</a>`; });
      html += `</div>`;
      resEl.innerHTML = html;
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Build model";
    }
  });
}
