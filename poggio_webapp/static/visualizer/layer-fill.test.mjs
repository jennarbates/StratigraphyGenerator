import assert from "node:assert/strict";
import {
  layerFillPath,
  layerFillPolygon,
} from "./layer-fill.mjs";

function test(name, callback) {
  callback();
  console.log(`✓ ${name}`);
}

test("oppositely ordered boundaries produce an uncrossed polygon", () => {
  const polygon = layerFillPolygon(
    [
      { x: 0, y: 0, along: 0 },
      { x: 10, y: 0, along: 10 },
    ],
    [
      { x: 10, y: 2, along: 10 },
      { x: 0, y: 2, along: 0 },
    ],
  );

  assert.deepEqual(polygon, [
    { x: 0, y: 0 },
    { x: 10, y: 0 },
    { x: 10, y: 2 },
    { x: 0, y: 2 },
  ]);
});

test("boundaries are clipped to their shared span", () => {
  const polygon = layerFillPolygon(
    [
      { x: -5, y: 0, along: -5 },
      { x: 10, y: 0, along: 10 },
    ],
    [
      { x: 0, y: 2, along: 0 },
      { x: 6, y: 2, along: 6 },
    ],
  );

  assert.deepEqual(polygon, [
    { x: 0, y: 0 },
    { x: 6, y: 0 },
    { x: 6, y: 2 },
    { x: 0, y: 2 },
  ]);
});

test("pixel-only boundaries derive a shared direction", () => {
  assert.deepEqual(
    layerFillPolygon(
      [{ x: 0, y: 0 }, { x: 5, y: 5 }],
      [{ x: 6, y: 4 }, { x: 1, y: -1 }],
    ),
    [
      { x: 0, y: 0 },
      { x: 5, y: 5 },
      { x: 6, y: 4 },
      { x: 1, y: -1 },
    ],
  );
});

test("crossing boundaries do not produce a misleading fill", () => {
  assert.equal(
    layerFillPath(
      [
        { x: 0, y: 0, along: 0 },
        { x: 10, y: 10, along: 10 },
      ],
      [
        { x: 0, y: 10, along: 0 },
        { x: 10, y: 0, along: 10 },
      ],
    ),
    null,
  );
});

test("backtracking boundaries do not produce a fill", () => {
  assert.equal(
    layerFillPath(
      [
        { x: 0, y: 0, along: 0 },
        { x: 2, y: 0, along: 2 },
        { x: 1, y: 0, along: 1 },
      ],
      [
        { x: 0, y: 2, along: 0 },
        { x: 2, y: 2, along: 2 },
      ],
    ),
    null,
  );
});

test("non-overlapping boundaries do not produce a fill", () => {
  assert.equal(
    layerFillPath(
      [
        { x: 0, y: 0, along: 0 },
        { x: 2, y: 0, along: 2 },
      ],
      [
        { x: 3, y: 2, along: 3 },
        { x: 5, y: 2, along: 5 },
      ],
    ),
    null,
  );
});
