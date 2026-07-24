// Run with: node poggio_webapp/static/canvas/grid.test.mjs
import assert from "node:assert/strict";
import {
  metersToPixels,
  nearestGridPoint,
  pixelsToMeters,
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
