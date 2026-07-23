import { api, ensureJob } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { invalidateDownstream, state } from "../core/state.js";
import { $content, banner, errorBanner } from "../core/ui.js";

export function renderScan() {
  $content.innerHTML = `
    <div class="panel">
      <h2>01 · Scan</h2>
      <p class="lede">Upload the raw drawing: an archival illustrator sheet (hatch-pattern
      legend) or a modern hand-drawn field sheet (Locus number + Munsell color).
      Each uses a different extraction schema downstream.</p>

      <div class="sheet-type-choice">
        <div class="sheet-card ${state.sheetType === "illustrator" ? "selected" : ""}" data-type="illustrator">
          <h3>Illustrator sheet</h3>
          <p>Drawn hatch/fill legend mapped to named materials. e.g. Trench 23, 1980.</p>
        </div>
        <div class="sheet-card ${state.sheetType === "fieldwall" ? "selected" : ""}" data-type="fieldwall">
          <h3>Field recording sheet</h3>
          <p>Hand-drawn on graph paper, Locus number + Munsell soil color. e.g. T104.</p>
        </div>
      </div>

      <div class="dropzone" id="dropzone">
        <input type="file" id="fileInput" accept=".png,.jpg,.jpeg,.pdf,.tif,.tiff">
        <div id="dzLabel">Drop a scan here, or click to choose a file<br>
        <span class="hint">PNG, JPEG, TIFF, or PDF</span></div>
      </div>

      <div id="scanError"></div>
      <div id="scanPreview"></div>
    </div>
  `;

  document.querySelectorAll(".sheet-card").forEach((c) => {
    c.addEventListener("click", () => {
      state.sheetType = c.dataset.type;
      renderScan();
    });
  });

  const dz = document.getElementById("dropzone");
  const input = document.getElementById("fileInput");
  dz.addEventListener("click", () => input.click());
  ["dragenter", "dragover"].forEach((ev) =>
    dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((ev) =>
    dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("drag"); }));
  dz.addEventListener("drop", (e) => {
    if (e.dataTransfer.files.length) handleScanFile(e.dataTransfer.files[0]);
  });
  input.addEventListener("change", () => {
    if (input.files.length) handleScanFile(input.files[0]);
  });

  if (state.scan.url) renderScanPreview();
}

function renderScanPreview() {
  const el = document.getElementById("scanPreview");
  if (!el) return;
  let html = state.scan.isPdf
    ? `<p class="lede">Uploaded ${state.scan.filename} (PDF — will be rasterized during preprocessing).</p>`
    : `<img class="preview-img" src="${state.scan.url}">`;
  if (state.scan.dims) {
    html += `<p class="hint" style="margin-top:8px">${state.scan.dims.width} × ${state.scan.dims.height} px</p>`;
  }
  if (state.scan.recommendedUpscale) {
    html += banner("ok",
      `Suggested upscale for preprocessing: <strong>${state.scan.recommendedUpscale.factor}×</strong> — ${state.scan.recommendedUpscale.reason}`);
  }
  el.innerHTML = html;
}

async function handleScanFile(file) {
  const errEl = document.getElementById("scanError");
  errEl.innerHTML = "";
  try {
    await ensureJob();
    const fd = new FormData();
    fd.append("file", file);
    fd.append("sheet_type", state.sheetType);
    const r = await api(`/api/jobs/${state.jobId}/scan`, { method: "POST", body: fd });
    state.scan.url = r.scan_url;
    state.scan.isPdf = r.is_pdf;
    state.scan.filename = file.name;
    state.scan.dims = r.dimensions;
    state.scan.recommendedUpscale = r.recommended_upscale;
    invalidateDownstream("scan");
    state.completed.scan = true;
    document.getElementById("dzLabel").textContent = `${file.name} uploaded`;
    renderScanPreview();
    refreshChrome();
  } catch (e) {
    errEl.innerHTML = errorBanner(e);
  }
}
