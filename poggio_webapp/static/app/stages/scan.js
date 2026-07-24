import { api, apiJson, ensureJob } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { invalidateDownstream, state } from "../core/state.js";
import { $content, banner, errorBanner } from "../core/ui.js";
import { editorCreationPayload } from "./start-options.mjs";

export function renderScan() {
  const startContent = state.startMethod === "blank"
    ? `
      <div class="action-card blank-start">
        <h3>Start with a blank grid</h3>
        <p id="blankGridDescription">Open an empty drawing canvas with a grid,
        then add the lines and details for your diagram.</p>
        <button type="button" id="openBlankCanvas"
                aria-describedby="blankGridDescription blankStartStatus">
          Open blank drawing canvas
        </button>
        <div class="blank-start-status" id="blankStartStatus"
             role="status" aria-live="polite" aria-atomic="true"></div>
      </div>
    `
    : `
      <div class="plain-note">
        <span class="note-icon" aria-hidden="true">i</span>
        <span><strong>Your original file stays unchanged.</strong><br>
        The app makes a working copy for this drawing.</span>
      </div>

      <div class="dropzone" id="dropzone" role="button" tabindex="0"
           aria-label="Choose a trench drawing from your computer">
        <input type="file" id="fileInput" accept=".png,.jpg,.jpeg,.pdf,.tif,.tiff">
        <svg class="dropzone-icon" viewBox="0 0 48 48" aria-hidden="true">
          <path fill="currentColor" d="M24 5 13 17h7v13h8V17h7L24 5Zm-15 27v8h30v-8h4v12H5V32h4Z"/>
        </svg>
        <strong id="dzLabel">${state.scan.filename ? `${state.scan.filename} is ready` : "Drag your drawing here"}</strong>
        <span>or</span>
        <button type="button" id="chooseFile">Choose a file</button>
        <span class="file-types">PNG, JPEG, TIFF, or PDF</span>
      </div>

      <div id="scanError"></div>
      <div id="scanPreview"></div>
    `;

  $content.innerHTML = `
    <div class="panel">
      <div class="stage-kicker">Step 1 of 8</div>
      <h2>Add your trench drawing</h2>
      <p class="lede">Choose how you want to begin, then tell us what kind of
      diagram you are making.</p>

      <fieldset class="start-method-choice">
        <legend>How would you like to begin?</legend>
        <div class="start-method-options">
          <label class="start-method-card">
            <input type="radio" name="startMethod" value="upload"
                   ${state.startMethod === "upload" ? "checked" : ""}>
            <span class="start-method-card-content">
              <span class="start-method-indicator" aria-hidden="true"></span>
              <span class="start-method-copy">
                <strong>Use an existing drawing</strong>
                <span>Upload an image or PDF that is ready to trace.</span>
              </span>
            </span>
          </label>
          <label class="start-method-card">
            <input type="radio" name="startMethod" value="blank"
                   ${state.startMethod === "blank" ? "checked" : ""}>
            <span class="start-method-card-content">
              <span class="start-method-indicator" aria-hidden="true"></span>
              <span class="start-method-copy">
                <strong>Create a diagram from scratch</strong>
                <span>Begin on a blank grid and draw directly in the app.</span>
              </span>
            </span>
          </label>
        </div>
      </fieldset>

      <h3 class="choice-heading">What kind of diagram are you making?</h3>
      <div class="sheet-type-choice">
        <button type="button" class="sheet-card ${state.sheetType === "illustrator" ? "selected" : ""}"
                data-type="illustrator" aria-pressed="${state.sheetType === "illustrator"}">
          <span class="choice-check" aria-hidden="true">✓</span>
          <h3>Illustrated trench sheet</h3>
          <p>Choose this for a polished drawing with patterns or shading that
          describe soil and materials.</p>
        </button>
        <button type="button" class="sheet-card ${state.sheetType === "fieldwall" ? "selected" : ""}"
                data-type="fieldwall" aria-pressed="${state.sheetType === "fieldwall"}">
          <span class="choice-check" aria-hidden="true">✓</span>
          <h3>Hand-drawn field sheet</h3>
          <p>Choose this for a drawing on graph paper with locus numbers and
          handwritten soil colours.</p>
        </button>
      </div>

      ${startContent}
    </div>
  `;

  document.querySelectorAll('input[name="startMethod"]').forEach((input) => {
    input.addEventListener("change", () => {
      if (!input.checked) return;
      state.startMethod = input.value;
      renderScan();
    });
  });

  document.querySelectorAll(".sheet-card").forEach((c) => {
    c.addEventListener("click", () => {
      state.sheetType = c.dataset.type;
      renderScan();
    });
  });

  const blankCanvas = document.getElementById("openBlankCanvas");
  if (blankCanvas) {
    const status = document.getElementById("blankStartStatus");
    const originalLabel = blankCanvas.textContent;
    let requestPending = false;

    blankCanvas.addEventListener("click", async () => {
      if (requestPending) return;

      requestPending = true;
      blankCanvas.disabled = true;
      blankCanvas.textContent = "Creating your drawing…";
      status.textContent = "";

      try {
        const payload = editorCreationPayload(state.sheetType);
        const response = await apiJson("/editor/new", payload);
        window.location.assign(response.editor_url);
      } catch (error) {
        requestPending = false;
        blankCanvas.disabled = false;
        blankCanvas.textContent = originalLabel;
        status.innerHTML = errorBanner(error);
      }
    });
  }

  const dz = document.getElementById("dropzone");
  const input = document.getElementById("fileInput");
  const choose = document.getElementById("chooseFile");
  if (!dz) return;

  dz.addEventListener("click", (event) => {
    if (event.target !== choose) input.click();
  });
  dz.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      input.click();
    }
  });
  choose.addEventListener("click", (event) => {
    event.stopPropagation();
    input.click();
  });
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
    ? `<div class="preview-card"><h3>Drawing added</h3>
       <p>${state.scan.filename} is a PDF. The next step will turn its first page
       into an image you can work with.</p></div>`
    : `<div class="preview-card"><h3>Drawing added</h3>
       <img class="preview-img" src="${state.scan.url}" alt="Preview of the uploaded trench drawing"></div>`;
  if (state.scan.dims) {
    html += `<p class="hint" style="margin-top:8px">Image size: ${state.scan.dims.width} × ${state.scan.dims.height} pixels</p>`;
  }
  if (state.scan.recommendedUpscale) {
    html += banner("ok",
      "Your drawing has been added. Continue to prepare the image.");
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
    const label = document.getElementById("dzLabel");
    label.textContent = `${file.name} is ready`;
    label.classList.add("upload-ready");
    renderScanPreview();
    refreshChrome();
  } catch (e) {
    errEl.innerHTML = errorBanner(e);
  }
}
