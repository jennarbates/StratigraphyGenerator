// Run with: node poggio_webapp/static/visualizer/alignment-policy.test.mjs
import assert from "node:assert/strict";
import {
  alignmentUiModel,
  hasExactCalibration,
} from "./alignment-policy.mjs";

const manualCalibration = {
  kind: "manual",
  origin_px: [100, 200],
  ref_px: [500, 200],
  lowest_px: [100, 600],
  ref_meters: 4,
  px_per_m: 100,
};

function test(name, callback) {
  callback();
  console.log(`✓ ${name}`);
}

function without(field) {
  const calibration = {...manualCalibration};
  delete calibration[field];
  return calibration;
}

test("valid manual calibration enables exact mode", () => {
  assert.equal(hasExactCalibration(manualCalibration), true);
});

test("null calibration enables approximate mode", () => {
  assert.equal(hasExactCalibration(null), false);
});

test("empty object does not enable exact mode", () => {
  assert.equal(hasExactCalibration({}), false);
});

test("missing origin does not enable exact mode", () => {
  assert.equal(hasExactCalibration(without("origin_px")), false);
});

test("missing reference does not enable exact mode", () => {
  assert.equal(hasExactCalibration(without("ref_px")), false);
});

test("missing lowest point does not enable exact mode", () => {
  assert.equal(hasExactCalibration(without("lowest_px")), false);
});

test("nonpositive scale does not enable exact mode", () => {
  for (const pxPerMeter of [0, -1]) {
    assert.equal(
      hasExactCalibration({...manualCalibration, px_per_m: pxPerMeter}),
      false,
    );
  }
});

test("exact mode disables controls", () => {
  assert.deepEqual(
    alignmentUiModel(manualCalibration),
    {
      exact: true,
      controlsDisabled: true,
      message: "Exact source-image alignment is active.",
    },
  );
});

test("approximate mode enables controls", () => {
  assert.deepEqual(
    alignmentUiModel(null),
    {
      exact: false,
      controlsDisabled: false,
      message: (
        "The overlay has no source-image calibration. "
        + "Drag a box over the drawing to align it."
      ),
    },
  );
});

test("exact and approximate messages are distinct", () => {
  assert.notEqual(
    alignmentUiModel(manualCalibration).message,
    alignmentUiModel(null).message,
  );
});
