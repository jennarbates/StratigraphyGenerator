import { apiJson } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { STRATA, invalidateDownstream, state } from "../core/state.js";
import {
  $content,
  banner,
  errorBanner,
  esc,
  renderJsonTree,
} from "../core/ui.js";

export function renderDraw() {
  const dw = state.draw;
  const isField = state.sheetType === "fieldwall";
  const nameLabel = isField ? "locus number" : "layer name";
  const isPdf = state.scan.isPdf;

  $content.innerHTML = `
    <div class="panel">
      <h2>03 · Draw boundaries <span class="hint">(optional)</span></h2>
      <p class="lede">Draw the boundary geometry yourself: click the drawn lines
      on a calibrated image, and the extraction is assembled deterministically —
      no model touches the geometry, no network call, no API key. Use this when
      a sheet is beyond what CV or Gemini reads reliably, or when you simply
      want full control. Building here installs the extraction directly; the
      Extraction step is then optional.</p>

      ${isPdf ? `
      <p class="hint">This scan is a PDF, so drawing happens on the
      <strong>preprocessed</strong> image${state.preprocess.cleanUrl ? "" :
      " — run <strong>02 · Preprocess</strong> first"}.</p>
      <div class="btn-row"><button class="secondary" id="dwShow"
        ${state.preprocess.cleanUrl ? "" : "disabled"}>1 · Show image</button></div>
      ` : `
      <label class="field">
        <span class="label-text">Image rotation</span>
        <select id="dwRotate">
          <option value="0">0° (already upright)</option>
          <option value="90">90° clockwise</option>
          <option value="180">180°</option>
          <option value="270">270° clockwise</option>
        </select>
      </label>
      <div class="btn-row"><button class="secondary" id="dwShow">1 · Show image</button></div>
      `}

      <div id="dwWrap" style="display:none">
        <p class="hint" id="dwHint"></p>
        <div class="btn-row">
          <button class="secondary" id="dwRecal">Recalibrate (clear the 3 reference clicks)</button>
        </div>
        <label class="field">
          <span class="label-text">Real width between the two top corners (m)</span>
          <input type="number" id="dwRefM" step="0.5" min="0.1"
                 placeholder="e.g. 4 (194 m → 190 m)" value="${dw.refM ?? ""}">
          <span class="hint">Read it off the sheet's own tie labels or scale bar.</span>
        </label>
        <div id="dwTools" style="display:none">
          <h3 style="margin-top:18px">Boundaries</h3>
          <p class="hint">Select a boundary, then click along its drawn line —
          each click adds a vertex. The surface line is the wall's top edge;
          every other boundary is the <em>bottom</em> of one ${isField ? "locus" : "layer"}.</p>
          <div class="btn-row">
            <button class="secondary" id="dwNewSurface">+ Surface line</button>
            <input id="dwName" placeholder="${nameLabel}" style="width:140px">
            <button class="secondary" id="dwNewBottom">+ Bottom boundary</button>
            <button class="secondary" id="dwUndo">Undo last point</button>
            <button class="secondary" id="dwDelete">Delete selected boundary</button>
          </div>
          <div id="dwChips" class="btn-row" style="flex-wrap:wrap"></div>
        </div>
        <div id="dwImgWrap" style="position:relative;display:inline-block;max-width:100%;margin-top:8px">
          <img id="dwImg" style="max-width:100%;display:block;cursor:crosshair">
          <svg id="dwSvg" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none"></svg>
        </div>
      </div>

      <div id="dwMetaWrap" style="display:none">
        <h3 style="margin-top:18px">Sheet details</h3>
        <div class="btn-row">
          <input id="dwTrench" placeholder="trench label (e.g. T104)" value="${esc(dw.trenchLabel)}">
          <input id="dwFace" placeholder="face label (e.g. south baulk)" value="${esc(dw.faceLabel)}">
          ${isField ? `<input type="number" id="dwSquareCm" step="0.5" min="0.1"
            placeholder="grid square (cm)" value="${dw.squareCm ?? ""}" style="width:150px">` : ""}
        </div>
        <div id="dwMeta"></div>
        <div class="btn-row">
          <button id="dwBuild">2 · Build extraction from drawn boundaries</button>
        </div>
      </div>

      <div id="dwResult"></div>
      <div id="dwError"></div>
    </div>
  `;

  const CAL_LABELS = [
    "Click the drawing's TOP-LEFT corner (x=0, depth=0).",
    "Now click the TOP-RIGHT corner.",
    "Now click the LOWEST point of the drawing.",
    "Calibrated. Select or create a boundary below, then click along its line.",
  ];
  const CAL_COLORS = ["#c0269a", "#d17a1f", "#2a7ab5"];
  const errEl = () => document.getElementById("dwError");
  const calibReady = () => dw.clicks.length >= 3 && dw.refM;

  function bottoms() { return dw.boundaries.filter(b => b.kind === "bottom"); }

  function redraw() {
    const img = document.getElementById("dwImg");
    const svg = document.getElementById("dwSvg");
    if (!img || !img.naturalWidth) return;
    svg.setAttribute("viewBox", `0 0 ${img.naturalWidth} ${img.naturalHeight}`);
    svg.setAttribute("preserveAspectRatio", "none");
    const r = Math.max(4, img.naturalWidth / 220);
    let out = "";
    dw.clicks.forEach((c, i) => {
      out += `<circle cx="${c[0]}" cy="${c[1]}" r="${r}" fill="rgba(255,255,255,.5)"
                stroke="${CAL_COLORS[i]}" stroke-width="${r * 0.6}"/>`;
    });
    dw.boundaries.forEach((b, i) => {
      const color = b.kind === "surface" ? "#2a7ab5" : STRATA[i % STRATA.length];
      const sel = i === dw.currentIdx;
      if (b.points.length > 1) {
        out += `<polyline points="${b.points.map(p => p.join(",")).join(" ")}"
                  fill="none" stroke="${color}" stroke-width="${r * (sel ? 0.9 : 0.5)}"
                  ${sel ? "" : `stroke-opacity="0.65"`}/>`;
      }
      b.points.forEach(p => {
        out += `<circle cx="${p[0]}" cy="${p[1]}" r="${r * (sel ? 0.9 : 0.6)}"
                  fill="${color}"/>`;
      });
    });
    svg.innerHTML = out;
    const hint = document.getElementById("dwHint");
    if (hint) hint.textContent = CAL_LABELS[Math.min(dw.clicks.length, 3)];
    drawChips();
    renderMeta();
  }

  function drawChips() {
    const chips = document.getElementById("dwChips");
    if (!chips) return;
    document.getElementById("dwTools").style.display = calibReady() ? "block" : "none";
    document.getElementById("dwMetaWrap").style.display =
      (calibReady() && bottoms().length) ? "block" : "none";
    chips.innerHTML = "";
    dw.boundaries.forEach((b, i) => {
      const el = document.createElement("button");
      el.className = "secondary";
      el.style.cssText = i === dw.currentIdx ? "outline:3px solid #2a7ab5" : "";
      el.textContent = (b.kind === "surface" ? "surface" :
        `${isField ? "locus" : "layer"} ${b.name}`) + ` (${b.points.length} pts)`;
      el.addEventListener("click", () => { dw.currentIdx = i; redraw(); });
      chips.appendChild(el);
    });
  }

  function renderMeta() {
    const holder = document.getElementById("dwMeta");
    if (!holder) return;
    const store = isField ? dw.lociMeta : dw.layerMeta;
    holder.innerHTML = bottoms().map(b => `
      <div class="btn-row" style="align-items:center;gap:8px" data-name="${esc(b.name)}">
        <span class="hint" style="min-width:90px">${isField ? "locus" : "layer"} ${esc(b.name)}</span>
        <input data-role="a" placeholder="${isField ? "Munsell (e.g. 10YR 5/3)" : "material (e.g. clay fill)"}"
               value="${esc((store[b.name] || {}).a || "")}">
        <input data-role="b" placeholder="description (optional)" style="flex:1;min-width:160px"
               value="${esc((store[b.name] || {}).b || "")}">
      </div>`).join("");
    holder.querySelectorAll("[data-name]").forEach(row => {
      const name = row.dataset.name;
      ["a", "b"].forEach(k => {
        row.querySelector(`[data-role="${k}"]`).addEventListener("change", (ev) => {
          store[name] = store[name] || {};
          store[name][k] = ev.target.value;
        });
      });
    });
  }

  function showImage() {
    document.getElementById("dwWrap").style.display = "block";
    const img = document.getElementById("dwImg");
    img.src = dw.imageUrl + (dw.imageUrl.includes("?") ? "&" : "?") + "t=" + Date.now();
    img.onload = redraw;
    window.addEventListener("resize", redraw);
  }

  document.getElementById("dwShow")?.addEventListener("click", async () => {
    errEl().innerHTML = "";
    try {
      if (isPdf) {
        dw.imageUrl = state.preprocess.cleanUrl;
        dw.imageKind = "clean";
      } else {
        dw.rotate = parseInt(document.getElementById("dwRotate").value, 10);
        const r = await apiJson(`/api/jobs/${state.jobId}/markers/preview`,
                                { rotate: dw.rotate });
        dw.imageUrl = r.image_url;
        dw.imageKind = "rotated";
      }
      dw.clicks = []; dw.boundaries = []; dw.currentIdx = -1;
      showImage();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  document.getElementById("dwRefM").addEventListener("change", (ev) => {
    dw.refM = parseFloat(ev.target.value) || null;
    redraw();
  });
  document.getElementById("dwRecal").addEventListener("click", () => {
    dw.clicks = []; redraw();
  });

  document.getElementById("dwImgWrap")?.addEventListener("click", (ev) => {
    const img = document.getElementById("dwImg");
    if (!img || ev.target !== img) return;
    const rect = img.getBoundingClientRect();
    const px = Math.round((ev.clientX - rect.left) * img.naturalWidth / rect.width);
    const py = Math.round((ev.clientY - rect.top) * img.naturalHeight / rect.height);
    if (dw.clicks.length < 3) {
      dw.clicks.push([px, py]);
    } else if (calibReady() && dw.currentIdx >= 0) {
      dw.boundaries[dw.currentIdx].points.push([px, py]);
    }
    redraw();
  });

  document.getElementById("dwNewSurface").addEventListener("click", () => {
    let i = dw.boundaries.findIndex(b => b.kind === "surface");
    if (i < 0) { dw.boundaries.push({ kind: "surface", name: null, points: [] });
                 i = dw.boundaries.length - 1; }
    dw.currentIdx = i; redraw();
  });
  document.getElementById("dwNewBottom").addEventListener("click", () => {
    const name = document.getElementById("dwName").value.trim();
    if (!name) { errEl().innerHTML = banner("err", `Give the new boundary a ${nameLabel} first.`); return; }
    errEl().innerHTML = "";
    dw.boundaries.push({ kind: "bottom", name, points: [] });
    dw.currentIdx = dw.boundaries.length - 1;
    document.getElementById("dwName").value = "";
    redraw();
  });
  document.getElementById("dwUndo").addEventListener("click", () => {
    if (dw.currentIdx >= 0) dw.boundaries[dw.currentIdx].points.pop();
    redraw();
  });
  document.getElementById("dwDelete").addEventListener("click", () => {
    if (dw.currentIdx < 0) return;
    dw.boundaries.splice(dw.currentIdx, 1);
    dw.currentIdx = -1; redraw();
  });

  document.getElementById("dwTrench").addEventListener("change",
    (ev) => { dw.trenchLabel = ev.target.value; });
  document.getElementById("dwFace").addEventListener("change",
    (ev) => { dw.faceLabel = ev.target.value; });
  document.getElementById("dwSquareCm")?.addEventListener("change",
    (ev) => { dw.squareCm = parseFloat(ev.target.value) || null; });

  document.getElementById("dwBuild").addEventListener("click", async () => {
    errEl().innerHTML = "";
    if (!calibReady()) { errEl().innerHTML = banner("err", "Finish calibration first (3 clicks + the real width)."); return; }
    if (!bottoms().length) { errEl().innerHTML = banner("err", "Draw at least one bottom boundary."); return; }
    const payload = {
      image: dw.imageKind,
      calibration: { origin_px: dw.clicks[0], ref_px: dw.clicks[1],
                     lowest_px: dw.clicks[2], ref_meters: dw.refM },
      boundaries: dw.boundaries.filter(b => b.points.length >= 2),
      trenchLabel: dw.trenchLabel, faceLabel: dw.faceLabel,
    };
    if (isField) {
      payload.square_cm = dw.squareCm;
      payload.loci = bottoms().map(b => ({
        locusNumber: b.name,
        munsellRaw: (dw.lociMeta[b.name] || {}).a || null,
        description: (dw.lociMeta[b.name] || {}).b || null,
      }));
    } else {
      payload.layerInfo = Object.fromEntries(bottoms().map(b => [b.name, {
        inferredMaterial: (dw.layerMeta[b.name] || {}).a || null,
        description: (dw.layerMeta[b.name] || {}).b || null,
      }]));
    }
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/boundaries/manual`, payload);
      dw.result = r;
      state.extract.rawJson = r.raw_json;
      state.extract.warning = null;
      invalidateDownstream("draw");
      state.completed.draw = true;
      state.completed.extract = true;
      const resEl = document.getElementById("dwResult");
      resEl.innerHTML = "";
      (r.warnings || []).forEach(w => { resEl.innerHTML += banner("warn", esc(w)); });
      resEl.innerHTML += banner("ok",
        "Extraction assembled from your drawn boundaries and installed — " +
        "no model touched the geometry. Continue to <strong>04 · Normalize</strong>.");
      const tree = document.createElement("div");
      tree.className = "json-tree";
      tree.appendChild(renderJsonTree(JSON.parse(r.raw_json)));
      resEl.appendChild(tree);
      refreshChrome();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  // restore in-progress work when navigating back to this step
  if (dw.imageUrl) showImage();
}
