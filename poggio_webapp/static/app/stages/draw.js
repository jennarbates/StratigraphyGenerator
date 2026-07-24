import { apiJson } from "../core/api.js";
import { goToStep, refreshChrome } from "../core/navigation.js";
import { STRATA, invalidateDownstream, state } from "../core/state.js";
import { pointInsideBand } from "../../boundary-label.js";
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
      <div class="stage-kicker">Step 3 of 8</div>
      <h2>Trace the layers</h2>
      <p class="lede">You’ll click directly on the drawing to show where each
      soil layer begins and ends. Nothing has to be perfect—you can undo any
      misplaced point.</p>

      <div class="plain-note">
        <span class="note-icon" aria-hidden="true">i</span>
        <span><strong>This step has four short parts.</strong><br>
        Set the scale, trace the lines, optionally mark features, then add names.</span>
      </div>

      ${isPdf ? `
        <p class="hint">Your PDF has been turned into an image that you can click.</p>
        <div class="btn-row">
          <button class="secondary" id="dwShow" ${state.preprocess.cleanUrl ? "" : "disabled"}>
            Open the drawing and start
          </button>
        </div>
      ` : `
        <label class="field">
          <span class="label-text">Is the drawing already upright?</span>
          <select id="dwRotate">
            <option value="0">Yes, it is upright</option>
            <option value="90">Turn it 90° to the right</option>
            <option value="180">Turn it upside down</option>
            <option value="270">Turn it 90° to the left</option>
          </select>
        </label>
        <div class="btn-row">
          <button id="dwShow">Open the drawing and start</button>
        </div>
      `}

      <div id="dwWrap" style="display:none">
        <section class="drawing-section">
        <h3><span class="section-label">A</span> Set the scale</h3>
        <p class="hint">Click three points on the drawing in the order shown
        below. This tells the app its size and which way is down.</p>
        <p class="calibration-prompt" id="dwHint" aria-live="polite"></p>
        <div class="btn-row">
          <button class="secondary" id="dwRecal">Start these three clicks again</button>
        </div>
        <label class="field">
          <span class="label-text">Distance between your first two clicks, in metres</span>
          <input type="number" id="dwRefM" step="0.01" min="0.01"
                 placeholder="For example: 4" value="${dw.refM ?? ""}">
          <span class="hint">Look for a measurement or scale bar on the sheet.
          If you are unsure, ask the person responsible for the trench record.</span>
        </label>
        </section>

        <div id="dwTools" style="display:none">
          <section class="drawing-section">
          <h3><span class="section-label">B</span> Trace the soil lines</h3>
          ${isField ? `
            <p class="hint">A locus is named by its <strong>top</strong> line on a field sheet.
            The next locus top also closes the locus above it.</p>
            <ol class="task-list">
              <li><span class="task-number">1</span><span>Type the first locus number, choose
              <strong>Start the top of this locus</strong>, then click along that line
              from left to right.</span></li>
              <li><span class="task-number">2</span><span>Repeat for the top of every
              deeper locus.</span></li>
              <li><span class="task-number">3</span><span>Choose
              <strong>Start the final bottom line</strong> and trace the line below
              the deepest locus.</span></li>
            </ol>
            <div class="btn-row">
              <input id="dwName" aria-label="${nameLabel}" placeholder="${nameLabel}" style="width:170px">
              <button class="secondary" id="dwNewTop">Start the top of this locus</button>
              <button class="secondary" id="dwNewBase">Start the final bottom line</button>
            </div>
          ` : `
            <ol class="task-list">
              <li><span class="task-number">1</span><span>Choose <strong>Start the surface line</strong>,
              then click along the top of the drawing from left to right.</span></li>
              <li><span class="task-number">2</span><span>Type the ${nameLabel}, choose
              <strong>Start this lower line</strong>, then click along that line.</span></li>
              <li><span class="task-number">3</span><span>Repeat for every lower soil line.</span></li>
            </ol>
            <div class="btn-row">
              <button class="secondary" id="dwNewSurface">Start the surface line</button>
              <input id="dwName" aria-label="${nameLabel}" placeholder="${nameLabel}" style="width:170px">
              <button class="secondary" id="dwNewBottom">Start this lower line</button>
            </div>
          `}
          <div class="btn-row">
            <button class="secondary" id="dwUndo">Undo my last point</button>
            <button class="secondary" id="dwDelete">Delete the selected line or shape</button>
            <span id="dwActive" class="hint"></span>
          </div>
          <div id="dwBoundaryChips" class="btn-row" style="flex-wrap:wrap"></div>
          </section>

          <details class="optional-section">
          <summary>C · Mark rocks, cuts, or other features (optional)</summary>
          <div class="details-body">
          <p class="hint">Choose what you found, start a shape, then click around
          its outside edge. Choose “Finish this shape” when you return to the start.</p>
          <div class="btn-row">
            <select id="dwFeatureType" aria-label="Type of feature" style="max-width:210px">
              ${FEATURE_TYPES.map((type) => `<option>${type}</option>`).join("")}
            </select>
            <input id="dwFeatureDesc" aria-label="Optional feature description"
                   placeholder="Short note (optional)" style="min-width:220px">
            <button class="secondary" id="dwNewFeature">Start a new shape</button>
            <button class="secondary" id="dwFinishFeature">Finish this shape</button>
          </div>
          <div id="dwFeatureChips" class="btn-row" style="flex-wrap:wrap"></div>
          <div id="dwFeatureMeta"></div>
          </div>
          </details>
        </div>

        <div id="dwImgWrap" class="image-workspace" style="position:relative;display:inline-block;max-width:100%;margin-top:10px">
          <img id="dwImg" alt="Trench drawing to trace" style="max-width:100%;display:block;cursor:crosshair">
          <svg id="dwSvg" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none"></svg>
        </div>
      </div>

      <div id="dwMetaWrap" style="display:none">
        <section class="drawing-section">
        <h3><span class="section-label">D</span> Add names and save</h3>
        <p class="hint">Copy these names from the drawing. Leave an optional
        description blank if the sheet does not provide one.</p>
        <div class="field-grid">
          <label class="field">
            <span class="label-text">Trench name</span>
            <input id="dwTrench" placeholder="For example: T104" value="${esc(dw.trenchLabel)}">
          </label>
          <label class="field">
            <span class="label-text">Side of the trench</span>
            <input id="dwFace" placeholder="For example: south baulk" value="${esc(dw.faceLabel)}">
          </label>
          ${isField ? `<label class="field">
            <span class="label-text">Large grid-square size, in centimetres</span>
            <input type="number" id="dwSquareCm" step="0.5" min="0.1"
              placeholder="For example: 20" value="${dw.squareCm ?? ""}">
          </label>` : ""}
        </div>
        <div id="dwMeta"></div>
        <div class="btn-row">
          <button id="dwBuild">Save my traced drawing</button>
        </div>
        </section>
      </div>

      <div id="dwResult"></div>
      <div id="dwError"></div>
    </div>
  `;

  const CAL_LABELS = [
    "Click 1 of 3: choose the top-left reference point on the drawing.",
    "Click 2 of 3: choose the matching top-right reference point.",
    "Click 3 of 3: choose the lowest point anywhere on the trench drawing.",
    "All three points are set. Enter the distance below to continue.",
  ];
  const CAL_COLORS = ["#c0269a", "#d17a1f", "#2a7ab5"];
  const errEl = () => document.getElementById("dwError");
  const calibReady = () => dw.clicks.length >= 3 && Number(dw.refM) > 0;
  const namedLines = () => dw.boundaries.filter(
    (boundary) => boundary.kind === (isField ? "top" : "bottom")
  );

  function boundaryLabel(boundary) {
    if (isField) {
      if (boundary.kind === "top") return `top of locus ${boundary.name}`;
      if (boundary.kind === "base") return "final bottom line";
    }
    if (boundary.kind === "surface") return "surface line";
    return `${isField ? "locus" : "layer"} ${boundary.name}`;
  }

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
      const label = boundaryLabel(boundary);
      button.textContent = `${label} · ${boundary.points.length} point${boundary.points.length === 1 ? "" : "s"}`;
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
      button.textContent = `Shape ${index + 1}: ${feature.feature_type} · ${feature.points.length} points · ${status}`;
      button.addEventListener("click", () => setActive("feature", index));
      holder.appendChild(button);
    });
  }

  function renderFeatureMeta() {
    const holder = document.getElementById("dwFeatureMeta");
    holder.innerHTML = dw.features.map((feature, index) => `
      <div class="btn-row" style="align-items:center;gap:8px" data-feature-index="${index}">
        <span class="hint" style="min-width:28px">F${index + 1}</span>
        <select data-role="type" aria-label="Type for shape ${index + 1}">
          ${FEATURE_TYPES.map((type) => `<option ${type === feature.feature_type ? "selected" : ""}>${type}</option>`).join("")}
        </select>
        <input data-role="description" aria-label="Description for shape ${index + 1}" placeholder="Short note (optional)"
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
    holder.innerHTML = namedLines().map((boundary) => `
      <div class="btn-row" style="align-items:center;gap:8px" data-name="${esc(boundary.name)}">
        <span class="hint" style="min-width:95px">${isField ? "locus" : "layer"} ${esc(boundary.name)}</span>
        <input data-role="a" aria-label="${isField ? "Munsell colour" : "Material"} for ${esc(boundary.name)}"
               placeholder="${isField ? "Soil colour (for example: 10YR 5/3)" : "Material (for example: clay fill)"}"
               value="${esc((store[boundary.name] || {}).a || "")}">
        <input data-role="b" aria-label="Optional description for ${esc(boundary.name)}"
               placeholder="Short note (optional)" style="flex:1;min-width:180px"
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
      const color = boundary.kind === "surface" || boundary.kind === "base"
        ? "#2a7ab5"
        : STRATA[index % STRATA.length];
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

    if (isField) {
      const base = dw.boundaries.find(
        (boundary) => boundary.kind === "base" && boundary.points.length >= 2
      );
      const tops = dw.boundaries
        .filter((boundary) => boundary.kind === "top" && boundary.points.length >= 2)
        .sort((left, right) => {
          const averageY = (boundary) => (
            boundary.points.reduce((sum, point) => sum + point[1], 0)
            / boundary.points.length
          );
          return averageY(left) - averageY(right);
        });

      tops.forEach((top, index) => {
        const bottom = tops[index + 1] || base;
        if (!bottom) return;
        const labelPoint = pointInsideBand(
          top.points,
          bottom.points,
          (point) => point[0],
          (point) => point[1],
        );
        if (!labelPoint) return;

        const label = `Locus ${top.name}`;
        const color = STRATA[dw.boundaries.indexOf(top) % STRATA.length];
        output += `<text x="${labelPoint.x}" y="${labelPoint.y}"
          fill="${color}" font-size="${radius * 3.1}" font-family="sans-serif"
          font-weight="700" text-anchor="middle" dominant-baseline="middle"
          paint-order="stroke fill" stroke="rgba(255,255,255,.94)"
          stroke-width="${radius * 1.25}" stroke-linejoin="round">${esc(label)}</text>`;
      });
    }

    svg.innerHTML = output;
    document.getElementById("dwHint").textContent = CAL_LABELS[Math.min(dw.clicks.length, 3)];
    document.getElementById("dwTools").style.display = calibReady() ? "block" : "none";
    document.getElementById("dwMetaWrap").style.display = calibReady() && namedLines().length ? "block" : "none";

    const active = activeItem();
    document.getElementById("dwActive").textContent = active
      ? `Now adding points to: ${dw.activeKind === "boundary" ? boundaryLabel(active) : active.feature_type}`
      : "Choose a line or shape before clicking the drawing.";

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

  document.getElementById("dwNewSurface")?.addEventListener("click", () => {
    let index = dw.boundaries.findIndex((boundary) => boundary.kind === "surface");
    if (index < 0) {
      dw.boundaries.push({ kind: "surface", name: null, points: [] });
      index = dw.boundaries.length - 1;
    }
    setActive("boundary", index);
  });

  function startNamedLine(kind, actionLabel) {
    const name = document.getElementById("dwName").value.trim();
    if (!name) {
      errEl().innerHTML = banner("err", `Type a ${nameLabel}, then choose “${actionLabel}.”`);
      return;
    }
    if (dw.boundaries.some((boundary) => boundary.kind === kind && boundary.name === name)) {
      errEl().innerHTML = banner("err", `${esc(name)} has already been added. Use a different name or select the existing line.`);
      return;
    }
    errEl().innerHTML = "";
    dw.boundaries.push({ kind, name, points: [] });
    document.getElementById("dwName").value = "";
    setActive("boundary", dw.boundaries.length - 1);
  }

  document.getElementById("dwNewBottom")?.addEventListener("click", () => {
    startNamedLine("bottom", "Start this lower line");
  });

  document.getElementById("dwNewTop")?.addEventListener("click", () => {
    startNamedLine("top", "Start the top of this locus");
  });

  document.getElementById("dwNewBase")?.addEventListener("click", () => {
    let index = dw.boundaries.findIndex((boundary) => boundary.kind === "base");
    if (index < 0) {
      dw.boundaries.push({ kind: "base", name: null, points: [] });
      index = dw.boundaries.length - 1;
    }
    errEl().innerHTML = "";
    setActive("boundary", index);
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
      errEl().innerHTML = banner("err", "Start or select a shape before finishing it.");
      return;
    }
    const feature = dw.features[dw.activeIdx];
    if (!feature || feature.points.length < 3) {
      errEl().innerHTML = banner("err", "Click at least three points around the feature before finishing the shape.");
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
    const namedKind = isField ? "top" : "bottom";
    const validNamedLines = validBoundaries.filter((boundary) => boundary.kind === namedKind);
    const invalidNamedLine = dw.boundaries.find(
      (boundary) => boundary.kind === namedKind && boundary.points.length < 2
    );
    const validBase = validBoundaries.find((boundary) => boundary.kind === "base");
    const invalidBase = dw.boundaries.find(
      (boundary) => boundary.kind === "base" && boundary.points.length < 2
    );
    const invalidFeature = dw.features.find((feature) => feature.points.length > 0 && feature.points.length < 3);

    if (!calibReady()) {
      errEl().innerHTML = banner("err", "Complete all three scale clicks and enter the distance between the first two.");
      return;
    }
    if (!validNamedLines.length) {
      errEl().innerHTML = banner(
        "err",
        isField
          ? "Add the top of at least one locus with two or more clicks."
          : "Add at least one lower soil line with two or more points."
      );
      return;
    }
    if (invalidNamedLine) {
      errEl().innerHTML = banner("err", `${esc(invalidNamedLine.name)} needs at least two clicks on the drawing.`);
      return;
    }
    if (isField && !validBase) {
      errEl().innerHTML = banner("err", "Trace the final bottom line below the deepest locus.");
      return;
    }
    if (invalidBase) {
      errEl().innerHTML = banner("err", "The final bottom line needs at least two clicks on the drawing.");
      return;
    }
    if (invalidFeature) {
      errEl().innerHTML = banner("err", "Finish the incomplete feature shape, or delete it, before saving.");
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
      payload.loci = validNamedLines.map((boundary) => ({
        locusNumber: boundary.name,
        munsellRaw: (dw.lociMeta[boundary.name] || {}).a || null,
        description: (dw.lociMeta[boundary.name] || {}).b || null,
      }));
    } else {
      payload.layerInfo = Object.fromEntries(validNamedLines.map((boundary) => [boundary.name, {
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
        `Your traced drawing has been saved with ${result.n_boundaries} soil line${result.n_boundaries === 1 ? "" : "s"} ` +
        `and ${result.n_features} feature shape${result.n_features === 1 ? "" : "s"}.`
      );

      const technical = document.createElement("details");
      technical.className = "technical-details";
      const summary = document.createElement("summary");
      summary.textContent = "Technical data";
      technical.appendChild(summary);
      const tree = document.createElement("div");
      tree.className = "json-tree";
      tree.appendChild(renderJsonTree(JSON.parse(result.raw_json)));
      technical.appendChild(tree);
      resultHolder.appendChild(technical);

      const nextRow = document.createElement("div");
      nextRow.className = "btn-row";
      const nextButton = document.createElement("button");
      nextButton.textContent = "Continue to clean up the data →";
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
