import { apiJson } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { invalidateDownstream, state } from "../core/state.js";
import { $content, banner, errorBanner } from "../core/ui.js";

export function renderMarkers() {
  const isField = state.sheetType === "fieldwall";
  const mk = state.markers;

  if (!isField) {
    $content.innerHTML = `
      <div class="panel">
        <h2>03 · Mark vertices</h2>
        <p class="lede">This step only applies to <strong>field recording
        sheets</strong>, where the recorder marks each measured vertex with a
        small circle that computer vision can find. Illustrator sheets have no
        such markers — continue straight to <strong>03 · Extraction</strong>.</p>
      </div>`;
    return;
  }

  $content.innerHTML = `
    <div class="panel">
      <h2>03 · Mark vertices</h2>
      <p class="lede">Finds the recorder's circle-marked vertices with computer
      vision — which can't invent a dot that isn't on the paper. No network
      call, no API key. The confirmed points feed the Extraction step, where
      Gemini only <em>labels</em> them.</p>

      <label class="field">
        <span class="label-text">Photo rotation</span>
        <select id="mkRotate">
          <option value="0">0° (already upright)</option>
          <option value="90">90° clockwise</option>
          <option value="180">180°</option>
          <option value="270">270° clockwise</option>
        </select>
        <span class="hint">If the photo was shot sideways, pick the rotation that makes it upright.</span>
      </label>
      <label class="field">
        <span class="label-text">Bold grid square size (cm)</span>
        <input type="number" id="mkSquareCm" placeholder="e.g. 20" step="0.5" min="0.1"
               value="${mk.squareCm ?? ""}">
        <span class="hint">Human-confirmed, not re-derived from the image — measure the sheet's bold squares by hand.</span>
      </label>
      <div class="btn-row">
        <button class="secondary" id="mkShow">1 · Show photo &amp; click reference points</button>
      </div>
      <div id="mkPickWrap" style="display:none">
        <p class="hint" id="mkPickHint"></p>
        <div style="position:relative;display:inline-block;max-width:100%">
          <img id="mkImg" style="max-width:100%;display:block;cursor:crosshair">
          <div id="mkDots" style="position:absolute;inset:0;pointer-events:none"></div>
        </div>
      </div>
      <label class="field">
        <span class="label-text">Real width between the two top corners (m)</span>
        <input type="number" id="mkRefM" step="0.5" min="0.1"
               placeholder="e.g. 4 (194 m → 190 m)" value="${mk.refM ?? ""}">
        <span class="hint">Read it off the sheet's own tie labels along the top edge.</span>
      </label>
      <div class="btn-row">
        <button class="secondary" id="mkDetect" disabled>2 · Detect markers</button>
      </div>
      <div id="mkResult"></div>

      <div id="mkReviewWrap" style="display:none">
        <h3 style="margin-top:22px">Review detected markers</h3>
        <p class="hint">Click a dot to accept/reject it — green = CV-accepted,
        red = CV-rejected, blue = manually added. Turn on "add feature" and
        click empty space to mark a vertex CV missed. (These dots are
        boundary <em>markers</em> — stones, cuts, and lenses belong in
        <strong>03 · Features</strong> instead.)</p>
        <div class="btn-row">
          <button class="secondary" id="mkAddMode">+ Add marker</button>
          <label class="hint" style="display:inline-flex;align-items:center;gap:6px;margin-left:12px">
            <input type="checkbox" id="mkShowRejected" checked>
            show rejected candidates (red)
          </label>
          <span id="mkAddModeStatus" class="hint"></span>
        </div>
        <div style="position:relative;display:inline-block;max-width:100%;margin-top:8px">
          <img id="mkReviewImg" style="max-width:100%;display:block">
          <div id="mkReviewDots" style="position:absolute;inset:0"></div>
        </div>
        <p class="hint" id="mkReviewCount"></p>
        <div class="btn-row">
          <button id="mkConfirm">3 · Confirm markers</button>
        </div>
      </div>

      <div id="mkConfirmed"></div>
      <div id="mkError"></div>
    </div>
  `;

  // clicks[0]=top-left (origin), [1]=top-right, [2]=lowest point of the wall
  const CLICK_LABELS = [
    "Click the wall's TOP-LEFT corner (x=0, depth=0).",
    "Now click the wall's TOP-RIGHT corner.",
    "Now click the LOWEST point of the drawn wall.",
    "All 3 points set — adjust by clicking again from the start, or continue below.",
  ];
  const COLORS = ["#c0269a", "#d17a1f", "#2a7ab5"];
  let addMode = false;

  const hintEl = () => document.getElementById("mkPickHint");
  const errEl = () => document.getElementById("mkError");

  document.getElementById("mkRotate").value = String(mk.rotate);
  document.getElementById("mkSquareCm").addEventListener("change", (ev) => {
    mk.squareCm = parseFloat(ev.target.value) || null;
  });
  document.getElementById("mkRefM").addEventListener("change", (ev) => {
    mk.refM = parseFloat(ev.target.value) || null;
  });

  function showConfirmedBanner() {
    document.getElementById("mkConfirmed").innerHTML = mk.confirmed.length
      ? banner("ok", `<strong>${mk.confirmed.length}</strong> markers confirmed — ` +
                     `continue to <strong>03 · Extraction</strong> to classify and ` +
                     `build the extraction.`)
      : "";
  }

  function drawDots() {
    const img = document.getElementById("mkImg");
    const dots = document.getElementById("mkDots");
    dots.innerHTML = "";
    const sx = img.clientWidth / img.naturalWidth;
    const sy = img.clientHeight / img.naturalHeight;
    mk.clicks.forEach((c, i) => {
      const d = document.createElement("div");
      d.style.cssText = `position:absolute;width:14px;height:14px;border-radius:50%;
        border:3px solid ${COLORS[i]};background:rgba(255,255,255,.5);
        transform:translate(-50%,-50%);left:${c[0]*sx}px;top:${c[1]*sy}px`;
      dots.appendChild(d);
    });
    hintEl().textContent = CLICK_LABELS[mk.clicks.length];
    document.getElementById("mkDetect").disabled = mk.clicks.length < 3;
  }

  function showPickWrap() {
    const img = document.getElementById("mkImg");
    img.src = mk.previewImageUrl + "&t=" + Date.now();  // bust cache on rotation change
    document.getElementById("mkPickWrap").style.display = "block";
    img.onload = drawDots;
    window.addEventListener("resize", drawDots);
  }

  document.getElementById("mkShow").addEventListener("click", async () => {
    errEl().innerHTML = "";
    try {
      mk.rotate = parseInt(document.getElementById("mkRotate").value, 10);
      const r = await apiJson(`/api/jobs/${state.jobId}/markers/preview`, { rotate: mk.rotate });
      mk.previewImageUrl = r.image_url;
      mk.clicks = [];
      showPickWrap();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  document.getElementById("mkImg")?.addEventListener("click", (ev) => {
    const img = ev.target;
    const rect = img.getBoundingClientRect();
    const px = (ev.clientX - rect.left) * img.naturalWidth / rect.width;
    const py = (ev.clientY - rect.top) * img.naturalHeight / rect.height;
    if (mk.clicks.length >= 3) mk.clicks = [];
    mk.clicks.push([Math.round(px), Math.round(py)]);
    drawDots();
  });

  document.getElementById("mkDetect").addEventListener("click", async () => {
    errEl().innerHTML = "";
    const resEl = document.getElementById("mkResult");
    const sc = parseFloat(document.getElementById("mkSquareCm").value);
    const refM = parseFloat(document.getElementById("mkRefM").value);
    if (!sc) { errEl().innerHTML = banner("err", "Bold grid square size (cm) is required — see the field above."); return; }
    if (!refM) { errEl().innerHTML = banner("err", "Real width between the top corners is required."); return; }
    mk.squareCm = sc; mk.refM = refM;
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/markers/detect`, {
        square_cm: sc, ref_meters: refM,
        origin_px: mk.clicks[0], ref_px: mk.clicks[1], bottom_px_y: mk.clicks[2][1],
        rotate: parseInt(document.getElementById("mkRotate").value, 10),
      });
      resEl.innerHTML =
        banner("ok", `Found <strong>${r.n_accepted}</strong> candidate features inside the wall ` +
          `(${r.n_rejected_in_box} rejected by size/shape filters, of which the ` +
          `${r.rejected.length} nearest misses are shown in red; scale ${r.px_per_m} px/m). ` +
          `Review them below — CV's filters aren't always right, and it can't ` +
          `mark a vertex that never got a filled-in dot.`) +
        `<div class="btn-row"><a class="secondary" style="text-decoration:none" ` +
        `href="${r.debug_image_url}" target="_blank"><button class="secondary">` +
        `Open raw debug image</button></a>` +
        `<a href="${r.csv_url}" download><button class="secondary">Download markers.csv</button></a></div>`;

      mk.features = [
        ...r.markers.map(m => ({ ...m, accepted: true, manual: false })),
        ...r.rejected.map(m => ({ ...m, accepted: false, manual: false })),
      ];
      // a fresh detection makes any previously confirmed set (and anything
      // built from it) stale — the server has already overwritten markers_path
      mk.confirmed = []; mk.boundaryResult = null; mk.classifyById = null;
      delete state.completed.markers;
      invalidateDownstream("markers");
      addMode = false;
      document.getElementById("mkAddMode").textContent = "+ Add marker";
      document.getElementById("mkAddModeStatus").textContent = "";
      showConfirmedBanner();
      showReviewWrap();
      refreshChrome();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  function showReviewWrap() {
    document.getElementById("mkReviewWrap").style.display = "block";
    const img = document.getElementById("mkReviewImg");
    img.src = mk.previewImageUrl + "&t=" + Date.now();
    img.onload = drawReviewDots;
    window.addEventListener("resize", drawReviewDots);
  }

  function drawReviewDots() {
    const img = document.getElementById("mkReviewImg");
    const dots = document.getElementById("mkReviewDots");
    dots.innerHTML = "";
    const sx = img.clientWidth / img.naturalWidth;
    const sy = img.clientHeight / img.naturalHeight;
    const showRejected = document.getElementById("mkShowRejected").checked;
    mk.features.forEach((f) => {
      if (!showRejected && !f.accepted && !f.manual) return;
      const d = document.createElement("div");
      // clamp in SCREEN pixels: small enough to never cover the drawing,
      // big enough to stay clickable regardless of image scale
      const r = Math.min(Math.max(((f.diam_px || 20) / 2) * Math.max(sx, sy), 6), 24);
      const color = f.manual ? "#2a7ab5" : (f.accepted ? "#3f9142" : "#c0392b");
      d.style.cssText = `position:absolute;width:${r*2}px;height:${r*2}px;border-radius:50%;
        transform:translate(-50%,-50%);left:${f.pixel_x*sx}px;top:${f.pixel_y*sy}px;
        border:3px solid ${color};background:rgba(255,255,255,.15);
        cursor:pointer;box-sizing:border-box;`;
      d.title = f.manual ? "manually added — click to remove"
                          : `circularity ${f.circularity} — click to ${f.accepted ? "reject" : "accept"}`;
      d.addEventListener("click", (ev) => {
        ev.stopPropagation();
        if (f.manual) { mk.features = mk.features.filter(x => x !== f); }
        else { f.accepted = !f.accepted; }
        drawReviewDots();
      });
      dots.appendChild(d);
    });
    const nAccepted = mk.features.filter(f => f.accepted).length;
    document.getElementById("mkReviewCount").textContent =
      `${nAccepted} of ${mk.features.length} markers accepted.`;
  }

  document.getElementById("mkShowRejected").addEventListener("change", drawReviewDots);

  document.getElementById("mkAddMode").addEventListener("click", () => {
    addMode = !addMode;
    document.getElementById("mkAddMode").textContent =
      addMode ? "+ Add marker (click the image; click here to stop)" : "+ Add marker";
    document.getElementById("mkAddModeStatus").textContent =
      addMode ? "Click anywhere on the image to place a marker." : "";
  });

  document.getElementById("mkReviewDots").addEventListener("click", (ev) => {
    if (!addMode) return;
    const img = document.getElementById("mkReviewImg");
    const rect = img.getBoundingClientRect();
    const px = (ev.clientX - rect.left) * img.naturalWidth / rect.width;
    const py = (ev.clientY - rect.top) * img.naturalHeight / rect.height;
    mk.features.push({ pixel_x: Math.round(px), pixel_y: Math.round(py),
                       diam_px: 20, circularity: 1, accepted: true, manual: true });
    drawReviewDots();
  });

  document.getElementById("mkConfirm").addEventListener("click", async () => {
    errEl().innerHTML = "";
    const accepted = mk.features.filter(f => f.accepted);
    if (!accepted.length) {
      errEl().innerHTML = banner("err", "Accept at least one marker before confirming.");
      return;
    }
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/markers/confirm`, { markers: accepted });
      mk.confirmed = r.markers;
      mk.boundaryResult = null;
      mk.classifyById = null;
      invalidateDownstream("markers");
      state.completed.markers = true;
      showConfirmedBanner();
      refreshChrome();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  // --- restore whatever was in progress when the user last left this step ---
  if (mk.previewImageUrl) showPickWrap();
  if (mk.previewImageUrl && mk.features.length) showReviewWrap();
  showConfirmedBanner();
}
