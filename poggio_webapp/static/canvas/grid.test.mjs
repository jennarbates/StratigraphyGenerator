// Run with: node poggio_webapp/static/canvas/grid.test.mjs
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  assembleEditorSessionState,
  assembleFinalizeState,
  edgeMidpoint,
  hasSelfIntersection,
  isShapeClosed,
  metersToPixels,
  nearestGridPoint,
  pixelsToMeters,
  selectFace,
  serializePolygons,
  validateBearingDeg,
} from "./grid.mjs";

const pixelsPerMeter = 200;

function test(name, callback) {
  callback();
  console.log(`✓ ${name}`);
}

test("metre values survive a metre-to-pixel-to-metre round trip", () => {
  for (const meters of [0, 0.25, 1, 2.875, -0.5]) {
    const pixels = metersToPixels(meters, pixelsPerMeter);
    const roundTripMeters = pixelsToMeters(pixels, pixelsPerMeter);
    assert.ok(
      Math.abs(roundTripMeters - meters) < Number.EPSILON,
      `${meters}m should survive a metre/pixel round trip`,
    );
  }
});

const spacing = 50;

test("a point exactly on grid lines remains unchanged", () => {
  assert.deepEqual(
    nearestGridPoint(100, 150, spacing),
    { x: 100, y: 150 },
  );
});

test("each coordinate snaps independently to its nearest grid line", () => {
  assert.deepEqual(
    nearestGridPoint(124, 176, spacing),
    { x: 100, y: 200 },
  );
});

test("a halfway point snaps to the higher grid line", () => {
  assert.deepEqual(
    nearestGridPoint(125, 175, spacing),
    { x: 150, y: 200 },
  );
});

test("a negative halfway point also snaps to the higher grid line", () => {
  assert.deepEqual(
    nearestGridPoint(-25, -75, spacing),
    { x: 0, y: -50 },
  );
});

test("non-positive grid spacing is rejected", () => {
  assert.throws(
    () => nearestGridPoint(10, 20, 0),
    RangeError,
  );
});

test("a bow-tie polygon is self-intersecting", () => {
  assert.equal(
    hasSelfIntersection([
      { x: 0, y: 0 },
      { x: 4, y: 4 },
      { x: 0, y: 4 },
      { x: 4, y: 0 },
    ]),
    true,
  );
});

test("a square polygon is not self-intersecting", () => {
  assert.equal(
    hasSelfIntersection([
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 4 },
      { x: 0, y: 4 },
    ]),
    false,
  );
});

test("a shape is closed only when its path ends at its first point", () => {
  const openPath = [
    { x: 0, y: 0 },
    { x: 4, y: 0 },
    { x: 4, y: 4 },
    { x: 0, y: 4 },
  ];
  const closedPath = [...openPath, openPath[0]];

  assert.equal(isShapeClosed(openPath), false);
  assert.equal(isShapeClosed(closedPath), true);
});

test("an edge midpoint is halfway between both endpoints", () => {
  assert.deepEqual(
    edgeMidpoint({ x: 2, y: 6 }, { x: 8, y: 14 }),
    { x: 5, y: 10 },
  );
});

const polygonGeometry = [
  {
    id: 1,
    vertices: [
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      { x: 100, y: 50 },
    ],
  },
  {
    id: 2,
    vertices: [
      { x: 50, y: 50 },
      { x: 150, y: 50 },
      { x: 100, y: 100 },
    ],
  },
  {
    id: 3,
    vertices: [],
  },
];

test("serialization includes every polygon with metadata", () => {
  const serialized = serializePolygons(
    polygonGeometry,
    {
      1: { material: "Soil", note: "Upper layer" },
      2: { material: "Stone", note: "" },
    },
    "ArchaeologicalDiagram",
  );

  assert.deepEqual(
    serialized.map(({ polygonId }) => polygonId),
    [1, 2],
  );
  assert.doesNotThrow(() => JSON.stringify(serialized));
});

test("serialization shapes Archaeological and FieldWall metadata correctly", () => {
  const archaeological = serializePolygons(
    [polygonGeometry[0]],
    { 1: { material: "Tile", note: "Burnt" } },
    "ArchaeologicalDiagram",
  );
  const fieldWall = serializePolygons(
    [polygonGeometry[0]],
    { 1: { locus: "1042", munsell: "10 5/3", note: "Compact" } },
    "FieldWallProfile",
  );

  assert.deepEqual(archaeological, [{
    polygonId: 1,
    geometry: polygonGeometry[0].vertices,
    material: "Tile",
    note: "Burnt",
  }]);
  assert.deepEqual(fieldWall, [{
    polygonId: 1,
    geometry: polygonGeometry[0].vertices,
    locus: "1042",
    munsell: "10 5/3",
    note: "Compact",
  }]);
});

const chunkThreeArchaeologicalFixture = {
  metadata: {
    currentFilePath: "manual-editor",
    suggestedFilename: "trench_104_2026",
    trenchLabel: "T104",
    scale: {
      unit: "m",
      valuesMarked: [0, 1],
      metricConversionAssumption: null,
      confidence: "certain",
    },
    credits: {
      attributions: [
        {
          name: "A. Recorder",
          role: "illustrator",
        },
      ],
      year: "2026",
    },
    marginalia: [],
  },
  trenchProfiles: [
    {
      face: "south",
      gridLabels: ["A"],
      gridLabelXMeters: [0.0],
      layers: [
        {
          layerName: "Layer 1",
          inferredMaterial: "soil",
          description: "Brown soil",
          visualPattern: "dots",
          featuresInLayer: [],
          topBoundary: [
            {
              xCoordinateMeters: 0.0,
              yCoordinateMeters: 0.0,
              confidence: "human-traced",
            },
          ],
          bottomBoundary: [
            {
              xCoordinateMeters: 0.0,
              yCoordinateMeters: 0.4,
              confidence: "human-traced",
            },
          ],
        },
      ],
    },
  ],
  legend: [
    {
      visualPattern: "dots",
      material: "soil",
    },
  ],
  inferred_notes: [],
  rawTranscription: "Manual editor example",
};

const fixtureEditorState = {
  activeFaceIndex: 0,
  faces: [
    {
      name: "south",
      gridLabels: ["A"],
      gridLabelXMeters: [0.0],
      gridRegistration: {
        originX: 123.5,
        originY: 456.25,
        surfaceZ: 287.8,
        bearing_deg: 90,
      },
      polygons: [
        {
          id: 1,
          closed: true,
          vertices: [{ x: 0, y: 80 }],
        },
      ],
      polygonMetadata: {
        1: {
          layerName: "Layer 1",
          inferredMaterial: "soil",
          description: "Brown soil",
          visualPattern: "dots",
          featuresInLayer: [],
          topBoundary: [
            {
              x: 0,
              y: 0,
              confidence: "human-traced",
            },
          ],
        },
      },
    },
  ],
};

const fixtureDocumentMetadata = {
  metadata: chunkThreeArchaeologicalFixture.metadata,
  legend: chunkThreeArchaeologicalFixture.legend,
  inferred_notes: chunkThreeArchaeologicalFixture.inferred_notes,
  rawTranscription: chunkThreeArchaeologicalFixture.rawTranscription,
};

test("full editor state assembles to the exact Chunk 3 finalize fixture", () => {
  const assembled = assembleEditorSessionState(
    fixtureEditorState,
    "ArchaeologicalDiagram",
    fixtureDocumentMetadata,
  );

  assert.deepEqual(
    assembled.finalizeState,
    chunkThreeArchaeologicalFixture,
  );
  assert.deepEqual(assembled.gridConfig, {
    faces: {
      south: {
        originX: 123.5,
        originY: 456.25,
        surfaceZ: 287.8,
        bearing_deg: 90,
      },
    },
  });
});

test("multi-face assembly includes each face and each registered polygon once", () => {
  const multiFaceState = {
    activeFaceIndex: 0,
    faces: [
      fixtureEditorState.faces[0],
      {
        name: "east",
        gridRegistration: {
          originX: 125,
          originY: 458,
          surfaceZ: 288,
          bearing_deg: 180,
        },
        polygons: [
          {
            id: 1,
            closed: true,
            vertices: [{ x: 100, y: 50 }],
          },
        ],
        polygonMetadata: {
          1: {
            layerName: "Layer 2",
            material: "clay",
            note: "East face",
          },
        },
      },
    ],
  };

  const assembled = assembleFinalizeState(
    multiFaceState,
    "ArchaeologicalDiagram",
    fixtureDocumentMetadata,
  );

  assert.deepEqual(
    assembled.trenchProfiles.map(({ face }) => face),
    ["south", "east"],
  );
  assert.deepEqual(
    assembled.trenchProfiles.map(({ layers }) => layers.length),
    [1, 1],
  );
  assert.deepEqual(
    assembled.trenchProfiles[1].layers[0].bottomBoundary,
    [{
      xCoordinateMeters: 0.5,
      yCoordinateMeters: 0.25,
      confidence: "human-traced",
    }],
  );
});

test("bearing validation rejects values outside 0 through 360", () => {
  assert.equal(validateBearingDeg(0), 0);
  assert.equal(validateBearingDeg(360), 360);
  assert.throws(() => validateBearingDeg(-0.1), RangeError);
  assert.throws(() => validateBearingDeg(360.1), RangeError);
});

test("switching faces and back preserves polygons without duplication", () => {
  const editorState = {
    activeFaceIndex: 0,
    faces: [
      { name: "south", polygons: [{ id: 1 }] },
      { name: "east", polygons: [{ id: 1 }, { id: 2 }] },
    ],
  };
  const southBeforeSwitch = structuredClone(editorState.faces[0].polygons);
  const eastBeforeSwitch = structuredClone(editorState.faces[1].polygons);

  assert.equal(selectFace(editorState, 1).name, "east");
  assert.equal(selectFace(editorState, 0).name, "south");
  assert.deepEqual(editorState.faces[0].polygons, southBeforeSwitch);
  assert.deepEqual(editorState.faces[1].polygons, eastBeforeSwitch);
});

test("assembled fixture validates through finalize_editor_session", () => {
  const assembled = assembleEditorSessionState(
    fixtureEditorState,
    "ArchaeologicalDiagram",
    fixtureDocumentMetadata,
  );
  const repoRoot = fileURLToPath(new URL("../../../", import.meta.url));
  const virtualEnvironmentPython = join(repoRoot, ".venv", "bin", "python");
  const python = existsSync(virtualEnvironmentPython)
    ? virtualEnvironmentPython
    : "python3";
  const script = `
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "poggio_webapp"))
from pipeline import editor

state = json.load(sys.stdin)
with tempfile.TemporaryDirectory() as jobs_directory:
    editor.JOBS_DIR = Path(jobs_directory)
    job_id = editor.create_editor_session("ArchaeologicalDiagram")
    editor.save_editor_state(job_id, state)
    result = editor.finalize_editor_session(job_id)
    assert result.model_dump(exclude={"source"}) == state
    print(f"validated {type(result).__name__}, source={result.source}")
`;
  const result = spawnSync(python, ["-c", script], {
    cwd: repoRoot,
    input: JSON.stringify(assembled.finalizeState),
    encoding: "utf8",
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(
    result.stdout,
    /validated ArchaeologicalDiagram, source=manual_editor/,
  );
});
