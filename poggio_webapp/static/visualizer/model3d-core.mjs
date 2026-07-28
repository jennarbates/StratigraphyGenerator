const MODEL_KIND = "gempy-surface-model";
const SUPPORTED_SCHEMA_VERSION = 1;
const MIN_OPACITY = 0.1;
const MAX_OPACITY = 1;
const DEFAULT_OPACITY = 0.72;
const CAMERA_VIEW_NAMES = Object.freeze([
  "isometric",
  "top",
  "front",
  "side",
]);

// A fixed palette keeps the fallback independent of CSS, Three.js, and the DOM.
const SURFACE_COLORS = Object.freeze([
  "#4477aa",
  "#ee6677",
  "#228833",
  "#ccbb44",
  "#66ccee",
  "#aa3377",
  "#bbbbbb",
  "#ee8866",
  "#44aa99",
  "#997700",
  "#6699cc",
  "#aa4466",
]);

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function validatedExtent(extent) {
  if (
    !Array.isArray(extent)
    || extent.length !== 6
    || !extent.every((value) => typeof value === "number" && Number.isFinite(value))
  ) {
    throw new TypeError("model3d.extent must contain six finite numbers");
  }

  const axisNames = ["X", "Y", "Z"];
  for (let axis = 0; axis < 3; axis += 1) {
    if (extent[axis * 2] >= extent[(axis * 2) + 1]) {
      throw new TypeError(
        `model3d.extent ${axisNames[axis]} minimum must be less than maximum`,
      );
    }
  }

  return extent.slice();
}

function validatedResolution(resolution) {
  if (
    !Array.isArray(resolution)
    || resolution.length !== 3
    || !resolution.every((value) => Number.isInteger(value) && value > 0)
  ) {
    throw new TypeError("model3d.resolution must contain three positive integers");
  }

  return resolution.slice();
}

function validatedNonEmptyString(value, path) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new TypeError(`${path} must be a non-empty string`);
  }
  return value;
}

function validatedStringArray(value, path, { nonEmpty = false } = {}) {
  if (!Array.isArray(value)) {
    throw new TypeError(`${path} must be an array`);
  }

  return value.map((item, index) => {
    if (typeof item !== "string" || (nonEmpty && item.trim() === "")) {
      const requirement = nonEmpty ? "a non-empty string" : "a string";
      throw new TypeError(`${path}[${index}] must be ${requirement}`);
    }
    return item;
  });
}

function validatedJobUrl(value, path) {
  const expected = `${path} must be a same-origin /api/jobs/ URL`;
  if (
    typeof value !== "string"
    || value.trim() !== value
    || !value.startsWith("/api/jobs/")
    || /[\u0000-\u0020\\]/u.test(value)
  ) {
    throw new TypeError(expected);
  }

  let parsed;
  try {
    parsed = new URL(value, "https://model3d.invalid");
  } catch {
    throw new TypeError(expected);
  }

  if (
    parsed.origin !== "https://model3d.invalid"
    || !parsed.pathname.startsWith("/api/jobs/")
  ) {
    throw new TypeError(expected);
  }

  return value;
}

function validatedCoordinateSystem(value) {
  if (!isObject(value)) {
    throw new TypeError("model3d.coordinate_system must be an object");
  }

  const units = validatedNonEmptyString(
    value.units,
    "model3d.coordinate_system.units",
  );
  if (value.up_axis !== "Z") {
    throw new TypeError('model3d.coordinate_system.up_axis must be "Z"');
  }

  return {
    units,
    up_axis: "Z",
  };
}

function validatedSurfaces(value) {
  if (!Array.isArray(value)) {
    throw new TypeError("model3d.surfaces must be an array");
  }

  const names = new Set();
  return value.map((surface, index) => {
    const path = `model3d.surfaces[${index}]`;
    if (!isObject(surface)) {
      throw new TypeError(`${path} must be an object`);
    }

    const name = validatedNonEmptyString(surface.name, `${path}.name`);
    if (names.has(name)) {
      throw new TypeError(`model3d contains duplicate surface name "${name}"`);
    }
    names.add(name);

    return {
      name,
      url: validatedJobUrl(surface.url, `${path}.url`),
    };
  });
}

/**
 * Validate an API model3d payload and return a detached, normalized copy.
 *
 * Optional `lith_block_url` is retained for later volume support, but this
 * surface-only module never fetches it.
 */
export function validateModel3d(raw) {
  if (!isObject(raw)) {
    throw new TypeError("model3d must be an object");
  }
  if (raw.schema_version !== SUPPORTED_SCHEMA_VERSION) {
    throw new TypeError("model3d.schema_version must be 1");
  }
  if (raw.kind !== MODEL_KIND) {
    throw new TypeError(`model3d.kind must be "${MODEL_KIND}"`);
  }

  const normalized = {
    schema_version: SUPPORTED_SCHEMA_VERSION,
    kind: MODEL_KIND,
    coordinate_system: validatedCoordinateSystem(raw.coordinate_system),
    extent: validatedExtent(raw.extent),
    resolution: validatedResolution(raw.resolution),
    series_order: validatedStringArray(
      raw.series_order,
      "model3d.series_order",
      { nonEmpty: true },
    ),
    single_face_note: raw.single_face_note ?? null,
    surfaces: validatedSurfaces(raw.surfaces),
    warnings: raw.warnings === undefined
      ? []
      : validatedStringArray(raw.warnings, "model3d.warnings"),
  };

  if (
    normalized.single_face_note !== null
    && typeof normalized.single_face_note !== "string"
  ) {
    throw new TypeError("model3d.single_face_note must be null or a string");
  }

  if (raw.lith_block_url !== undefined && raw.lith_block_url !== null) {
    normalized.lith_block_url = validatedJobUrl(
      raw.lith_block_url,
      "model3d.lith_block_url",
    );
  }

  return normalized;
}

export function extentCenter(extent) {
  const value = validatedExtent(extent);
  return [
    (value[0] + value[1]) / 2,
    (value[2] + value[3]) / 2,
    (value[4] + value[5]) / 2,
  ];
}

export function extentSize(extent) {
  const value = validatedExtent(extent);
  return [
    value[1] - value[0],
    value[3] - value[2],
    value[5] - value[4],
  ];
}

/**
 * Return a renderer-neutral camera description.
 *
 * `position` and `target` are world-space XYZ coordinates, `up` documents
 * the GemPy Z-up convention, and `distance` is the eye-to-target distance.
 */
export function cameraPreset(extent, viewName) {
  const target = extentCenter(extent);
  const size = extentSize(extent);
  const distance = Math.hypot(...size) * 1.5;
  let offset;

  switch (viewName) {
    case "top":
      offset = [0, 0, distance];
      break;
    case "front":
      offset = [0, distance, 0];
      break;
    case "side":
      offset = [distance, 0, 0];
      break;
    case "isometric": {
      const component = distance / Math.sqrt(3);
      offset = [component, component, component];
      break;
    }
    default:
      throw new TypeError(
        'viewName must be one of "top", "front", "side", or "isometric"',
      );
  }

  return {
    position: target.map((value, index) => value + offset[index]),
    target,
    up: [0, 0, 1],
    distance,
  };
}

export function deterministicSurfaceColor(name) {
  validatedNonEmptyString(name, "surface name");
  let hash = 5381;
  for (const character of name) {
    hash = ((hash * 33) ^ character.codePointAt(0)) >>> 0;
  }
  return SURFACE_COLORS[hash % SURFACE_COLORS.length];
}

/**
 * Build initial UI state in manifest surface order.
 *
 * Callers may pass `colorFor(name, index)`; otherwise a stable hash selects
 * from the module's fixed color-blind-friendly palette.
 */
export function surfaceControlModel(
  model3d,
  colorFor = deterministicSurfaceColor,
) {
  const normalized = validateModel3d(model3d);
  if (typeof colorFor !== "function") {
    throw new TypeError("colorFor must be a function");
  }

  return normalized.surfaces.map((surface, index) => ({
    name: surface.name,
    url: surface.url,
    color: colorFor(surface.name, index),
    visible: true,
  }));
}

export function clampOpacity(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new TypeError("opacity must be a finite number");
  }
  return Math.min(MAX_OPACITY, Math.max(MIN_OPACITY, value));
}

/**
 * Return the complete initial state for visualizer-owned 3D controls.
 */
export function model3dControlState(
  model3d,
  colorFor = deterministicSurfaceColor,
) {
  return {
    surfaces: surfaceControlModel(model3d, colorFor),
    opacity: DEFAULT_OPACITY,
    wireframe: false,
    helpersVisible: true,
    cameraView: "isometric",
  };
}

/**
 * Create a detached visibility state without reordering model surfaces.
 */
export function setAllSurfaceVisibility(surfaces, visible) {
  if (!Array.isArray(surfaces)) {
    throw new TypeError("surfaces must be an array");
  }
  if (typeof visible !== "boolean") {
    throw new TypeError("visible must be a boolean");
  }

  return surfaces.map((surface, index) => {
    if (!isObject(surface) || typeof surface.name !== "string") {
      throw new TypeError(`surfaces[${index}] must be a surface control`);
    }
    return {
      ...surface,
      visible,
    };
  });
}

/**
 * Return renderer-neutral camera button state in visible control order.
 *
 * Reset is an action, so it does not expose a pressed state. The four view
 * choices form the persistent camera selection.
 */
export function cameraControlModel(activeView = "isometric") {
  if (!CAMERA_VIEW_NAMES.includes(activeView)) {
    throw new TypeError(
      'active camera view must be "isometric", "top", "front", or "side"',
    );
  }

  return [
    {
      id: "reset",
      label: "Reset",
      command: "reset",
      view: "isometric",
      pressed: null,
    },
    {
      id: "top",
      label: "Top",
      command: "view",
      view: "top",
      pressed: activeView === "top",
    },
    {
      id: "front",
      label: "Front",
      command: "view",
      view: "front",
      pressed: activeView === "front",
    },
    {
      id: "side",
      label: "Side",
      command: "view",
      view: "side",
      pressed: activeView === "side",
    },
    {
      id: "isometric",
      label: "3D",
      command: "view",
      view: "isometric",
      pressed: activeView === "isometric",
    },
  ];
}

function normalizedCount(value, name, fallback = 0) {
  const count = value ?? fallback;
  if (!Number.isInteger(count) || count < 0) {
    throw new TypeError(`${name} must be a non-negative integer`);
  }
  return count;
}

function failureNames(failures) {
  if (failures === undefined) return [];
  if (!Array.isArray(failures)) {
    throw new TypeError("failures must be an array");
  }
  return failures.map((failure, index) => {
    if (!isObject(failure)) {
      throw new TypeError(`failures[${index}] must be an object`);
    }
    return validatedNonEmptyString(failure.name, `failures[${index}].name`);
  });
}

function failureWarning(names) {
  if (!names.length) return "";
  const noun = names.length === 1 ? "surface" : "surfaces";
  const list = names.join(", ");
  const ending = /[.!?]$/u.test(list) ? "" : ".";
  return `Could not load ${names.length} ${noun}: ${list}${ending}`;
}

/**
 * Convert renderer progress into concise text for the two aria-live regions.
 */
export function modelLoadStatusSummary(detail) {
  if (!isObject(detail)) {
    throw new TypeError("load detail must be an object");
  }

  const total = normalizedCount(detail.total, "total");
  const loaded = normalizedCount(detail.loaded, "loaded");
  const failed = normalizedCount(detail.failed, "failed");
  const names = failureNames(detail.failures);

  if (detail.phase === "loading") {
    const settled = normalizedCount(
      detail.settled,
      "settled",
      loaded + failed,
    );
    return {
      status: `Loading ${Math.min(settled, total)} of ${total} surfaces…`,
      warning: "",
      failedNames: [],
      recoverable: false,
    };
  }

  if (detail.phase === "complete") {
    return {
      status: `Loaded ${loaded} of ${total} surfaces.`,
      warning: failureWarning(names),
      failedNames: names,
      recoverable: loaded === 0,
    };
  }

  if (detail.phase === "error") {
    return {
      status: loaded > 0
        ? `Loaded ${loaded} of ${total} surfaces.`
        : "No 3D surfaces could be displayed.",
      warning: failureWarning(names)
        || "The 3D viewer could not start. Your 2D data and job downloads remain available.",
      failedNames: names,
      recoverable: true,
    };
  }

  throw new TypeError('load detail phase must be "loading", "complete", or "error"');
}
