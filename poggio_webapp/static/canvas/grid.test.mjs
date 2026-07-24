// Run with: node poggio_webapp/static/canvas/grid.test.mjs
import assert from "node:assert/strict";
import {
  edgeMidpoint,
  hasSelfIntersection,
  isShapeClosed,
  metersToPixels,
  nearestGridPoint,
  pixelsToMeters,
  serializePolygons,
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
