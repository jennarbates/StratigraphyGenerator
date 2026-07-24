import { apiJson } from "../core/api.js";
import { goToStep, refreshChrome } from "../core/navigation.js";
import { STRATA, invalidateDownstream, state } from "../core/state.js";
import {
  $content,
  banner,
  errorBanner,
  esc,
  renderJsonTree,
} from "../core/ui.js";

const FEATURE_TYPES = ["rock/stone", "cut", "lens", "void", "other feature"];

export function renderDraw() {
  const dw = state.draw;
  const isField = state.sheetType === "fieldwall";
  const nameLabel = isField ? "locus number" : "layer name";
  const isPdf = state.scan.isPdf;

  $content.innerHTML = `
    <div class="panel">
      <h2>03 · Trace drawing</h2>
      <p class="lede">This is the primary extraction workflow. You calibrate
      the image, trace each boundary, and outline any internal features. The
      server converts those clicks directly into measured JSON. Computer vision
      and Gemini are not required and do not alter the geometry.</p>

      ${isPdf ? `
        <p class="hint">PDFs must first be converted to an image in
        <strong>02 · Preprocess</strong>.</p>
        <div class="btn-row">
          <button class="secondary" id="dwShow" ${state.preprocess.cleanUrl ? "" : "disabled"}>
            1 · Open tracing image
          </button>
        </div>
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
        <div class="btn-row">
          <button class="secondary" id="dwShow">1 · Open tracing image</button>
        </div>
      `}

      <div id="dwWrap" style="display:none">
        <h3 style="margin-top:20px">A · Calibrate</h3>
        <p class="hint" id="dwHint"></p>
        <div class="btn-row">
          <button class="secondary" id="dwRecal">Clear calibration clicks</button>
        </div>
        <label class="field">
          <span class="label-text">Real width between the two top reference points (m)</span>
          <input type="number" id="dwRefM" step="0.01" min="0.01"
                 placeholder="e.g. 4" value="${dw.refM ?? ""}">
          <span class="hint">Use the sheet’s tie labels, scale bar, or known wall width.</span>
        </label>

        <div id="dwTools" style="display:none">
          <h3 style="margin-top:20px">B · Trace boundaries</h3>
          <p class="hint">Create a boundary, then click along the ink line in
          order from left to right. The first layer starts at the surface; each
          bottom boundary closes one ${isField ? "locus" : "layer"} and becomes
          the top of the next.</p>
          <div class="btn-row">
            <button class="secondary" id="dwNewSurface">+ Surface line</button>
            <input id="dwName" placeholder="${nameLabel}" style="width:150px">
            <button class="secondary" id="dwNewBottom">+ Bottom boundary</button>
          </div>
          <div class="btn-row">
            <button class="secondary" id="dwUndo">Undo selected point</button>
            <button class="secondary" id="dwDelete">Delete selected item</button>
            <span id="dwActive" class="hint"></span>
          </div>
          <div id="dwBoundaryChips" class="btn-row" style="flex-wrap:wrap"></div>

          <h3 style="margin-top:24px">C · Draw internal features <span class="hint">(optional)</span></h3>
          <p class="hint">Choose a feature type, create a polygon, click around
          its outline, then finish it. Polygons can represent stones, cuts,
          lenses, voids, or anything else inside the layers.</p>
          <div class="btn-row">
            <select id="dwFeatureType" style="max-width:180px">
              ${FEATURE_TYPES.map((type) => `<option>${type}</option>`).join("")}
            </select>
            <input id="dwFeatureDesc" placeholder="description (optional)" style="min-width:220px">
            <button class="secondary" id="dwNewFeature">+ New feature polygon</button>
            <button class="secondary" id="dwFinishFeature">Finish polygon</button>
          </div>
          <div id="dwFeatureChips" class="btn-row" style="flex-wrap:wrap"></div>
          <div id="dwFeatureMeta"></div>
        </div>

        <div id="dwImgWrap" style="position:relative;display:inline-block;max-width:100%;margin-top:10px">
          <img id="dwImg" style="max-width:100%;display:block;cursor:crosshair">
          <svg id="dwSvg" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none"></svg>
        </div>
      </div>

      <div id="dwMetaWrap" style="display:none">
        <h3 style="margin-top:22px">D · Layer details and build</h3>
        <div class="btn-row">
          <input id="dwTrench" placeholder="trench label (e.g. T104)" value="${esc(dw.trenchLabel)}">
          <input id="dwFace" placeholder="face label (e.g. south baulk)" value="${esc(dw.faceLabel)}">
          ${isField ? `<input type="number" id="dwSquareCm" step="0.5" min="0.1"
            placeholder="grid square (cm)" value="${dw.squareCm ?? ""}" style="width:160px">` : ""}
        </div>
        <div id="dwMeta"></div>
        <div class="btn-row">
          <button id="dwBuild">2 · Build manual extraction</button>
        </div>
      </div>

      <div id="dwResult"></div>
      <div id="dwError"></div>
    </div>
  `;

  const CAL_LABELS = [
    "Click the drawing’s TOP-LEFT reference point.",
    "Click the TOP-RIGHT reference point.",
    "Click the LOWEST point of the drawing so the app knows which direction is down.",
    "Calibration points are set. Enter the real width, then trace the drawing.",
  ];
  const CAL_COLORS = ["#c0269a", "#d17a1f", "#2a7ab5"];
  const errEl = () => document.getElementById("dwError");
  const calibReady = () => dw.clicks.length >= 3 && Number(dw.refM) > 0;
  const bottoms = () => dw.boundaries.filter((boundary) => boundary.kind === "bottom");

  if (!isPdf) document.getElementById("dwRotate").value = String(dw.rotate || 0);

  function activeItem() {
    if (dw.activeKind === "boundary") return dw.boundaries[dw.activeIdx] || null;
    if (dw.activeKind === "feature") return dw.features[dw.activeIdx] || null;
    return null;
  }

  function setActive(kind, index) {
    dw.activeKind = kind;
    dw.activeIdx = index;
    redraw();
  }

  function renderBoundaryChips() {
    const holder = document.getElementById("dwBoundaryChips");
    holder.innerHTML = "";
    dw.boundaries.forEach((boundary, index) => {
      const button = document.createElement("button");
      button.className = "secondary";
      if (dw.activeKind === "boundary" && dw.activeIdx === index) {
        button.style.outline = "3px solid #2a7ab5";
      }
      const label = boundary.kind === "surface"
        ? "surface"
        : `${isField ? "locus" : "layer"} ${boundary.name}`;
      button.textContent = `${label} (${boundary.points.length} pts)`;
      button.addEventListener("click", () => setActive("boundary", index));
      holder.appendChild(button);
    });
  }

  function renderFeatureChips() {
    const holder = document.getElementById("dwFeatureChips");
    holder.innerHTML = "";
    dw.features.forEach((feature, index) => {
      const button = document.createElement("button");
      button.className = "secondary";
      if (dw.activeKind === "feature" && dw.activeIdx === index) {
        button.style.outline = "3px solid #2a7ab5";
      }
      const status = feature.closed ? "closed" : "drawing";
      button.textContent = `F${index + 1}: ${feature.feature_type} (${feature.points.length} pts, ${status})`;
      button.addEventListener("click", () => setActive("feature", index));
      holder.appendChild(button);
    });
  }

  function renderFeatureMeta() {
    const holder = document.getElementById("dwFeatureMeta");
    holder.innerHTML = dw.features.map((feature, index) => `
      <div class="btn-row" style="align-items:center;gap:8px" data-feature-index="${index}">
        <span class="hint" style="min-width:28px">F${index + 1}</span>
        <select data-role="type">
          ${FEATURE_TYPES.map((type) => `<option ${type === feature.feature_type ? "selected" : ""}>${type}</option>`).join("")}
        </select>
        <input data-role="description" placeholder="description (optional)"
               value="${esc(feature.description || "")}" style="flex:1;min-width:220px">
      </div>
    `).join("");

    holder.querySelectorAll("[data-feature-index]").forEach((row) => {
      const feature = dw.features[Number(row.dataset.featureIndex)];
      row.querySelector('[data-role="type"]').addEventListener("change", (event) => {
        feature.feature_type = event.target.value;
        renderFeatureChips();
      });
      row.querySelector('[data-role="description"]').addEventListener("change", (event) => {
        feature.description = event.target.value;
      });
    });
  }

  function renderLayerMeta() {
    const holder = document.getElementById("dwMeta");
    const store = isField ? dw.lociMeta : dw.layerMeta;
    holder.innerHTML = bottoms().map((boundary) => `
      <div class="btn-row" style="align-items:center;gap:8px" data-name="${esc(boundary.name)}">
        <span class="hint" style="min-width:95px">${isField ? "locus" : "layer"} ${esc(boundary.name)}</span>
        <input data-role="a" placeholder="${isField ? "Munsell (e.g. 10YR 5/3)" : "material (e.g. clay fill)"}"
               value="${esc((store[boundary.name] || {}).a || "")}">
        <input data-role="b" placeholder="description (optional)" style="flex:1;min-width:180px"
               value="${esc((store[boundary.name] || {}).b || "")}">
      </div>
    `).join("");

    holder.querySelectorAll("[data-name]").forEach((row) => {
      const name = row.dataset.name;
      ["a", "b"].forEach((key) => {
        row.querySelector(`[data-role="${key}"]`).addEventListener("change", (event) => {
          store[name] = store[name] || {};
          store[name][key] = event.target.value;
        });
      });
    });
  }

  function redraw() {
    const img = document.getElementById("dwImg");
    const svg = document.getElementById("dwSvg");
    if (!img || !img.naturalWidth) return;

    svg.setAttribute("viewBox", `0 0 ${img.naturalWidth} ${img.naturalHeight}`);
    svg.setAttribute("preserveAspectRatio", "none");
    const radius = Math.max(4, img.naturalWidth / 240);
    let output = "";

    dw.clicks.forEach((click, index) => {
      output += `<circle cx="${click[0]}" cy="${click[1]}" r="${radius}"
        fill="rgba(255,255,255,.55)" stroke="${CAL_COLORS[index]}"
        stroke-width="${radius * 0.65}"/>`;
    });

    dw.boundaries.forEach((boundary, index) => {
      const selected = dw.activeKind === "boundary" && dw.activeIdx === index;
      const color = boundary.kind === "surface" ? "#2a7ab5" : STRATA[index % STRATA.length];
      if (boundary.points.length > 1) {
        output += `<polyline points="${boundary.points.map((point) => point.join(",")).join(" ")}"
          fill="none" stroke="${color}" stroke-width="${radius * (selected ? 0.95 : 0.58)}"
          stroke-opacity="${selected ? 1 : 0.72}"/>`;
      }
      boundary.points.forEach((point) => {
        output += `<circle cx="${point[0]}" cy="${point[1]}"
          r="${radius * (selected ? 0.9 : 0.62)}" fill="${color}"/>`;
      });
    });

    dw.features.forEach((feature, index) => {
      const selected = dw.activeKind === "feature" && dw.activeIdx === index;
      const color = "#7a3fa0";
      const points = feature.points.map((point) => point.join(",")).join(" ");
      if (feature.closed && feature.points.length >= 3) {
        output += `<polygon points="${points}" fill="rgba(122,63,160,.15)"
          stroke="${color}" stroke-width="${radius * (selected ? 0.95 : 0.58)}"/>`;
      } else if (feature.points.length > 1) {
        output += `<polyline points="${points}" fill="none" stroke="${color}"
          stroke-dasharray="${radius * 2} ${radius}" stroke-width="${radius * (selected ? 0.95 : 0.58)}"/>`;
      }
      feature.points.forEach((point) => {
        output += `<circle cx="${point[0]}" cy="${point[1]}"
          r="${radius * (selected ? 0.9 : 0.62)}" fill="${color}"/>`;
      });
    });

    svg.innerHTML = output;
    document.getElementById("dwHint").textContent = CAL_LABELS[Math.min(dw.clicks.length, 3)];
    document.getElementById("dwTools").style.display = calibReady() ? "block" : "none";
    document.getElementById("dwMetaWrap").style.display = calibReady() && bottoms().length ? "block" : "none";

    const active = activeItem();
    document.getElementById("dwActive").textContent = active
      ? `Selected ${dw.activeKind}: ${active.kind === "surface" ? "surface" : active.name || active.feature_type}`
      : "Select an item before adding points.";

    renderBoundaryChips();
    renderFeatureChips();
    renderFeatureMeta();
    renderLayerMeta();
  }

  function showImage() {
    document.getElementById("dwWrap").style.display = "block";
    const img = document.getElementById("dwImg");
    img.src = dw.imageUrl + (dw.imageUrl.includes("?") ? "&" : "?") + `t=${Date.now()}`;
    img.onload = redraw;
  }

  document.getElementById("dwShow")?.addEventListener("click", async () => {
    errEl().innerHTML = "";
    try {
      if (isPdf) {
        dw.imageUrl = state.preprocess.cleanUrl;
        dw.imageKind = "clean";
      } else {
        dw.rotate = Number(document.getElementById("dwRotate").value || 0);
        const result = await apiJson(`/api/jobs/${state.jobId}/markers/preview`, { rotate: dw.rotate });
        dw.imageUrl = result.image_url;
        dw.imageKind = "rotated";
      }
      dw.clicks = [];
      dw.boundaries = [];
      dw.features = [];
      dw.activeKind = null;
      dw.activeIdx = -1;
      dw.result = null;
      delete state.completed.draw;
      invalidateDownstream("draw");
      showImage();
      refreshChrome();
    } catch (error) {
      errEl().innerHTML = errorBanner(error);
    }
  });

  document.getElementById("dwRefM").addEventListener("input", (event) => {
    dw.refM = Number(event.target.value) || null;
    redraw();
  });

  document.getElementById("dwRecal").addEventListener("click", () => {
    dw.clicks = [];
    redraw();
  });

  document.getElementById("dwImgWrap")?.addEventListener("click", (event) => {
    const img = document.getElementById("dwImg");
    if (!img || event.target !== img) return;
    const rect = img.getBoundingClientRect();
    const x = Math.round((event.clientX - rect.left) * img.naturalWidth / rect.width);
    const y = Math.round((event.clientY - rect.top) * img.naturalHeight / rect.height);

    if (dw.clicks.length < 3) {
      dw.clicks.push([x, y]);
    } else if (calibReady() && dw.activeKind === "boundary") {
      const boundary = dw.boundaries[dw.activeIdx];
      if (boundary) boundary.points.push([x, y]);
    } else if (calibReady() && dw.activeKind === "feature") {
      const feature = dw.features[dw.activeIdx];
      if (feature && !feature.closed) feature.points.push([x, y]);
    }
    redraw();
  });

  document.getElementById("dwNewSurface").addEventListener("click", () => {
    let index = dw.boundaries.findIndex((boundary) => boundary.kind === "surface");
    if (index < 0) {
      dw.boundaries.push({ kind: "surface", name: null, points: [] });
      index = dw.boundaries.length - 1;
    }
    setActive("boundary", index);
  });

  document.getElementById("dwNewBottom").addEventListener("click", () => {
    const name = document.getElementById("dwName").value.trim();
    if (!name) {
      errEl().innerHTML = banner("err", `Enter a ${nameLabel} before creating the boundary.`);
      return;
    }
    if (dw.boundaries.some((boundary) => boundary.kind === "bottom" && boundary.name === name)) {
      errEl().innerHTML = banner("err", `A bottom boundary named ${esc(name)} already exists.`);
      return;
    }
    errEl().innerHTML = "";
    dw.boundaries.push({ kind: "bottom", name, points: [] });
    document.getElementById("dwName").value = "";
    setActive("boundary", dw.boundaries.length - 1);
  });

  document.getElementById("dwNewFeature").addEventListener("click", () => {
    const type = document.getElementById("dwFeatureType").value;
    const description = document.getElementById("dwFeatureDesc").value.trim();
    dw.features.push({ feature_type: type, description, points: [], closed: false });
    document.getElementById("dwFeatureDesc").value = "";
    setActive("feature", dw.features.length - 1);
  });

  document.getElementById("dwFinishFeature").addEventListener("click", () => {
    if (dw.activeKind !== "feature") {
      errEl().innerHTML = banner("err", "Select a feature polygon first.");
      return;
    }
    const feature = dw.features[dw.activeIdx];
    if (!feature || feature.points.length < 3) {
      errEl().innerHTML = banner("err", "A feature polygon needs at least three points.");
      return;
    }
    feature.closed = true;
    errEl().innerHTML = "";
    redraw();
  });

  document.getElementById("dwUndo").addEventListener("click", () => {
    const active = activeItem();
    if (!active) return;
    if (dw.activeKind === "feature") active.closed = false;
    active.points.pop();
    redraw();
  });

  document.getElementById("dwDelete").addEventListener("click", () => {
    if (dw.activeIdx < 0) return;
    if (dw.activeKind === "boundary") dw.boundaries.splice(dw.activeIdx, 1);
    if (dw.activeKind === "feature") dw.features.splice(dw.activeIdx, 1);
    dw.activeKind = null;
    dw.activeIdx = -1;
    redraw();
  });

  document.getElementById("dwTrench").addEventListener("change", (event) => {
    dw.trenchLabel = event.target.value;
  });
  document.getElementById("dwFace").addEventListener("change", (event) => {
    dw.faceLabel = event.target.value;
  });
  document.getElementById("dwSquareCm")?.addEventListener("change", (event) => {
    dw.squareCm = Number(event.target.value) || null;
  });

  document.getElementById("dwBuild").addEventListener("click", async () => {
    errEl().innerHTML = "";
    const validBoundaries = dw.boundaries.filter((boundary) => boundary.points.length >= 2);
    const validBottoms = validBoundaries.filter((boundary) => boundary.kind === "bottom");
    const invalidBottom = dw.boundaries.find((boundary) => boundary.kind === "bottom" && boundary.points.length < 2);
    const invalidFeature = dw.features.find((feature) => feature.points.length > 0 && feature.points.length < 3);

    if (!calibReady()) {
      errEl().innerHTML = banner("err", "Finish calibration: three clicks and a real reference width.");
      return;
    }
    if (!validBottoms.length) {
      errEl().innerHTML = banner("err", "Trace at least one bottom boundary with two or more points.");
      return;
    }
    if (invalidBottom) {
      errEl().innerHTML = banner("err", `Boundary ${esc(invalidBottom.name)} needs at least two points.`);
      return;
    }
    if (invalidFeature) {
      errEl().innerHTML = banner("err", "Delete or finish the incomplete feature polygon before building.");
      return;
    }

    const payload = {
      image: dw.imageKind,
      calibration: {
        origin_px: dw.clicks[0],
        ref_px: dw.clicks[1],
        lowest_px: dw.clicks[2],
        ref_meters: dw.refM,
      },
      boundaries: validBoundaries,
      features: dw.features
        .filter((feature) => feature.points.length >= 3)
        .map((feature) => ({
          feature_type: feature.feature_type,
          description: feature.description,
          points: feature.points,
        })),
      trenchLabel: dw.trenchLabel,
      faceLabel: dw.faceLabel,
    };

    if (isField) {
      payload.square_cm = dw.squareCm;
      payload.loci = validBottoms.map((boundary) => ({
        locusNumber: boundary.name,
        munsellRaw: (dw.lociMeta[boundary.name] || {}).a || null,
        description: (dw.lociMeta[boundary.name] || {}).b || null,
      }));
    } else {
      payload.layerInfo = Object.fromEntries(validBottoms.map((boundary) => [boundary.name, {
        inferredMaterial: (dw.layerMeta[boundary.name] || {}).a || null,
        description: (dw.layerMeta[boundary.name] || {}).b || null,
      }]));
    }

    try {
      const result = await apiJson(`/api/jobs/${state.jobId}/boundaries/manual`, payload);
      invalidateDownstream("draw");
      dw.result = result;
      state.extract.rawJson = result.raw_json;
      state.extract.warning = null;
      state.completed.draw = true;
      state.completed.extract = true;

      const resultHolder = document.getElementById("dwResult");
      resultHolder.innerHTML = "";
      (result.warnings || []).forEach((warning) => {
        resultHolder.innerHTML += banner("warn", esc(warning));
      });
      resultHolder.innerHTML += banner(
        "ok",
        `<strong>Manual extraction built.</strong> ${result.n_boundaries} traced boundaries and ` +
        `${result.n_features} feature polygons were converted at ${result.px_per_m} px/m. ` +
        `No CV or model altered the geometry.`
      );

      const tree = document.createElement("div");
      tree.className = "json-tree";
      tree.appendChild(renderJsonTree(JSON.parse(result.raw_json)));
      resultHolder.appendChild(tree);

      const nextRow = document.createElement("div");
      nextRow.className = "btn-row";
      const nextButton = document.createElement("button");
      nextButton.textContent = "Continue to Normalize →";
      nextButton.addEventListener("click", () => goToStep("normalize"));
      nextRow.appendChild(nextButton);
      resultHolder.appendChild(nextRow);
      refreshChrome();
    } catch (error) {
      errEl().innerHTML = errorBanner(error);
    }
  });

  if (dw.imageUrl) showImage();
}
