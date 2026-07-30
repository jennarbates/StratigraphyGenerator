import assert from "node:assert/strict";
import test from "node:test";

import {
  cameraPreset,
  cameraControlModel,
  clampOpacity,
  deterministicSurfaceColor,
  extentCenter,
  extentSize,
  model3dControlState,
  modelLoadStatusSummary,
  setAllSurfaceVisibility,
  surfaceControlModel,
  validateModel3d,
} from "./model3d-core.mjs";

function validModel(overrides = {}) {
  return {
    schema_version: 1,
    kind: "gempy-surface-model",
    coordinate_system: {
      units: "m",
      up_axis: "Z",
    },
    extent: [0, 12, -4, 2, 90, 93],
    resolution: [50, 40, 30],
    series_order: ["Topsoil", "Fill"],
    single_face_note: null,
    surfaces: [
      {
        name: "Topsoil",
        url: "/api/jobs/job-1/file?path=06_gempy_model/topsoil.obj",
      },
      {
        name: "Fill",
        url: "/api/jobs/job-1/file?path=06_gempy_model/fill.obj",
      },
    ],
    warnings: [],
    ...overrides,
  };
}

function expectTypeError(raw, pattern) {
  assert.throws(() => validateModel3d(raw), {
    name: "TypeError",
    message: pattern,
  });
}

test("validateModel3d normalizes a valid minimal model without mutating it", () => {
  const raw = validModel();
  const normalized = validateModel3d(raw);

  assert.deepEqual(normalized, raw);
  assert.notStrictEqual(normalized, raw);
  assert.notStrictEqual(normalized.extent, raw.extent);
  assert.notStrictEqual(normalized.surfaces, raw.surfaces);
  assert.notStrictEqual(normalized.surfaces[0], raw.surfaces[0]);
});

test("validateModel3d requires an object", () => {
  for (const raw of [null, undefined, [], "model"]) {
    expectTypeError(raw, /model3d must be an object/);
  }
});

test("validateModel3d accepts only the supported schema and kind", () => {
  expectTypeError(validModel({ schema_version: undefined }), /schema_version must be 1/);
  expectTypeError(validModel({ schema_version: 2 }), /schema_version must be 1/);
  expectTypeError(validModel({ kind: undefined }), /kind must be "gempy-surface-model"/);
  expectTypeError(validModel({ kind: "volume" }), /kind must be "gempy-surface-model"/);
});

test("validateModel3d requires metre-based Z-up coordinates", () => {
  expectTypeError(validModel({ coordinate_system: undefined }), /coordinate_system must be an object/);
  expectTypeError(
    validModel({ coordinate_system: { units: "", up_axis: "Z" } }),
    /coordinate_system\.units must be a non-empty string/,
  );
  expectTypeError(
    validModel({ coordinate_system: { units: "m", up_axis: "Y" } }),
    /coordinate_system\.up_axis must be "Z"/,
  );
});

test("validateModel3d rejects missing, malformed, and non-finite extents", () => {
  expectTypeError(validModel({ extent: undefined }), /extent must contain six finite numbers/);
  expectTypeError(validModel({ extent: [0, 1] }), /extent must contain six finite numbers/);
  expectTypeError(validModel({ extent: [0, 1, 0, Infinity, 0, 1] }), /extent must contain six finite numbers/);
  expectTypeError(validModel({ extent: [0, 1, 0, 1, 0, NaN] }), /extent must contain six finite numbers/);
});

test("validateModel3d rejects equal or reversed extent axes", () => {
  expectTypeError(validModel({ extent: [1, 1, 0, 2, 0, 3] }), /extent X minimum must be less than maximum/);
  expectTypeError(validModel({ extent: [0, 1, 4, 2, 0, 3] }), /extent Y minimum must be less than maximum/);
  expectTypeError(validModel({ extent: [0, 1, 0, 2, 3, -1] }), /extent Z minimum must be less than maximum/);
});

test("validateModel3d requires three positive integer resolution values", () => {
  expectTypeError(validModel({ resolution: undefined }), /resolution must contain three positive integers/);
  expectTypeError(validModel({ resolution: [50, 40] }), /resolution must contain three positive integers/);
  expectTypeError(validModel({ resolution: [50, 0, 30] }), /resolution must contain three positive integers/);
  expectTypeError(validModel({ resolution: [50, 2.5, 30] }), /resolution must contain three positive integers/);
});

test("validateModel3d validates series metadata", () => {
  expectTypeError(validModel({ series_order: undefined }), /series_order must be an array/);
  expectTypeError(validModel({ series_order: ["Topsoil", ""] }), /series_order\[1\] must be a non-empty string/);
  expectTypeError(validModel({ single_face_note: 42 }), /single_face_note must be null or a string/);
  expectTypeError(validModel({ warnings: ["warning", 42] }), /warnings\[1\] must be a string/);
});

test("validateModel3d requires a surface array with safe names and URLs", () => {
  expectTypeError(validModel({ surfaces: undefined }), /surfaces must be an array/);
  expectTypeError(validModel({ surfaces: [null] }), /surfaces\[0\] must be an object/);
  expectTypeError(
    validModel({ surfaces: [{ name: " ", url: "/api/jobs/job-1/file?path=a.obj" }] }),
    /surfaces\[0\]\.name must be a non-empty string/,
  );
  expectTypeError(
    validModel({ surfaces: [{ name: "Topsoil", url: "" }] }),
    /surfaces\[0\]\.url must be a same-origin \/api\/jobs\/ URL/,
  );
});

test("validateModel3d rejects duplicate surface names", () => {
  expectTypeError(
    validModel({
      surfaces: [
        { name: "Fill", url: "/api/jobs/job-1/file?path=fill-a.obj" },
        { name: "Fill", url: "/api/jobs/job-1/file?path=fill-b.obj" },
      ],
    }),
    /duplicate surface name "Fill"/,
  );
});

test("validateModel3d rejects unsafe surface and lith-block URLs", () => {
  const unsafeUrls = [
    "https://example.test/api/jobs/job-1/file?path=a.obj",
    "//example.test/api/jobs/job-1/file?path=a.obj",
    "../api/jobs/job-1/file?path=a.obj",
    "/static/model.obj",
    "/api/jobs/job-1/\nevil",
  ];

  for (const url of unsafeUrls) {
    expectTypeError(
      validModel({ surfaces: [{ name: "Topsoil", url }] }),
      /surfaces\[0\]\.url must be a same-origin \/api\/jobs\/ URL/,
    );
  }

  expectTypeError(
    validModel({ lith_block_url: "https://example.test/model.npz" }),
    /lith_block_url must be a same-origin \/api\/jobs\/ URL/,
  );
});

test("validateModel3d preserves safe optional lith-block metadata", () => {
  const raw = validModel({
    lith_block_url: "/api/jobs/job-1/file?path=06_gempy_model/trench_model_lith_block.npz",
  });

  assert.equal(validateModel3d(raw).lith_block_url, raw.lith_block_url);
});

test("validateModel3d preserves detached wall traces", () => {
  const wall_traces = [
    {
      face: "north wall",
      surface: "Topsoil",
      points: [[0, 3, 99.9], [2, 3, 99.8], [4, 3, 99.85]],
    },
    {
      face: "east wall",
      surface: "Topsoil",
      points: [[4, 3, 99.85], [4, 0, 99.7]],
    },
  ];
  const normalized = validateModel3d(validModel({ wall_traces }));

  assert.deepEqual(normalized.wall_traces, wall_traces);
  assert.notStrictEqual(normalized.wall_traces, wall_traces);
  assert.notStrictEqual(normalized.wall_traces[0], wall_traces[0]);
  assert.notStrictEqual(normalized.wall_traces[0].points[0], wall_traces[0].points[0]);
});

test("validateModel3d treats absent wall traces as no overlay", () => {
  assert.equal("wall_traces" in validateModel3d(validModel()), false);
  assert.equal(
    "wall_traces" in validateModel3d(validModel({ wall_traces: null })),
    false,
  );
  assert.deepEqual(
    validateModel3d(validModel({ wall_traces: [] })).wall_traces,
    [],
  );
});

test("validateModel3d rejects unusable wall traces", () => {
  const points = [[0, 3, 99.9], [4, 3, 99.85]];

  expectTypeError(
    validModel({ wall_traces: "north wall" }),
    /wall_traces must be an array/,
  );
  expectTypeError(
    validModel({ wall_traces: ["north wall"] }),
    /wall_traces\[0\] must be an object/,
  );
  expectTypeError(
    validModel({ wall_traces: [{ face: "", surface: "Topsoil", points }] }),
    /wall_traces\[0\]\.face must be a non-empty string/,
  );
  expectTypeError(
    validModel({ wall_traces: [{ face: "north wall", points }] }),
    /wall_traces\[0\]\.surface must be a non-empty string/,
  );
  expectTypeError(
    validModel({
      wall_traces: [{ face: "north wall", surface: "Topsoil", points: [points[0]] }],
    }),
    /wall_traces\[0\]\.points must contain at least two points/,
  );
  expectTypeError(
    validModel({
      wall_traces: [{
        face: "north wall",
        surface: "Topsoil",
        points: [points[0], [4, 3, Number.NaN]],
      }],
    }),
    /wall_traces\[0\]\.points\[1\] must contain three finite numbers/,
  );
});

test("model3dControlState shows wall traces by default", () => {
  assert.equal(model3dControlState(validModel()).wallTracesVisible, true);
});

test("validateModel3d preserves validated volume metadata", () => {
  const volume = {
    schema_version: 1,
    format: "raw",
    dtype: "uint16-le",
    layout: "C",
    axes: ["x", "y", "z"],
    shape: [50, 40, 30],
    url: "/api/jobs/job-1/file?path=06_gempy_model/trench_model_lith_block.bin",
    lithologies: [
      { id: 1, name: "Topsoil" },
      { id: 2, name: "Fill" },
    ],
  };
  const normalized = validateModel3d(validModel({ volume }));

  assert.deepEqual(normalized.volume, volume);
  assert.notStrictEqual(normalized.volume, volume);
  assert.notStrictEqual(normalized.volume.shape, volume.shape);
  assert.notStrictEqual(normalized.volume.lithologies, volume.lithologies);
});

test("validateModel3d rejects invalid or resolution-mismatched volume metadata", () => {
  const baseVolume = {
    schema_version: 1,
    format: "raw",
    dtype: "uint16-le",
    layout: "C",
    axes: ["x", "y", "z"],
    shape: [50, 40, 30],
    url: "/api/jobs/job-1/file?path=06_gempy_model/trench_model_lith_block.bin",
    lithologies: [{ id: 1, name: "Topsoil" }],
  };

  expectTypeError(
    validModel({ volume: { ...baseVolume, dtype: "uint16" } }),
    /volume\.dtype must be "uint16-le"/,
  );
  expectTypeError(
    validModel({ volume: { ...baseVolume, shape: [50, 40, 29] } }),
    /volume\.shape must match model3d\.resolution/,
  );
});

test("extentCenter and extentSize calculate a non-cubic extent exactly", () => {
  const extent = [-4, 8, 10, 16, 90, 93];

  assert.deepEqual(extentCenter(extent), [2, 13, 91.5]);
  assert.deepEqual(extentSize(extent), [12, 6, 3]);
});

test("cameraPreset returns Z-up top, front, side, and isometric views", () => {
  const extent = [-4, 8, 10, 16, 90, 93];
  const target = extentCenter(extent);
  const top = cameraPreset(extent, "top");
  const front = cameraPreset(extent, "front");
  const side = cameraPreset(extent, "side");
  const isometric = cameraPreset(extent, "isometric");

  for (const preset of [top, front, side, isometric]) {
    assert.deepEqual(preset.target, target);
    assert.deepEqual(preset.up, [0, 0, 1]);
    assert.ok(preset.distance > 0);
  }

  assert.deepEqual(top.position.slice(0, 2), target.slice(0, 2));
  assert.ok(top.position[2] > target[2], "top looks down along negative Z");
  assert.equal(front.position[0], target[0]);
  assert.ok(front.position[1] > target[1], "front looks along negative Y");
  assert.equal(front.position[2], target[2]);
  assert.ok(side.position[0] > target[0], "side looks along negative X");
  assert.deepEqual(side.position.slice(1), target.slice(1));
  assert.ok(isometric.position.every((value, index) => value > target[index]));
});

test("cameraPreset rejects unknown view names", () => {
  assert.throws(() => cameraPreset([0, 1, 0, 1, 0, 1], "back"), {
    name: "TypeError",
    message: /viewName must be one of/,
  });
});

test("clampOpacity clamps below, within, and above the supported range", () => {
  assert.equal(clampOpacity(-2), 0.1);
  assert.equal(clampOpacity(0.1), 0.1);
  assert.equal(clampOpacity(0.72), 0.72);
  assert.equal(clampOpacity(1), 1);
  assert.equal(clampOpacity(4), 1);
  assert.throws(() => clampOpacity(NaN), {
    name: "TypeError",
    message: /opacity must be a finite number/,
  });
});

test("surfaceControlModel preserves manifest order and passed colors", () => {
  const controls = surfaceControlModel(validModel(), (name, index) => `${index}:${name}`);

  assert.deepEqual(controls, [
    {
      name: "Topsoil",
      url: "/api/jobs/job-1/file?path=06_gempy_model/topsoil.obj",
      color: "0:Topsoil",
      visible: true,
    },
    {
      name: "Fill",
      url: "/api/jobs/job-1/file?path=06_gempy_model/fill.obj",
      color: "1:Fill",
      visible: true,
    },
  ]);
});

test("surfaceControlModel fallback colors are deterministic", () => {
  const first = surfaceControlModel(validModel());
  const second = surfaceControlModel(validModel());

  assert.deepEqual(first, second);
  assert.match(first[0].color, /^#[0-9a-f]{6}$/);
  assert.notEqual(first[0].color, first[1].color);
});

test("deterministicSurfaceColor is stable without renderer or DOM state", () => {
  assert.equal(
    deterministicSurfaceColor("Topsoil"),
    deterministicSurfaceColor("Topsoil"),
  );
  assert.match(deterministicSurfaceColor("Fill"), /^#[0-9a-f]{6}$/);
  assert.throws(() => deterministicSurfaceColor(""), {
    name: "TypeError",
    message: /surface name must be a non-empty string/,
  });
});

test("model3dControlState uses accessible control defaults in manifest order", () => {
  const controls = model3dControlState(
    validModel(),
    (name, index) => `${index}:${name}`,
  );

  assert.equal(controls.opacity, 0.72);
  assert.equal(controls.wireframe, false);
  assert.equal(controls.helpersVisible, true);
  assert.equal(controls.cameraView, "isometric");
  assert.deepEqual(
    controls.surfaces.map(({ name, visible, color }) => ({ name, visible, color })),
    [
      { name: "Topsoil", visible: true, color: "0:Topsoil" },
      { name: "Fill", visible: true, color: "1:Fill" },
    ],
  );
});

test("setAllSurfaceVisibility creates show-all and hide-all state", () => {
  const initial = model3dControlState(validModel()).surfaces;
  const hidden = setAllSurfaceVisibility(initial, false);
  const shown = setAllSurfaceVisibility(hidden, true);

  assert.deepEqual(hidden.map((surface) => surface.visible), [false, false]);
  assert.deepEqual(shown.map((surface) => surface.visible), [true, true]);
  assert.deepEqual(shown.map((surface) => surface.name), ["Topsoil", "Fill"]);
  assert.notStrictEqual(hidden, initial);
  assert.notStrictEqual(hidden[0], initial[0]);
  assert.equal(initial[0].visible, true, "the input state is not mutated");
  assert.throws(() => setAllSurfaceVisibility(initial, "yes"), {
    name: "TypeError",
    message: /visible must be a boolean/,
  });
});

test("cameraControlModel exposes the required camera control names", () => {
  const controls = cameraControlModel("front");

  assert.deepEqual(
    controls.map((control) => control.label),
    ["Reset", "Top", "Front", "Side", "3D"],
  );
  assert.equal(controls.find((control) => control.label === "Reset").pressed, null);
  assert.equal(controls.find((control) => control.label === "Front").pressed, true);
  assert.equal(controls.find((control) => control.label === "3D").pressed, false);
  assert.throws(() => cameraControlModel("back"), {
    name: "TypeError",
    message: /active camera view/,
  });
});

test("modelLoadStatusSummary reports deterministic partial failures", () => {
  const summary = modelLoadStatusSummary({
    phase: "complete",
    loaded: 1,
    failed: 2,
    total: 3,
    failures: [
      { name: "Fill (late?)", message: "404" },
      { name: "Topsoil & stones", message: "invalid OBJ" },
    ],
  });

  assert.deepEqual(summary, {
    status: "Loaded 1 of 3 surfaces.",
    warning: "Could not load 2 surfaces: Fill (late?), Topsoil & stones.",
    failedNames: ["Fill (late?)", "Topsoil & stones"],
    recoverable: false,
  });
});

test("modelLoadStatusSummary covers loading and all-failed recovery", () => {
  assert.deepEqual(
    modelLoadStatusSummary({
      phase: "loading",
      loaded: 1,
      failed: 0,
      settled: 1,
      total: 2,
    }),
    {
      status: "Loading 1 of 2 surfaces…",
      warning: "",
      failedNames: [],
      recoverable: false,
    },
  );

  assert.deepEqual(
    modelLoadStatusSummary({
      phase: "error",
      loaded: 0,
      failed: 2,
      total: 2,
      failures: [{ name: "Topsoil" }, { name: "Fill" }],
    }),
    {
      status: "No 3D surfaces could be displayed.",
      warning: "Could not load 2 surfaces: Topsoil, Fill.",
      failedNames: ["Topsoil", "Fill"],
      recoverable: true,
    },
  );
});
