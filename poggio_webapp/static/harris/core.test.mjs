// Run with: node poggio_webapp/static/harris/core.test.mjs
import assert from "node:assert/strict";
import {
  addManualRelation,
  addManualUnit,
  applySavedResponse,
  removeCorrelation,
  removeRelation,
  removeUnitCascade,
  saveRequestPayload,
  setCorrelation,
  updateMatrixMetadata,
  updateUnit,
  validateMatrixPayload,
} from "./core.mjs";

const UNIT_A = "unit-00000000000a";
const UNIT_B = "unit-00000000000b";
const UNIT_C = "unit-00000000000c";
const RELATION_A = "rel-00000000000a";
const CORRELATION_A = "corr-00000000000a";
const CORRELATION_B = "corr-00000000000b";

function test(name, callback) {
  callback();
  console.log(`✓ ${name}`);
}

function unit(id, label = id) {
  return {
    id,
    label,
    unit_type: "deposit",
    description: null,
    source_refs: [],
  };
}

function minimalMatrix(overrides = {}) {
  return {
    schema_version: 1,
    matrix_id: "a1b2c3d4e5f6",
    revision: 0,
    title: "T123 Harris Matrix",
    site: "Poggio Civitate",
    trench: "T123",
    notes: "",
    source_job_ids: [],
    units: [],
    relations: [],
    correlations: [],
    suggestions: [],
    created_at: "2026-07-28T08:00:00+00:00",
    updated_at: "2026-07-28T08:00:00+00:00",
    ...overrides,
  };
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function assertImmutable(input, operation) {
  const before = clone(input);
  const result = operation(input);

  assert.notEqual(result, input);
  assert.deepEqual(input, before);
  return result;
}

test("validates and copies a valid minimal payload", () => {
  const input = minimalMatrix();
  const result = assertImmutable(input, validateMatrixPayload);

  assert.deepEqual(result, input);
});

test("rejects unknown schema versions and malformed arrays", () => {
  assert.throws(
    () => validateMatrixPayload(minimalMatrix({ schema_version: 2 })),
    /schema version/i,
  );

  for (const field of [
    "source_job_ids",
    "units",
    "relations",
    "correlations",
    "suggestions",
  ]) {
    assert.throws(
      () => validateMatrixPayload(minimalMatrix({ [field]: {} })),
      new RegExp(field),
    );
  }
});

test("trims editable metadata without mutating the matrix", () => {
  const input = minimalMatrix({ notes: " existing notes " });
  const result = assertImmutable(input, matrix => updateMatrixMetadata(
    matrix,
    {
      title: "  Updated matrix  ",
      site: "  Poggio Civitate ",
      trench: " T123  ",
    },
  ));

  assert.equal(result.title, "Updated matrix");
  assert.equal(result.site, "Poggio Civitate");
  assert.equal(result.trench, "T123");
  assert.equal(result.notes, " existing notes ");
});

test("adds and edits a manual unit immutably", () => {
  const input = minimalMatrix();
  const added = assertImmutable(input, matrix => addManualUnit(
    matrix,
    {
      label: "  Locus 7  ",
      unit_type: "deposit",
      description: " Occupation layer ",
      source_refs: [{ job_id: "ffffffffffff" }],
    },
    UNIT_A,
  ));

  assert.deepEqual(added.units, [{
    id: UNIT_A,
    label: "Locus 7",
    unit_type: "deposit",
    description: "Occupation layer",
    source_refs: [],
  }]);

  const updated = assertImmutable(added, matrix => updateUnit(
    matrix,
    UNIT_A,
    { label: "  Locus 8 ", unit_type: "natural", description: null },
  ));
  assert.deepEqual(updated.units[0], {
    id: UNIT_A,
    label: "Locus 8",
    unit_type: "natural",
    description: null,
    source_refs: [],
  });
});

test("removes a unit and its dependent local state", () => {
  const input = minimalMatrix({
    units: [unit(UNIT_A), unit(UNIT_B), unit(UNIT_C)],
    relations: [
      {
        id: RELATION_A,
        younger_id: UNIT_A,
        older_id: UNIT_B,
        kind: "above",
        evidence: "",
        source: "manual",
        notes: null,
      },
    ],
    correlations: [{
      id: CORRELATION_A,
      unit_ids: [UNIT_A, UNIT_B, UNIT_C],
      notes: null,
    }],
    suggestions: [
      {
        id: "suggestion-00000000000a",
        suggestion_type: "ordering",
        status: "pending",
        younger_id: UNIT_A,
        older_id: UNIT_C,
        relation_kind: "above",
        correlation_unit_ids: [],
        reason: "Shared boundary",
        source_refs: [],
      },
      {
        id: "suggestion-00000000000b",
        suggestion_type: "correlation",
        status: "pending",
        younger_id: null,
        older_id: null,
        relation_kind: null,
        correlation_unit_ids: [UNIT_A, UNIT_B],
        reason: "Matching label",
        source_refs: [],
      },
      {
        id: "suggestion-00000000000c",
        suggestion_type: "ordering",
        status: "rejected",
        younger_id: UNIT_A,
        older_id: UNIT_C,
        relation_kind: "above",
        correlation_unit_ids: [],
        reason: "Reviewed",
        source_refs: [],
      },
    ],
  });

  const result = assertImmutable(
    input,
    matrix => removeUnitCascade(matrix, UNIT_A),
  );

  assert.deepEqual(result.units.map(item => item.id), [UNIT_B, UNIT_C]);
  assert.deepEqual(result.relations, []);
  assert.deepEqual(result.correlations, [{
    id: CORRELATION_A,
    unit_ids: [UNIT_B, UNIT_C],
    notes: null,
  }]);
  assert.deepEqual(
    result.suggestions.map(suggestion => suggestion.id),
    ["suggestion-00000000000c"],
  );

  const droppedGroup = removeUnitCascade(
    minimalMatrix({
      units: [unit(UNIT_A), unit(UNIT_B)],
      correlations: [{
        id: CORRELATION_A,
        unit_ids: [UNIT_A, UNIT_B],
        notes: null,
      }],
    }),
    UNIT_A,
  );
  assert.deepEqual(droppedGroup.correlations, []);
});

test("adds and removes a manual relation immutably", () => {
  const input = minimalMatrix({ units: [unit(UNIT_A), unit(UNIT_B)] });
  const added = assertImmutable(input, matrix => addManualRelation(
    matrix,
    {
      younger_id: UNIT_A,
      older_id: UNIT_B,
      kind: "cuts",
      evidence: "  Section drawing  ",
      notes: null,
    },
    RELATION_A,
  ));

  assert.deepEqual(added.relations, [{
    id: RELATION_A,
    younger_id: UNIT_A,
    older_id: UNIT_B,
    kind: "cuts",
    evidence: "Section drawing",
    source: "manual",
    notes: null,
  }]);

  const removed = assertImmutable(
    added,
    matrix => removeRelation(matrix, RELATION_A),
  );
  assert.deepEqual(removed.relations, []);
});

test("rejects missing and self-referential relation endpoints", () => {
  const input = minimalMatrix({ units: [unit(UNIT_A), unit(UNIT_B)] });

  assert.throws(
    () => addManualRelation(
      input,
      { younger_id: UNIT_A, older_id: UNIT_C, kind: "above" },
      RELATION_A,
    ),
    /existing unit/i,
  );
  assert.throws(
    () => addManualRelation(
      input,
      { younger_id: UNIT_A, older_id: UNIT_A, kind: "above" },
      RELATION_A,
    ),
    /different/i,
  );
});

test("adds and removes a correlation immutably", () => {
  const input = minimalMatrix({ units: [unit(UNIT_A), unit(UNIT_B)] });
  const added = assertImmutable(
    input,
    matrix => setCorrelation(
      matrix,
      [UNIT_B, UNIT_A, UNIT_B],
      CORRELATION_A,
      " Same deposit ",
    ),
  );

  assert.deepEqual(added.correlations, [{
    id: CORRELATION_A,
    unit_ids: [UNIT_A, UNIT_B],
    notes: "Same deposit",
  }]);

  const removed = assertImmutable(
    added,
    matrix => removeCorrelation(matrix, CORRELATION_A),
  );
  assert.deepEqual(removed.correlations, []);

  assert.throws(
    () => setCorrelation(input, [UNIT_A, UNIT_C], CORRELATION_A, null),
    /existing units/i,
  );
  assert.throws(
    () => setCorrelation(input, [UNIT_A, UNIT_A], CORRELATION_A, null),
    /two distinct/i,
  );
});

test("merges overlapping correlations and retains a stored ID", () => {
  const input = minimalMatrix({
    units: [unit(UNIT_A), unit(UNIT_B), unit(UNIT_C)],
    correlations: [
      {
        id: CORRELATION_B,
        unit_ids: [UNIT_B, UNIT_C],
        notes: "Second",
      },
      {
        id: CORRELATION_A,
        unit_ids: [UNIT_A, UNIT_B],
        notes: "First",
      },
    ],
  });

  const result = assertImmutable(
    input,
    matrix => setCorrelation(
      matrix,
      [UNIT_A, UNIT_C],
      "corr-00000000000c",
      "Merged",
    ),
  );

  assert.deepEqual(result.correlations, [{
    id: CORRELATION_A,
    unit_ids: [UNIT_A, UNIT_B, UNIT_C],
    notes: "Merged",
  }]);
});

test("builds a save payload with the current revision", () => {
  const input = minimalMatrix({
    revision: 7,
    import_warnings: ["UI-only response metadata"],
  });
  const result = assertImmutable(input, saveRequestPayload);

  assert.equal(result.revision, 7);
  assert.equal("import_warnings" in result, false);
  assert.deepEqual(Object.keys(result), [
    "schema_version",
    "matrix_id",
    "revision",
    "title",
    "site",
    "trench",
    "notes",
    "source_job_ids",
    "units",
    "relations",
    "correlations",
    "suggestions",
    "created_at",
    "updated_at",
  ]);
});

test("applies a saved response with a newer revision", () => {
  const current = minimalMatrix({ revision: 3, title: "Before" });
  const saved = minimalMatrix({ revision: 4, title: "After" });
  const currentBefore = clone(current);
  const savedBefore = clone(saved);

  const result = applySavedResponse(current, saved);

  assert.notEqual(result, current);
  assert.notEqual(result, saved);
  assert.equal(result.revision, 4);
  assert.equal(result.title, "After");
  assert.deepEqual(current, currentBefore);
  assert.deepEqual(saved, savedBefore);
});

test("rejects saved responses for another matrix or an old revision", () => {
  const current = minimalMatrix({ revision: 3 });

  assert.throws(
    () => applySavedResponse(
      current,
      minimalMatrix({ matrix_id: "ffffffffffff", revision: 4 }),
    ),
    /matrix ID/i,
  );
  assert.throws(
    () => applySavedResponse(current, minimalMatrix({ revision: 3 })),
    /newer revision/i,
  );
  assert.throws(
    () => applySavedResponse(current, minimalMatrix({ revision: 2 })),
    /newer revision/i,
  );
});

test("keeps user-controlled HTML-looking strings as inert state data", () => {
  const htmlLooking = '<img src=x onerror="globalThis.pwned=true">';
  const withMetadata = updateMatrixMetadata(
    minimalMatrix(),
    { title: htmlLooking, notes: htmlLooking },
  );
  const withUnit = addManualUnit(
    withMetadata,
    { label: htmlLooking, unit_type: "unknown", description: htmlLooking },
    UNIT_A,
  );

  assert.equal(withUnit.title, htmlLooking);
  assert.equal(withUnit.notes, htmlLooking);
  assert.equal(withUnit.units[0].label, htmlLooking);
  assert.equal(withUnit.units[0].description, htmlLooking);
  assert.equal(globalThis.pwned, undefined);
});
