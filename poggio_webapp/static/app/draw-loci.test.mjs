import assert from "node:assert/strict";
import test from "node:test";

import { ensureLocusTopBoundary } from "./draw-loci.js";


test("first verified-locus selection starts its top boundary", () => {
  const boundaries = [];

  assert.deepEqual(ensureLocusTopBoundary(boundaries, "1042"), {
    index: 0,
    created: true,
  });
  assert.deepEqual(boundaries, [
    { kind: "top", name: "1042", points: [] },
  ]);
});


test("selecting the next verified locus creates and switches to its top", () => {
  const boundaries = [
    { kind: "top", name: "1042", points: [[10, 20], [30, 20]] },
  ];

  assert.deepEqual(ensureLocusTopBoundary(boundaries, "1043"), {
    index: 1,
    created: true,
  });
  assert.deepEqual(boundaries[1], {
    kind: "top",
    name: "1043",
    points: [],
  });
});


test("reselecting a verified locus activates its existing top", () => {
  const boundaries = [
    { kind: "top", name: "1042", points: [[10, 20]] },
    { kind: "top", name: "1043", points: [[10, 40]] },
  ];

  assert.deepEqual(ensureLocusTopBoundary(boundaries, "1042"), {
    index: 0,
    created: false,
  });
  assert.equal(boundaries.length, 2);
});


test("blank and non-string locus values do not create boundaries", () => {
  const boundaries = [];

  assert.deepEqual(ensureLocusTopBoundary(boundaries, "   "), {
    index: -1,
    created: false,
  });
  assert.deepEqual(ensureLocusTopBoundary(boundaries, 1042), {
    index: -1,
    created: false,
  });
  assert.deepEqual(boundaries, []);
});
