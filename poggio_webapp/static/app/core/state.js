export const STRATA = ["#9c6b3e", "#b98a4f", "#8a8c53", "#6c7a80", "#a4522f", "#5b7a9c", "#8a5ba0"];

export const STEPS = [
  { id: "scan",       title: "Scan",          sub: "01_scans",              num: "01" },
  { id: "preprocess", title: "Preprocess",    sub: "02_preprocess",         num: "02" },
  { id: "draw",       title: "Trace drawing", sub: "03_extraction",         num: "03" },
  { id: "extract",    title: "AI fallback",   sub: "03_extraction",         num: "03" },
  { id: "normalize",  title: "Normalize",     sub: "04_normalize_validate", num: "04" },
  { id: "validate",   title: "Validate",      sub: "04_normalize_validate", num: "04" },
  { id: "convert",    title: "Convert coords", sub: "05_convert_coords",    num: "05" },
  { id: "gempy",      title: "3D model",      sub: "06_gempy_model",        num: "06" },
  { id: "visualize",  title: "Visualize",     sub: "07_visualizer",         num: "07" },
];

export const state = {
  jobId: null,
  sheetType: "illustrator",
  current: "scan",
  completed: {},
  scan: { url: null, isPdf: false, filename: null, dims: null, recommendedUpscale: null },
  preprocess: { cleanUrl: null },
  draw: {
    rotate: 0,
    imageUrl: null,
    imageKind: null,
    clicks: [],
    refM: null,
    boundaries: [],
    features: [],
    activeKind: null,
    activeIdx: -1,
    trenchLabel: "",
    faceLabel: "",
    squareCm: null,
    lociMeta: {},
    layerMeta: {},
    result: null,
  },
  extract: { rawJson: null, warning: null },
  normalize: { data: null, log: [] },
  validate: { report: null },
  convert: { gridConfig: null, result: null },
  gempy: { result: null },
  apiKey: "",
};

export const PREREQS = {
  scan: [],
  preprocess: ["scan"],
  draw: ["scan"],
  extract: ["scan"],
  normalize: ["extract"],
  validate: ["extract"],
  convert: ["normalize", "validate"],
  gempy: ["convert"],
  visualize: ["extract"],
};

const FRESH_STATE = {
  preprocess: () => ({ cleanUrl: null }),
  draw: () => ({
    rotate: 0,
    imageUrl: null,
    imageKind: null,
    clicks: [],
    refM: null,
    boundaries: [],
    features: [],
    activeKind: null,
    activeIdx: -1,
    trenchLabel: "",
    faceLabel: "",
    squareCm: null,
    lociMeta: {},
    layerMeta: {},
    result: null,
  }),
  extract: () => ({ rawJson: null, warning: null }),
  normalize: () => ({ data: null, log: [] }),
  validate: () => ({ report: null }),
  convert: () => ({ gridConfig: null, result: null }),
  gempy: () => ({ result: null }),
};

export function invalidateDownstream(stepId) {
  const EXTRA_STALE_EDGES = {
    validate: ["normalize"],
    extract: ["draw"],
  };
  const depsOf = (id) => (PREREQS[id] || []).concat(EXTRA_STALE_EDGES[id] || []);
  const stale = new Set();
  let grew = true;

  while (grew) {
    grew = false;
    for (const id of Object.keys(PREREQS)) {
      if (stale.has(id)) continue;
      const reqs = depsOf(id);
      if (reqs.includes(stepId) || reqs.some((required) => stale.has(required))) {
        stale.add(id);
        grew = true;
      }
    }
  }

  stale.forEach((id) => {
    delete state.completed[id];
    if (FRESH_STATE[id]) state[id] = FRESH_STATE[id]();
  });
  return stale;
}
