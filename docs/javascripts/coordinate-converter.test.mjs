/**
 * The converter re-implements, in JavaScript, arithmetic that already exists in
 * Python. That duplication is the risk: the two can drift silently and the page
 * would go on producing confident wrong numbers.
 *
 * The expected values below were produced by importing the application's own
 * code and running it, not by hand:
 *
 *   backend.routes.manual._make_calibration({...}).convert([760, 520])
 *     -> (2.273, 1.3788)
 *   convert_coords to_site(2.273, 1.3788) with bearing 90, surfaceZ 100
 *     -> X 2.273, Y 0.0, Z 98.6212
 */

import test from "node:test";
import assert from "node:assert/strict";

import { toLocalMetres, toSite } from "./coordinate-converter.mjs";

const CALIBRATION = {
  ox: 220, oy: 180,
  rx: 1180, ry: 196,
  lx: 700, ly: 900,
  refM: 4,
  px: 760, py: 520,
  originX: 0, originY: 0, surfaceZ: 100, bearing: 90,
};

const round4 = (n) => Math.round(n * 10000) / 10000;

test("local metres match the Python Calibration.convert", () => {
  const local = toLocalMetres(CALIBRATION);

  assert.equal(round4(local.xMeters), 2.273);
  assert.equal(round4(local.depthMeters), 1.3788);
  assert.equal(round4(local.pxPerM), 240.0333);
});

test("site coordinates match convert_coords.to_site", () => {
  const local = toLocalMetres(CALIBRATION);
  const site = toSite(local.xMeters, local.depthMeters, CALIBRATION);

  assert.equal(round4(site.X), 2.273);
  assert.equal(round4(site.Y), 0);
  assert.equal(round4(site.Z), 98.6212);
});

test("bearing 0 puts all displacement into Y", () => {
  const local = toLocalMetres(CALIBRATION);
  const site = toSite(local.xMeters, local.depthMeters, { ...CALIBRATION, bearing: 0 });

  assert.equal(round4(site.X), 0);
  assert.equal(round4(site.Y), 2.273);
});

test("depth is positive toward the third click", () => {
  // Mirror the drawing vertically: the lowest click moves above the origin, so
  // the perpendicular must flip and depth stays positive downward from it.
  const flipped = { ...CALIBRATION, ly: -900, py: -520 };
  const local = toLocalMetres(flipped);

  assert.ok(local.depthMeters > 0, "depth should point toward the lowest click");
});

test("clicks closer than two pixels are refused, as the backend refuses them", () => {
  const local = toLocalMetres({ ...CALIBRATION, rx: 221, ry: 181 });

  assert.match(local.error, /too close together/);
});

test("a non-positive real distance is refused", () => {
  assert.match(toLocalMetres({ ...CALIBRATION, refM: 0 }).error, /above zero/);
  assert.match(toLocalMetres({ ...CALIBRATION, refM: -4 }).error, /above zero/);
});
