// Run with: node poggio_webapp/static/visualizer/viewbox.test.mjs
import assert from "node:assert/strict";
import { legacyViewBox } from "./viewbox.mjs";

const tolerance = 1e-5;

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

test("legacyViewBox with pad=0 returns the data extent unchanged", () => {
  assert.deepEqual(
    legacyViewBox(10, 5, 0),
    { vbW: 10, vbH: 5, ox: 0, oy: 0 },
  );
});

test("legacyViewBox default pad is 0", () => {
  assert.deepEqual(
    legacyViewBox(10, 5),
    { vbW: 10, vbH: 5, ox: 0, oy: 0 },
  );
});

test("legacyViewBox with a nonzero pad still centers correctly", () => {
  const viewBox = legacyViewBox(10, 5, 0.04);

  assertClose(viewBox.vbW, 10.8, "viewBox width");
  assertClose(viewBox.vbH, 5.4, "viewBox height");
  assertClose(viewBox.ox, 0.4, "x offset");
  assertClose(viewBox.oy, 0.2, "y offset");
});
