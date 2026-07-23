export const STRATA = ["#9c6b3e", "#b98a4f", "#8a8c53", "#6c7a80", "#a4522f", "#5b7a9c", "#8a5ba0"];

export const STEPS = [
  { id: "scan",       title: "Scan",        sub: "01_scans",              num: "01" },
  { id: "preprocess", title: "Preprocess",  sub: "02_preprocess",         num: "02" },
  { id: "markers",    title: "Mark vertices", sub: "03_extraction",       num: "03" },
  { id: "features",   title: "Features",    sub: "03_extraction",         num: "03" },
  { id: "draw",       title: "Draw boundaries", sub: "03_extraction",     num: "03" },
  { id: "extract",    title: "Extraction",  sub: "03_extraction",         num: "03" },
  { id: "normalize",  title: "Normalize",   sub: "04_normalize_validate", num: "04" },
  { id: "validate",   title: "Validate",    sub: "04_normalize_validate", num: "04" },
  { id: "convert",    title: "Convert coords", sub: "05_convert_coords",  num: "05" },
  { id: "gempy",      title: "3D model",    sub: "06_gempy_model",        num: "06" },
  { id: "visualize",  title: "Visualize",   sub: "07_visualizer",         num: "07" },
];

export const state = {
  jobId: null,
  sheetType: "illustrator",
  current: "scan",
  completed: {},          // {stepId: true}
  scan: { url: null, isPdf: false, filename: null, dims: null, recommendedUpscale: null },
  preprocess: { cleanUrl: null },
  // CV marker detection (field sheets). Lives in global state, not render
  // closures, so navigating between steps mid-flow doesn't discard work.
  markers: { rotate: 0, clicks: [], squareCm: null, refM: null,
             previewImageUrl: null, features: [], confirmed: [],
             boundaryResult: null, classifyById: null },
  // human-in-the-loop feature inventory (both sheet types, optional)
  features: { imageUrl: null, imageKind: null, imgW: 0, imgH: 0,
              candidates: [], confirmedCount: 0, debugUrl: null },
  // human-drawn boundary geometry (both sheet types, optional)
  draw: { rotate: 0, imageUrl: null, imageKind: null, clicks: [], refM: null,
          boundaries: [], currentIdx: -1, trenchLabel: "", faceLabel: "",
          squareCm: null, lociMeta: {}, layerMeta: {}, result: null },
  extract: { rawJson: null, warning: null },
  normalize: { data: null, log: [] },
  validate: { report: null },
  convert: { gridConfig: null, result: null },
  gempy: { result: null },
  apiKey: "",
};

export const PREREQS = {
  // extract opens after scan (not preprocess) so a previous extraction JSON
  // can be uploaded without re-running the image pipeline; the Gemini path
  // inside the stage still checks for preprocess itself.
  // markers likewise only needs the scan (detection runs on the raw photo,
  // not the preprocessed image) and is optional: extract does not require
  // it, since illustrator sheets and uploaded JSONs never touch it.
  // features and draw likewise open after scan and are both optional:
  // features feeds every extraction path an authoritative inventory, and
  // draw installs a finished extraction all by itself.
  scan: [], preprocess: ["scan"], markers: ["scan"], features: ["scan"],
  draw: ["scan"], extract: ["scan"],
  normalize: ["extract"], validate: ["extract"],
  convert: ["normalize", "validate"], gempy: ["convert"], visualize: ["extract"],
};

// Everything downstream of stepId in the PREREQS graph loses its completed
// flag and cached outputs. Called whenever a stage (re-)runs: without this,
// re-uploading a scan left every later step marked complete, so the sidebar
// and Next button let you jump ahead carrying results from the previous
// image — the exact step-skipping the greyed-out states are meant to stop.
const FRESH_STATE = {
  preprocess: () => ({ cleanUrl: null }),
  markers: () => ({ rotate: 0, clicks: [], squareCm: null, refM: null,
                    previewImageUrl: null, features: [], confirmed: [],
                    boundaryResult: null, classifyById: null }),
  features: () => ({ imageUrl: null, imageKind: null, imgW: 0, imgH: 0,
                     candidates: [], confirmedCount: 0, debugUrl: null }),
  draw: () => ({ rotate: 0, imageUrl: null, imageKind: null, clicks: [],
                 refM: null, boundaries: [], currentIdx: -1, trenchLabel: "",
                 faceLabel: "", squareCm: null, lociMeta: {}, layerMeta: {},
                 result: null }),
  extract: () => ({ rawJson: null, warning: null }),
  normalize: () => ({ data: null, log: [] }),
  validate: () => ({ report: null }),
  convert: () => ({ gridConfig: null, result: null }),
  gempy: () => ({ result: null }),
};

export function invalidateDownstream(stepId) {
  // PREREQS is the gating graph (what must run before a step opens). For
  // staleness there's one extra edge: the server validates the normalized
  // file when it exists, so re-running normalize makes a previous
  // validation report stale even though normalize isn't required to OPEN
  // the validate step. A second edge: extract isn't GATED on markers (the
  // illustrator/upload paths never use them) but a field-sheet extraction
  // built from confirmed markers IS stale once markers re-run.
  // extract also goes stale when the confirmed feature inventory or a
  // hand-drawn build changes, since both shape the installed extraction
  const EXTRA_STALE_EDGES = { validate: ["normalize"],
                              extract: ["markers", "features", "draw"] };
  const depsOf = (id) =>
    (PREREQS[id] || []).concat(EXTRA_STALE_EDGES[id] || []);
  const stale = new Set();
  let grew = true;
  while (grew) {
    grew = false;
    for (const id of Object.keys(PREREQS)) {
      if (stale.has(id)) continue;
      const reqs = depsOf(id);
      if (reqs.includes(stepId) || reqs.some((r) => stale.has(r))) {
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
