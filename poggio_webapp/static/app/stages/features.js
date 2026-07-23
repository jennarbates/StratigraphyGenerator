import { apiJson } from "../core/api.js";
import { refreshChrome } from "../core/navigation.js";
import { invalidateDownstream, state } from "../core/state.js";
import { $content, banner, errorBanner, esc } from "../core/ui.js";

const FEATURE_TYPES = ["rock/stone", "cut", "lens", "void", "other feature"];

export function renderFeatures() {
  const ft = state.features;
  $content.innerHTML = `
    <div class="panel">
      <h2>03 · Features <span class="hint">(optional)</span></h2>
      <p class="lede">Features are the objects <em>inside</em> layers (stones,
      cuts, lenses, voids), as opposed to markers, which are boundary vertices.
      Here CV proposes closed-contour candidates and <strong>you</strong> decide:
      accept, reject, re-label, or draw boxes it missed. The confirmed inventory
      is authoritative for every extraction path: Gemini tracing must reproduce
      it exactly, and the no-network paths attach it verbatim. No API key needed
      on this step.</p>
      <div class="btn-row">
        <button class="secondary" id="ftDetect">1 · Detect feature candidates</button>
      </div>
      <div id="ftInfo"></div>
      <div id="ftReviewWrap" style="display:none">
        <p class="hint">Click a box to accept/reject it. Amber dashed =
        CV proposal (not yet a feature), green = accepted, blue = drawn by you.
        Label every accepted feature in the list below.</p>
        <div class="btn-row">
          <button class="secondary" id="ftDrawMode">+ Draw a feature box</button>
          <span id="ftDrawStatus" class="hint"></span>
        </div>
        <div id="ftImgWrap" style="position:relative;display:inline-block;max-width:100%;margin-top:8px">
          <img id="ftImg" style="max-width:100%;display:block">
          <div id="ftBoxes" style="position:absolute;inset:0"></div>
        </div>
        <p class="hint" id="ftCount"></p>
        <div id="ftList"></div>
        <div class="btn-row">
          <button id="ftConfirm">2 · Confirm feature inventory</button>
        </div>
      </div>
      <div id="ftConfirmed"></div>
      <div id="ftError"></div>
    </div>
  `;

  const errEl = () => document.getElementById("ftError");
  let drawMode = false, dragStart = null, dragBox = null;

  function accepted() { return ft.candidates.filter(c => c.accepted); }

  function showConfirmedBanner() {
    document.getElementById("ftConfirmed").innerHTML = ft.confirmedCount
      ? banner("ok", `<strong>${ft.confirmedCount}</strong> features confirmed — ` +
               `they will be included in whichever extraction path you use ` +
               `(<strong>03 · Extraction</strong> or <strong>03 · Draw boundaries</strong>).`)
      : "";
  }

  function scale() {
    const img = document.getElementById("ftImg");
    return [img.clientWidth / img.naturalWidth, img.clientHeight / img.naturalHeight];
  }

  function drawBoxes() {
    const boxes = document.getElementById("ftBoxes");
    boxes.innerHTML = "";
    const [sx, sy] = scale();
    ft.candidates.forEach((c) => {
      const d = document.createElement("div");
      const color = c.manual ? "#2a7ab5" : (c.accepted ? "#3f9142" : "#c98a1b");
      d.style.cssText = `position:absolute;left:${c.x*sx}px;top:${c.y*sy}px;` +
        `width:${c.width*sx}px;height:${c.height*sy}px;box-sizing:border-box;` +
        `border:3px ${c.accepted || c.manual ? "solid" : "dashed"} ${color};` +
        `cursor:pointer;`;
      d.title = c.manual ? `${c.feature_type} (drawn by you) — click to remove`
                         : `score ${c.score ?? "-"} — click to ${c.accepted ? "reject" : "accept"}`;
      d.addEventListener("click", (ev) => {
        ev.stopPropagation();
        if (drawMode) return;
        if (c.manual) { ft.candidates = ft.candidates.filter(x => x !== c); }
        else { c.accepted = !c.accepted; }
        drawBoxes(); renderList();
      });
      boxes.appendChild(d);
    });
    document.getElementById("ftCount").textContent =
      `${accepted().length} of ${ft.candidates.length} candidates accepted as features.`;
  }

  function renderList() {
    const list = document.getElementById("ftList");
    const rows = accepted();
    if (!rows.length) { list.innerHTML = ""; return; }
    list.innerHTML = `<h3 style="margin-top:16px">Accepted features</h3>` +
      rows.map((c, i) => `
        <div class="btn-row" style="align-items:center;gap:8px" data-fi="${i}">
          <span class="hint" style="min-width:34px">F${i + 1}</span>
          <select data-role="type">${FEATURE_TYPES.map(t =>
            `<option ${t === c.feature_type ? "selected" : ""}>${t}</option>`).join("")}
          </select>
          <input data-role="desc" placeholder="description (optional)"
                 value="${esc(c.description || "")}" style="flex:1;min-width:180px">
          <span class="hint">${c.manual ? "drawn by you" : "CV proposal"}</span>
        </div>`).join("");
    list.querySelectorAll("[data-fi]").forEach((row) => {
      const c = rows[parseInt(row.dataset.fi, 10)];
      row.querySelector('[data-role="type"]').addEventListener("change",
        (ev) => { c.feature_type = ev.target.value; });
      row.querySelector('[data-role="desc"]').addEventListener("change",
        (ev) => { c.description = ev.target.value; });
    });
  }

  function showReview() {
    document.getElementById("ftReviewWrap").style.display = "block";
    const img = document.getElementById("ftImg");
    img.src = ft.imageUrl + "&t=" + Date.now();
    img.onload = () => { drawBoxes(); renderList(); };
    window.addEventListener("resize", drawBoxes);
  }

  document.getElementById("ftDetect").addEventListener("click", async () => {
    errEl().innerHTML = "";
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/features/detect`, {});
      ft.imageUrl = r.image_url; ft.imageKind = r.image_kind;
      ft.imgW = r.image_width; ft.imgH = r.image_height;
      ft.debugUrl = r.debug_image_url;
      ft.candidates = r.features.map(f => ({ ...f, accepted: false, manual: false,
                                             description: "" }));
      ft.confirmedCount = 0;
      delete state.completed.features;
      invalidateDownstream("features");
      document.getElementById("ftInfo").innerHTML =
        banner("ok", `CV proposed <strong>${r.candidate_count}</strong> closed-contour ` +
          `candidates on the <strong>${r.image_kind}</strong> image. None of them is a ` +
          `feature until you accept it — and you can reject all of them and only ` +
          `draw your own.`) +
        `<div class="btn-row"><a href="${r.debug_image_url}" target="_blank">` +
        `<button class="secondary">Open numbered debug image</button></a></div>`;
      showConfirmedBanner();
      showReview();
      refreshChrome();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  document.getElementById("ftDrawMode").addEventListener("click", () => {
    drawMode = !drawMode;
    document.getElementById("ftDrawMode").textContent =
      drawMode ? "+ Draw a feature box (drag on the image; click here to stop)"
               : "+ Draw a feature box";
    document.getElementById("ftDrawStatus").textContent =
      drawMode ? "Press, drag, and release to outline a feature." : "";
  });

  const boxesEl = () => document.getElementById("ftBoxes");
  function evToNatural(ev) {
    const img = document.getElementById("ftImg");
    const rect = img.getBoundingClientRect();
    return [(ev.clientX - rect.left) * img.naturalWidth / rect.width,
            (ev.clientY - rect.top) * img.naturalHeight / rect.height];
  }
  document.getElementById("ftImgWrap").addEventListener("mousedown", (ev) => {
    if (!drawMode) return;
    ev.preventDefault();
    dragStart = evToNatural(ev);
    dragBox = document.createElement("div");
    dragBox.style.cssText = "position:absolute;border:2px dashed #2a7ab5;pointer-events:none";
    boxesEl().appendChild(dragBox);
  });
  document.getElementById("ftImgWrap").addEventListener("mousemove", (ev) => {
    if (!drawMode || !dragStart) return;
    const [nx, ny] = evToNatural(ev);
    const [sx, sy] = scale();
    const x = Math.min(dragStart[0], nx), y = Math.min(dragStart[1], ny);
    const w = Math.abs(nx - dragStart[0]), h = Math.abs(ny - dragStart[1]);
    dragBox.style.left = (x * sx) + "px"; dragBox.style.top = (y * sy) + "px";
    dragBox.style.width = (w * sx) + "px"; dragBox.style.height = (h * sy) + "px";
  });
  document.getElementById("ftImgWrap").addEventListener("mouseup", (ev) => {
    if (!drawMode || !dragStart) return;
    const [nx, ny] = evToNatural(ev);
    const x = Math.min(dragStart[0], nx), y = Math.min(dragStart[1], ny);
    const w = Math.abs(nx - dragStart[0]), h = Math.abs(ny - dragStart[1]);
    dragStart = null;
    if (dragBox) { dragBox.remove(); dragBox = null; }
    if (w < 6 || h < 6) return;  // a click, not a drag
    ft.candidates.push({ x: Math.round(x), y: Math.round(y),
                         width: Math.round(w), height: Math.round(h),
                         feature_type: "rock/stone", description: "",
                         accepted: true, manual: true });
    drawBoxes(); renderList();
  });

  document.getElementById("ftConfirm").addEventListener("click", async () => {
    errEl().innerHTML = "";
    const rows = accepted();
    try {
      const r = await apiJson(`/api/jobs/${state.jobId}/features/confirm`, {
        features: rows.map(c => ({
          x: c.x, y: c.y, width: c.width, height: c.height,
          feature_type: c.feature_type, description: c.description,
          points: c.points || null, manual: c.manual,
        })),
      });
      ft.confirmedCount = r.n_confirmed;
      invalidateDownstream("features");
      state.completed.features = true;
      showConfirmedBanner();
      refreshChrome();
    } catch (e) { errEl().innerHTML = errorBanner(e); }
  });

  if (ft.imageUrl && ft.candidates.length) showReview();
  showConfirmedBanner();
}
