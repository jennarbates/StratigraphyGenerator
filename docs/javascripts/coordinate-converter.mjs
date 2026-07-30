/**
 * Live pixel -> face-local metres -> site coordinates converter.
 *
 * Progressive enhancement: the page already contains a static worked example.
 * This module prepends a form and a live result panel. With JavaScript off, the
 * worked example is still there and still teaches the same thing.
 *
 * The arithmetic mirrors two places in the application exactly, and must be
 * kept in step with them:
 *
 *   backend/routes/manual.py   Calibration.convert()  pixels -> local metres
 *   pipeline/convert_coords.py to_site()              local metres -> site XYZ
 */

const FIELDS = [
  { key: "ox", label: "Click 1 — x px", value: 220 },
  { key: "oy", label: "Click 1 — y px", value: 180 },
  { key: "rx", label: "Click 2 — x px", value: 1180 },
  { key: "ry", label: "Click 2 — y px", value: 196 },
  { key: "lx", label: "Click 3 — x px", value: 700 },
  { key: "ly", label: "Click 3 — y px", value: 900 },
  { key: "refM", label: "Real distance, clicks 1→2 (m)", value: 4 },
  { key: "px", label: "Point to convert — x px", value: 760 },
  { key: "py", label: "Point to convert — y px", value: 520 },
  { key: "originX", label: "originX (m)", value: 0 },
  { key: "originY", label: "originY (m)", value: 0 },
  { key: "surfaceZ", label: "surfaceZ (m)", value: 100 },
  { key: "bearing", label: "bearing_deg", value: 90 },
];

const GROUPS = [
  { title: "Calibration — the three clicks", keys: ["ox", "oy", "rx", "ry", "lx", "ly", "refM"] },
  { title: "The point you want to convert", keys: ["px", "py"] },
  { title: "Registration for this face", keys: ["originX", "originY", "surfaceZ", "bearing"] },
];

/** Local metres for one pixel point, or a reason it cannot be computed. */
export function toLocalMetres(v) {
  const dx = v.rx - v.ox;
  const dy = v.ry - v.oy;
  const span = Math.hypot(dx, dy);

  if (span < 2) {
    return { error: "Clicks 1 and 2 are too close together to set a scale." };
  }
  if (!(v.refM > 0)) {
    return { error: "The real distance between clicks 1 and 2 must be above zero." };
  }

  const ux = dx / span;
  const uy = dy / span;

  // One of the two perpendiculars points toward the lowest click; that is +depth.
  let vx = -uy;
  let vy = ux;
  if ((v.lx - v.ox) * vx + (v.ly - v.oy) * vy < 0) {
    vx = -vx;
    vy = -vy;
  }

  const pxPerM = span / v.refM;
  const qx = v.px - v.ox;
  const qy = v.py - v.oy;

  return {
    xMeters: (qx * ux + qy * uy) / pxPerM,
    depthMeters: (qx * vx + qy * vy) / pxPerM,
    pxPerM,
  };
}

/** Site coordinates for a face-local point. */
export function toSite(xMeters, depthMeters, v) {
  const theta = (v.bearing * Math.PI) / 180;
  return {
    X: v.originX + xMeters * Math.sin(theta),
    Y: v.originY + xMeters * Math.cos(theta),
    Z: v.surfaceZ - depthMeters,
  };
}

const round4 = (n) => Math.round(n * 10000) / 10000;

function readValues(root) {
  const values = {};
  for (const field of FIELDS) {
    const input = root.querySelector(`[name="${field.key}"]`);
    values[field.key] = Number(input.value);
  }
  return values;
}

function render(root, output) {
  const values = readValues(root);

  if (Object.values(values).some((n) => !Number.isFinite(n))) {
    output.innerHTML = '<p class="pc-error">Every field needs a number.</p>';
    return;
  }

  const local = toLocalMetres(values);
  if (local.error) {
    output.innerHTML = `<p class="pc-error">${local.error}</p>`;
    return;
  }

  const site = toSite(local.xMeters, local.depthMeters, values);
  output.innerHTML = `
    <dl class="pc-result">
      <div><dt>Pixel</dt><dd>(${values.px}, ${values.py})</dd></div>
      <div><dt>Face-local metres</dt>
        <dd>x = ${round4(local.xMeters)} m, depth = ${round4(local.depthMeters)} m</dd></div>
      <div><dt>Site coordinates</dt>
        <dd>X = ${round4(site.X)}, Y = ${round4(site.Y)}, Z = ${round4(site.Z)}</dd></div>
    </dl>
    <p class="pc-note">Scale: ${round4(local.pxPerM)} pixels per metre.</p>`;
}

function build(root) {
  const form = document.createElement("form");
  form.className = "pc-form";
  form.setAttribute("aria-label", "Coordinate converter");
  form.addEventListener("submit", (event) => event.preventDefault());

  for (const group of GROUPS) {
    const fieldset = document.createElement("fieldset");
    const legend = document.createElement("legend");
    legend.textContent = group.title;
    fieldset.appendChild(legend);

    for (const key of group.keys) {
      const field = FIELDS.find((f) => f.key === key);
      const label = document.createElement("label");
      label.textContent = field.label;
      const input = document.createElement("input");
      input.type = "number";
      input.step = "any";
      input.name = field.key;
      input.value = String(field.value);
      label.appendChild(input);
      fieldset.appendChild(label);
    }
    form.appendChild(fieldset);
  }

  const output = document.createElement("div");
  output.className = "pc-output";
  output.setAttribute("role", "status");
  output.setAttribute("aria-live", "polite");

  form.addEventListener("input", () => render(root, output));

  root.prepend(output);
  root.prepend(form);
  render(root, output);
}

export function init(doc = document) {
  for (const root of doc.querySelectorAll("[data-pc-converter]")) {
    if (root.dataset.pcReady) continue;
    root.dataset.pcReady = "true";
    build(root);
  }
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => init());
  } else {
    init();
  }
}
