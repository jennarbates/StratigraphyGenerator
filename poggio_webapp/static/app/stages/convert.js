import { api, apiJson } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { invalidateDownstream, state } from "../core/state.js";
import {
  $content,
  banner,
  dataTable,
  errorBanner,
} from "../core/ui.js";

export function renderConvert() {
  $content.innerHTML = `
    <div class="panel">
      <div class="stage-kicker">Step 6 of 8</div>
      <h2>Place the drawing on the site</h2>
      <p class="lede">Add the surveyed position of each trench face so the
      drawing appears in the correct place and at the correct height.</p>
      <div class="warning-card">
        <strong>Do not guess these numbers.</strong>
        The example values are only placeholders. Ask your survey lead for the
        real site coordinates and direction before creating a model you intend to use.
      </div>
      <div id="cvError"></div>
      <div id="cvForm"><span class="spinner"></span>Preparing the coordinate table…</div>
      <div id="cvResult"></div>
    </div>
  `;

  loadGridConfig();
}

async function loadGridConfig() {
  const formEl = document.getElementById("cvForm");
  const errEl = document.getElementById("cvError");
  try {
    const cfg = await api(`/api/jobs/${state.jobId}/gridconfig/starter`);
    state.convert.gridConfig = cfg;
    renderGridConfigForm(cfg);
  } catch (e) {
    formEl.innerHTML = "";
    errEl.innerHTML = errorBanner(e);
  }
}

function renderGridConfigForm(cfg) {
  const formEl = document.getElementById("cvForm");
  const faces = Object.keys(cfg.faces || {});
  let html = `
    <div class="table-explainer">
      <span><strong>Map position X</strong> — east/west position</span>
      <span><strong>Map position Y</strong> — north/south position</span>
      <span><strong>Ground height Z</strong> — height above the site datum</span>
      <span><strong>Direction</strong> — compass bearing in degrees</span>
    </div>`;
  html += `<div class="table-wrap grid-config-table"><table class="data-table"><thead><tr>
    <th>Trench face</th><th>Map position X</th><th>Map position Y</th><th>Ground height Z</th><th>Direction</th>
  </tr></thead><tbody>`;
  faces.forEach((f) => {
    const c = cfg.faces[f];
    html += `<tr data-face="${f}">
      <td>${f}</td>
      <td><input type="number" aria-label="Map position X for ${f}" step="0.1" class="gc-originX" value="${c.originX}"></td>
      <td><input type="number" aria-label="Map position Y for ${f}" step="0.1" class="gc-originY" value="${c.originY}"></td>
      <td><input type="number" aria-label="Ground height Z for ${f}" step="0.1" class="gc-surfaceZ" value="${c.surfaceZ}"></td>
      <td><input type="number" aria-label="Direction for ${f}" step="0.1" class="gc-bearing" value="${c.bearing_deg}"></td>
    </tr>`;
  });
  html += `</tbody></table></div>
    <details class="technical-details">
      <summary>Technical note about these values</summary>
      <div class="details-body">${cfg._comment || "Starter values were generated automatically."}</div>
    </details>
    <div class="btn-row"><button id="cvRun">Use these site coordinates</button></div>`;
  formEl.innerHTML = html;

  document.getElementById("cvRun").addEventListener("click", async () => {
    const btn = document.getElementById("cvRun");
    const errEl = document.getElementById("cvError");
    errEl.innerHTML = "";
    const grid = { _comment: cfg._comment, faces: {} };
    document.querySelectorAll("#cvForm tr[data-face]").forEach((tr) => {
      const face = tr.dataset.face;
      grid.faces[face] = {
        originX: parseFloat(tr.querySelector(".gc-originX").value),
        originY: parseFloat(tr.querySelector(".gc-originY").value),
        surfaceZ: parseFloat(tr.querySelector(".gc-surfaceZ").value),
        bearing_deg: parseFloat(tr.querySelector(".gc-bearing").value),
      };
    });
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>Converting...`;
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/convert`, { grid_config: grid });
      state.convert.result = r;
      invalidateDownstream("convert");
      state.completed.convert = true;
      const resEl = document.getElementById("cvResult");
      let html = banner("ok", `${r.n_points} drawing points are now placed on the site map.`);
      if (r.missing_faces.length) html += banner("warn", `These trench faces had no coordinates and were skipped: ${r.missing_faces.join(", ")}.`);
      html += `<div class="download-list">
        <a class="file-link" href="${r.points_csv_url}" download>Download placed points</a>
        <a class="file-link" href="${r.orientations_csv_url}" download>Download point directions</a>
      </div>`;
      html += `<details class="technical-details"><summary>Preview the coordinate data</summary>
        <div class="details-body">${dataTable(r.rows_preview)}</div></details>`;
      resEl.innerHTML = html;
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Use these site coordinates";
    }
  });
}
