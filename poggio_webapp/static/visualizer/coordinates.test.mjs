// Run with: node poggio_webapp/static/visualizer/coordinates.test.mjs
import assert from "node:assert/strict";
import {
  calibrationAxes,
  metersToSourcePixel,
  pointToSourcePixel,
  projectPolyline,
} from "./coordinates.mjs";

const tolerance = 1e-5;

const manualCalibration = {
  kind: "manual",
  origin_px: [1434, 1622],
  ref_px: [4163, 1571],
  lowest_px: [1390, 3178],
  ref_meters: 4,
  px_per_m: 682.369127,
};

function test(name, callback) {
  callback();
  console.log(`✓ ${name}`);
}

function assertClose(actual, expected, message) {
  assert.ok(
    Math.abs(actual - expected) <= tolerance,
    `${message}: expected ${expected}, received ${actual}`,
  );
}

function assertPointClose(actual, expected, message) {
  assertClose(actual.x, expected.x, `${message} x`);
  assertClose(actual.y, expected.y, `${message} y`);
}

test("calibration origin maps exactly to origin_px", () => {
  assert.deepEqual(
    metersToSourcePixel(
      { xMeters: 0, depthMeters: 0 },
      manualCalibration,
    ),
    { x: 1434, y: 1622 },
  );
});

test("four metre reference maps back to ref_px", () => {
  assertPointClose(
    metersToSourcePixel(
      { xMeters: 4, depthMeters: 0 },
      manualCalibration,
    ),
    { x: 4163, y: 1571 },
    "reference endpoint",
  );
});

test("positive depth points toward lowest_px", () => {
  const axes = calibrationAxes(manualCalibration);
  const projected = metersToSourcePixel(
    { xMeters: 0, depthMeters: 1 },
    manualCalibration,
  );
  const towardLowest = {
    x: manualCalibration.lowest_px[0] - manualCalibration.origin_px[0],
    y: manualCalibration.lowest_px[1] - manualCalibration.origin_px[1],
  };
  const projectedDepth = {
    x: projected.x - axes.origin.x,
    y: projected.y - axes.origin.y,
  };

  assert.ok(
    (towardLowest.x * projectedDepth.x)
      + (towardLowest.y * projectedDepth.y) > 0,
    "positive depth should have a positive projection toward lowest_px",
  );
});

test("tilted reference produces orthonormal axes", () => {
  const axes = calibrationAxes({
    origin_px: [2, 3],
    ref_px: [5, 7],
    lowest_px: [0, 10],
    px_per_m: 5,
  });
  const uLength = Math.hypot(axes.u.x, axes.u.y);
  const vLength = Math.hypot(axes.v.x, axes.v.y);
  const dot = (axes.u.x * axes.v.x) + (axes.u.y * axes.v.y);

  assertClose(uLength, 1, "u length");
  assertClose(vLength, 1, "v length");
  assertClose(dot, 0, "u/v dot product");
});

test("downward axis flips when required", () => {
  const axes = calibrationAxes({
    origin_px: [0, 0],
    ref_px: [10, 0],
    lowest_px: [0, -5],
    px_per_m: 10,
  });

  assert.deepEqual(axes.v, { x: 0, y: -1 });
});

test("field-wall coordinate names are accepted", () => {
  assertPointClose(
    pointToSourcePixel(
      { xMeters: 1.2, depthMeters: 0.4 },
      {
        origin_px: [10, 20],
        ref_px: [20, 20],
        lowest_px: [10, 30],
        px_per_m: 10,
      },
    ),
    { x: 22, y: 24 },
    "field-wall point",
  );
});

test("illustrator coordinate names are accepted", () => {
  assertPointClose(
    pointToSourcePixel(
      { xCoordinateMeters: 1.2, yCoordinateMeters: 0.4 },
      {
        origin_px: [10, 20],
        ref_px: [20, 20],
        lowest_px: [10, 30],
        px_per_m: 10,
      },
    ),
    { x: 22, y: 24 },
    "illustrator point",
  );
});

test("sourcePixel overrides calculated coordinates", () => {
  assert.deepEqual(
    pointToSourcePixel(
      {
        xMeters: 1.2,
        depthMeters: 0.4,
        sourcePixel: [2250, 1900],
      },
      manualCalibration,
    ),
    { x: 2250, y: 1900 },
  );
});

test("projectPolyline preserves order", () => {
  const points = [
    { xMeters: 2, depthMeters: 0 },
    { xMeters: 0, depthMeters: 1 },
    { xMeters: 1, depthMeters: 0.5 },
  ];
  const calibration = {
    origin_px: [0, 0],
    ref_px: [10, 0],
    lowest_px: [0, 10],
    px_per_m: 10,
  };

  assert.deepEqual(
    projectPolyline(points, calibration),
    [
      { x: 20, y: 0 },
      { x: 0, y: 10 },
      { x: 10, y: 5 },
    ],
  );
});

test("zero-length reference is rejected", () => {
  assert.throws(
    () => calibrationAxes({
      origin_px: [5, 5],
      ref_px: [5, 5],
      lowest_px: [5, 10],
      px_per_m: 10,
    }),
    RangeError,
  );
});

test("nonpositive px_per_m is rejected", () => {
  for (const pxPerMeter of [0, -1]) {
    assert.throws(
      () => calibrationAxes({
        origin_px: [0, 0],
        ref_px: [10, 0],
        lowest_px: [0, 10],
        px_per_m: pxPerMeter,
      }),
      RangeError,
    );
  }
});

test("missing point coordinates are rejected", () => {
  assert.throws(
    () => pointToSourcePixel({ xMeters: 1.2 }, manualCalibration),
    TypeError,
  );
  assert.throws(
    () => pointToSourcePixel({}, manualCalibration),
    TypeError,
  );
});
