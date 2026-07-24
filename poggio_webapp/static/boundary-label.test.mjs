import assert from "node:assert/strict";
import test from "node:test";

import { pointInsideBand } from "./boundary-label.js";


test("places a locus label halfway between sloping boundaries", () => {
  const top = [{ x: 0, y: 0 }, { x: 10, y: 2 }];
  const bottom = [{ x: 0, y: 4 }, { x: 10, y: 8 }];

  assert.deepEqual(pointInsideBand(top, bottom), { x: 5, y: 3.5 });
});


test("uses the horizontal overlap shared by both boundaries", () => {
  const top = [{ x: 0, y: 1 }, { x: 8, y: 1 }];
  const bottom = [{ x: 4, y: 5 }, { x: 12, y: 5 }];

  assert.deepEqual(pointInsideBand(top, bottom), { x: 6, y: 3 });
});


test("does not place a label until both sides of the locus are traced", () => {
  assert.equal(
    pointInsideBand([{ x: 0, y: 1 }, { x: 8, y: 1 }], []),
    null,
  );
});
