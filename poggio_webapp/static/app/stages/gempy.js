import { api, apiJson, pollTask } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { state } from "../core/state.js";
import { $content, banner, errorBanner } from "../core/ui.js";

export function renderGempy() {
  $content.innerHTML = `
    <div class="panel">
      <div class="stage-kicker">Step 7 of 8</div>
      <h2>Create the 3D model</h2>
      <p class="lede">The app now has everything it needs. Choose the button
      below and it will turn your traced layers into a 3D model.</p>

      <div class="plain-note">
        <span class="note-icon" aria-hidden="true">i</span>
        <span><strong>This may take several minutes.</strong><br>
        Keep this page open. A message will appear when the model is ready.</span>
      </div>

      <details class="advanced-settings">
        <summary>3D model settings (optional)</summary>
        <div class="details-body">
          <p class="hint">The recommended settings work for most models.
          Change them only when you need a specific scientific output.</p>
          <div class="row">
            <label class="field">
              <span class="label-text">Model detail (X Y Z)</span>
              <input type="text" id="gpRes" value="50 50 30">
            </label>
            <label class="field">
              <span class="label-text">Cross-section direction</span>
              <select id="gpDir">
                <option value="y">Front to back (Y)</option>
                <option value="x">Side to side (X)</option>
                <option value="z">Top to bottom (Z)</option>
              </select>
            </label>
            <label class="field">
              <span class="label-text">Make vertical differences easier to see</span>
              <input type="number" id="gpVe" value="5.0" step="0.5">
            </label>
          </div>
          <label class="field">
            <span class="label-text">Soil-layer order (optional)</span>
            <input type="text" id="gpSeries" placeholder="For example: Topsoil; Fill; Virgin Soil">
            <span class="hint">Leave this blank to work out the order automatically.
            If entered, list the youngest layer first and separate names with semicolons.</span>
          </label>
        </div>
      </details>

      <div class="btn-row"><button id="gpRun">Create my 3D model</button></div>
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
    btn.innerHTML = `<span class="spinner"></span>Creating your model… keep this page open`;
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
      let html = banner("ok", "Your 3D model has been created.");
      if (urls.single_face_note) html += banner("warn", urls.single_face_note);
      html += `<div class="section-imgs">`;
      if (urls.outputs.section) html += `<figure><img src="${urls.outputs.section}" alt="Cross-section of the 3D trench model"><figcaption>Full model cross-section</figcaption></figure>`;
      if (urls.outputs.section_zoom) html += `<figure><img src="${urls.outputs.section_zoom}" alt="Closer view of the middle layers"><figcaption>Closer view of the middle layers</figcaption></figure>`;
      html += `</div>`;
      html += `<div class="download-list">`;
      if (urls.outputs.model) html += `<a class="file-link" href="${urls.outputs.model}" download>Download 3D model</a>`;
      if (urls.outputs.lith_block) html += `<a class="file-link" href="${urls.outputs.lith_block}" download>Download model data</a>`;
      (urls.outputs.meshes || []).forEach((m, i) => { html += `<a class="file-link" href="${m}" download>Download surface ${i + 1}</a>`; });
      html += `</div>`;
      html += `<details class="technical-details"><summary>Layer order used</summary>
        <div class="details-body">${urls.series_order.join(" → ")} (youngest to oldest)</div></details>`;
      resEl.innerHTML = html;
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Create my 3D model";
    }
  });
}
