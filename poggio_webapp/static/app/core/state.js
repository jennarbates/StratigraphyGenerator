export const STRATA = ["#9c6b3e", "#b98a4f", "#8a8c53", "#6c7a80", "#a4522f", "#5b7a9c", "#8a5ba0"];

export const STEPS = [
  { id: "scan",       title: "Add your drawing",        sub: "Choose a file to begin",              num: "1" },
  { id: "preprocess", title: "Prepare the image",       sub: "Make lines easier to see",             num: "2" },
  { id: "draw",       title: "Trace the layers",        sub: "Click along the drawing",              num: "3" },
  { id: "extract",    title: "Other ways to add data",  sub: "Import a file or use automatic reading", num: "OR", optional: true },
  { id: "normalize",  title: "Clean up the data",       sub: "Fix small formatting issues",          num: "4" },
  { id: "validate",   title: "Check for problems",      sub: "Make sure the result looks safe",      num: "5" },
  { id: "convert",    title: "Place it on the site",    sub: "Add surveyed coordinates",             num: "6" },
  { id: "gempy",      title: "Create the 3D model",     sub: "Build the final model",                 num: "7" },
  { id: "visualize",  title: "View and download",       sub: "Open your finished work",              num: "8" },
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
