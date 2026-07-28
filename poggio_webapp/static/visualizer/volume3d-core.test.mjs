import assert from "node:assert/strict";
import test from "node:test";

import {
  cellCenter,
  decodeUint16LE,
  groupCellsByLithology,
  validateVolumeMetadata,
  visibleCellRange,
  volumeIndex,
} from "./volume3d-core.mjs";

function validMetadata(overrides = {}) {
  return {
    schema_version: 1,
    format: "raw",
    dtype: "uint16-le",
    layout: "C",
    axes: ["x", "y", "z"],
    shape: [2, 3, 4],
    url: "/api/jobs/job-1/file?path=06_gempy_model/trench_model_lith_block.bin",
    lithologies: [
      { id: 2, name: "Fill" },
      { id: 7, name: "Basement" },
    ],
    ...overrides,
  };
}

test("validateVolumeMetadata returns a detached normalized copy", () => {
  const raw = validMetadata();
  const normalized = validateVolumeMetadata(raw);

  assert.deepEqual(normalized, raw);
  assert.notStrictEqual(normalized, raw);
  assert.notStrictEqual(normalized.axes, raw.axes);
  assert.notStrictEqual(normalized.shape, raw.shape);
  assert.notStrictEqual(normalized.lithologies, raw.lithologies);
  assert.notStrictEqual(normalized.lithologies[0], raw.lithologies[0]);
});

test("validateVolumeMetadata rejects unsupported and malformed metadata", () => {
  const cases = [
    [null, /volume metadata must be an object/],
    [validMetadata({ schema_version: 2 }), /schema_version must be 1/],
    [validMetadata({ format: "npz" }), /format must be "raw"/],
    [validMetadata({ dtype: "uint16" }), /dtype must be "uint16-le"/],
    [validMetadata({ layout: "F" }), /layout must be "C"/],
    [validMetadata({ axes: ["z", "y", "x"] }), /axes must be \["x", "y", "z"\]/],
    [validMetadata({ shape: [2, 0, 4] }), /shape must contain three positive integers/],
    [validMetadata({ url: "https://example.test/volume.bin" }), /same-origin \/api\/jobs\/ URL/],
    [validMetadata({ lithologies: [{ id: -1, name: "Void" }] }), /id must be an integer from 0 through 65535/],
    [validMetadata({ lithologies: [{ id: 1, name: " " }] }), /name must be a non-empty string/],
    [
      validMetadata({
        lithologies: [
          { id: 2, name: "Fill" },
          { id: 2, name: "Duplicate" },
        ],
      }),
      /duplicate lithology id 2/,
    ],
  ];

  for (const [raw, message] of cases) {
    assert.throws(() => validateVolumeMetadata(raw), {
      name: "TypeError",
      message,
    });
  }
});

test("decodeUint16LE decodes exact little-endian bytes", () => {
  const bytes = Uint8Array.from([
    0x00, 0x00,
    0x01, 0x00,
    0x00, 0x01,
    0xff, 0xff,
  ]);

  assert.deepEqual(
    [...decodeUint16LE(bytes.buffer, 4)],
    [0, 1, 256, 65535],
  );
});

test("decodeUint16LE rejects an odd byte length", () => {
  assert.throws(
    () => decodeUint16LE(Uint8Array.from([1, 0, 2]).buffer, 2),
    {
      name: "RangeError",
      message: /byte length must be even/,
    },
  );
});

test("decodeUint16LE rejects the wrong element count", () => {
  assert.throws(
    () => decodeUint16LE(Uint8Array.from([1, 0, 2, 0]).buffer, 3),
    {
      name: "RangeError",
      message: /contains 2 elements; expected 3/,
    },
  );
});

test("volumeIndex follows C order for a non-cubic shape", () => {
  const shape = [2, 3, 4];

  for (let x = 0; x < shape[0]; x += 1) {
    for (let y = 0; y < shape[1]; y += 1) {
      for (let z = 0; z < shape[2]; z += 1) {
        assert.equal(
          volumeIndex(x, y, z, shape),
          ((x * shape[1]) + y) * shape[2] + z,
        );
      }
    }
  }
});

test("cellCenter returns the first and last world-space cell centers", () => {
  const shape = [2, 3, 4];
  const extent = [-2, 6, 10, 16, 90, 98];

  assert.deepEqual(cellCenter(0, 0, 0, shape, extent), [0, 11, 91]);
  assert.deepEqual(cellCenter(1, 2, 3, shape, extent), [4, 15, 97]);
});

test("visibleCellRange uses inclusive x, y, and z slice boundaries", () => {
  const shape = [2, 3, 4];

  assert.deepEqual(visibleCellRange(shape), {
    x: { min: 0, max: 1 },
    y: { min: 0, max: 2 },
    z: { min: 0, max: 3 },
  });
  assert.deepEqual(visibleCellRange(shape, { x: 0, y: 1, z: 2 }), {
    x: { min: 0, max: 0 },
    y: { min: 0, max: 1 },
    z: { min: 0, max: 2 },
  });
});

test("groupCellsByLithology applies each maximum slice boundary", () => {
  const metadata = validMetadata({
    lithologies: [{ id: 1, name: "Layer" }],
  });
  const values = new Uint16Array(24).fill(1);

  const xSlice = groupCellsByLithology(values, metadata, { x: 0 });
  const ySlice = groupCellsByLithology(values, metadata, { y: 1 });
  const zSlice = groupCellsByLithology(values, metadata, { z: 2 });

  assert.equal(xSlice[0].cells.length, 1 * 3 * 4);
  assert.ok(xSlice[0].cells.every(([x]) => x <= 0));
  assert.equal(ySlice[0].cells.length, 2 * 2 * 4);
  assert.ok(ySlice[0].cells.every(([, y]) => y <= 1));
  assert.equal(zSlice[0].cells.length, 2 * 3 * 3);
  assert.ok(zSlice[0].cells.every(([, , z]) => z <= 2));
});

test("groupCellsByLithology produces stable numeric groups and C-order cells", () => {
  const metadata = validMetadata({
    shape: [2, 2, 2],
    lithologies: [
      { id: 10, name: "Ten" },
      { id: 2, name: "Two" },
    ],
  });
  const groups = groupCellsByLithology(
    Uint16Array.from([10, 2, 10, 2, 2, 10, 2, 10]),
    metadata,
  );

  assert.deepEqual(groups, [
    {
      id: 2,
      name: "Two",
      cells: [
        [0, 0, 1],
        [0, 1, 1],
        [1, 0, 0],
        [1, 1, 0],
      ],
    },
    {
      id: 10,
      name: "Ten",
      cells: [
        [0, 0, 0],
        [0, 1, 0],
        [1, 0, 1],
        [1, 1, 1],
      ],
    },
  ]);
});

test("groupCellsByLithology labels unknown IDs without guessing", () => {
  const metadata = validMetadata({
    shape: [1, 1, 3],
    lithologies: [{ id: 2, name: "Known" }],
  });

  assert.deepEqual(
    groupCellsByLithology(Uint16Array.from([7, 2, 7]), metadata),
    [
      {
        id: 2,
        name: "Known",
        cells: [[0, 0, 1]],
      },
      {
        id: 7,
        name: "Lithology 7",
        cells: [[0, 0, 0], [0, 0, 2]],
      },
    ],
  );
});

test("coordinate and slice helpers reject out-of-range coordinates clearly", () => {
  const shape = [2, 3, 4];
  const extent = [0, 2, 0, 3, 0, 4];

  for (const operation of [
    () => volumeIndex(-1, 0, 0, shape),
    () => volumeIndex(2, 0, 0, shape),
    () => volumeIndex(0, 3, 0, shape),
    () => cellCenter(0, 0, 4, shape, extent),
    () => visibleCellRange(shape, { x: 2 }),
    () => visibleCellRange(shape, { y: -1 }),
    () => visibleCellRange(shape, { z: 4 }),
  ]) {
    assert.throws(operation, {
      name: "RangeError",
      message: /out of range/,
    });
  }
});
