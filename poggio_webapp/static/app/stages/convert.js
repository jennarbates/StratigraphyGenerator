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
      <h2>05 · Convert coordinates</h2>
      <p class="lede">Converts each face's local (x, depth) into site-wide (X, Y, Z) using a
      grid-registration config. <strong>This needs real survey data</strong> — the starter
      values below are placeholders that line faces up end-to-end for a pipeline smoke-test only.</p>
      <div id="cvError"></div>
      <div id="cvForm">Loading starter grid config…</div>
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
  let html = `<p class="hint">${cfg._comment}</p>`;
  html += `<div class="table-wrap grid-config-table"><table class="data-table"><thead><tr>
    <th>face</th><th>originX</th><th>originY</th><th>surfaceZ</th><th>bearing_deg</th>
  </tr></thead><tbody>`;
  faces.forEach((f) => {
    const c = cfg.faces[f];
    html += `<tr data-face="${f}">
      <td>${f}</td>
      <td><input type="number" step="0.1" class="gc-originX" value="${c.originX}"></td>
      <td><input type="number" step="0.1" class="gc-originY" value="${c.originY}"></td>
      <td><input type="number" step="0.1" class="gc-surfaceZ" value="${c.surfaceZ}"></td>
      <td><input type="number" step="0.1" class="gc-bearing" value="${c.bearing_deg}"></td>
    </tr>`;
  });
  html += `</tbody></table></div>
    <div class="btn-row"><button id="cvRun">Convert coordinates</button></div>`;
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
      let html = banner("ok", `Wrote ${r.n_points} interface point(s), ${r.n_orientations} orientation seed(s).`);
      if (r.missing_faces.length) html += banner("warn", `No grid config for: ${r.missing_faces.join(", ")} — skipped.`);
      html += `<div class="download-list">
        <a class="file-link" href="${r.points_csv_url}" download>points.csv</a>
        <a class="file-link" href="${r.orientations_csv_url}" download>points_orientations.csv</a>
      </div>`;
      html += dataTable(r.rows_preview);
      resEl.innerHTML = html;
      refreshChrome();
    } catch (e) {
      errEl.innerHTML = errorBanner(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Convert coordinates";
    }
  });
}
