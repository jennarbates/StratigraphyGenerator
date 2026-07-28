// Run with: node poggio_webapp/static/harris/core.test.mjs
import assert from "node:assert/strict";
import {
  addManualRelation,
  addManualUnit,
  applySavedResponse,
  createAutosaveController,
  filterUnits,
  formatSourceJobDisplay,
  groupSuggestionsByStatus,
  relationshipUnitOptions,
  removeCorrelation,
  removeRelation,
  removeUnitCascade,
  reviewSuggestionWithServer,
  saveRequestPayload,
  setCorrelation,
  summarizeUnitCascade,
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

function sourceUnit({
  id,
  label,
  description = null,
  unitType = "deposit",
  jobId = "111111111111",
  face = "North baulk",
  sourceLabel = label,
}) {
  return {
    id,
    label,
    unit_type: unitType,
    description,
    source_refs: [{
      job_id: jobId,
      schema_type: "FieldWallProfile",
      face,
      layer_index: 0,
      source_label: sourceLabel,
    }],
  };
}

function orderingSuggestion(overrides = {}) {
  return {
    id: "suggestion-00000000000a",
    suggestion_type: "ordering",
    status: "pending",
    younger_id: UNIT_A,
    older_id: UNIT_B,
    relation_kind: "above",
    correlation_unit_ids: [],
    reason: "Shared boundary",
    source_refs: [],
    ...overrides,
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

test("filters units across editable and source fields", () => {
  const units = [
    sourceUnit({
      id: UNIT_A,
      label: "Locus 7",
      description: "Occupation floor",
      jobId: "111111111111",
    }),
    sourceUnit({
      id: UNIT_B,
      label: "Cut 12",
      description: "Foundation trench",
      unitType: "cut",
      jobId: "222222222222",
      face: "East",
    }),
    unit(UNIT_C, "Manual fill"),
  ];
  const before = clone(units);

  assert.deepEqual(
    filterUnits(units, "  LOCUS  "),
    [units[0]],
  );
  assert.deepEqual(filterUnits(units, "foundation"), [units[1]]);
  assert.deepEqual(filterUnits(units, "CUT"), [units[1]]);
  assert.deepEqual(filterUnits(units, "222222222222"), [units[1]]);
  assert.deepEqual(filterUnits(units, ""), units);
  assert.deepEqual(units, before);
});

test("formats safe source display parts without retaining paths", () => {
  const display = formatSourceJobDisplay({
    job_id: "111111111111",
    schema_type: "FieldWallProfile",
    trench: "T123",
    faces: ["North baulk", "East"],
    unit_count: 2,
    extraction_path: "/private/jobs/111111111111/output.json",
    normalized_path: "/private/jobs/111111111111/clean.json",
  });

  assert.deepEqual(display, {
    jobId: "111111111111",
    schema: "Field wall profile",
    trench: "T123",
    faces: "North baulk, East",
    unitCount: "2 units",
  });
  assert.doesNotMatch(JSON.stringify(display), /private|path|output\.json/);
});

test("orders relationship unit options by human-readable label", () => {
  const units = [
    unit(UNIT_A, "10"),
    unit(UNIT_C, "Locus 2"),
    unit(UNIT_B, "2"),
  ];

  assert.deepEqual(
    relationshipUnitOptions(units).map(option => option.label),
    ["2", "10", "Locus 2"],
  );
  assert.deepEqual(
    relationshipUnitOptions(units).map(option => option.value),
    [UNIT_B, UNIT_A, UNIT_C],
  );
});

test("summarizes dependent records before cascading unit deletion", () => {
  const input = minimalMatrix({
    units: [unit(UNIT_A, "Locus 7"), unit(UNIT_B), unit(UNIT_C)],
    relations: [{
      id: RELATION_A,
      younger_id: UNIT_A,
      older_id: UNIT_B,
      kind: "above",
      evidence: "",
      source: "manual",
      notes: null,
    }],
    correlations: [{
      id: CORRELATION_A,
      unit_ids: [UNIT_A, UNIT_B, UNIT_C],
      notes: null,
    }],
    suggestions: [
      orderingSuggestion(),
      orderingSuggestion({
        id: "suggestion-00000000000b",
        status: "rejected",
      }),
    ],
  });

  const summary = summarizeUnitCascade(input, UNIT_A);

  assert.deepEqual(
    {
      relationCount: summary.relationCount,
      correlationCount: summary.correlationCount,
      pendingSuggestionCount: summary.pendingSuggestionCount,
    },
    {
      relationCount: 1,
      correlationCount: 1,
      pendingSuggestionCount: 1,
    },
  );
  assert.match(summary.message, /Locus 7/);
  assert.match(summary.message, /1 relationship/);
  assert.match(summary.message, /1 correlation group/);
  assert.match(summary.message, /1 pending suggestion/);
});

test("groups suggestions into pending, accepted, and rejected", () => {
  const pending = orderingSuggestion();
  const accepted = orderingSuggestion({
    id: "suggestion-00000000000b",
    status: "accepted",
  });
  const rejected = orderingSuggestion({
    id: "suggestion-00000000000c",
    status: "rejected",
  });
  const matrix = minimalMatrix({
    units: [unit(UNIT_A), unit(UNIT_B)],
    suggestions: [rejected, pending, accepted],
  });

  const grouped = groupSuggestionsByStatus(matrix);

  assert.deepEqual(grouped.pending, [pending]);
  assert.deepEqual(grouped.accepted, [accepted]);
  assert.deepEqual(grouped.rejected, [rejected]);
  assert.notEqual(grouped.pending[0], pending);
});

async function autosaveHarness(save) {
  const scheduled = [];
  const cancelled = [];
  const statuses = [];
  const controller = createAutosaveController({
    delayMs: 800,
    save,
    onStatus(status) {
      statuses.push(status);
    },
    scheduleTimeout(callback, delayMs) {
      const timer = { callback, delayMs };
      scheduled.push(timer);
      return timer;
    },
    cancelTimeout(timer) {
      cancelled.push(timer);
    },
  });
  return { controller, scheduled, cancelled, statuses };
}

await (async () => {
  const saves = [];
  const harness = await autosaveHarness(async () => {
    saves.push("saved");
  });

  assert.equal(harness.controller.schedule(), true);
  assert.equal(harness.controller.status, "unsaved");
  assert.equal(harness.scheduled.length, 1);
  assert.equal(harness.scheduled[0].delayMs, 800);

  assert.equal(harness.controller.schedule(), true);
  assert.equal(harness.cancelled.length, 1);
  assert.equal(harness.scheduled.length, 2);

  await harness.scheduled[1].callback();

  assert.deepEqual(saves, ["saved"]);
  assert.equal(harness.controller.status, "saved");
  assert.deepEqual(
    harness.statuses,
    ["unsaved", "unsaved", "saving", "saved"],
  );
  console.log("✓ debounces changes and reports save states");
})();

await (async () => {
  const conflict = Object.assign(new Error("newer work exists"), {
    status: 409,
  });
  const harness = await autosaveHarness(async () => {
    throw conflict;
  });

  harness.controller.schedule();
  await harness.scheduled[0].callback();

  assert.equal(harness.controller.status, "conflict");
  assert.equal(harness.controller.stopped, true);
  assert.equal(harness.controller.schedule(), false);
  assert.equal(harness.scheduled.length, 1);
  assert.deepEqual(
    harness.statuses,
    ["unsaved", "saving", "conflict"],
  );
  console.log("✓ conflict stops automatic retries");
})();

await (async () => {
  const input = minimalMatrix({
    revision: 2,
    units: [unit(UNIT_A), unit(UNIT_B)],
    suggestions: [orderingSuggestion()],
  });
  const before = clone(input);
  let resolveResponse;
  let requestPayload;
  const response = new Promise(resolve => {
    resolveResponse = resolve;
  });

  const review = reviewSuggestionWithServer(
    input,
    "suggestion-00000000000a",
    "accept",
    request => {
      requestPayload = request;
      return response;
    },
  );

  assert.deepEqual(input, before);
  assert.equal(input.suggestions[0].status, "pending");
  assert.deepEqual(requestPayload, {
    matrixId: "a1b2c3d4e5f6",
    suggestionId: "suggestion-00000000000a",
    action: "accept",
    revision: 2,
  });

  resolveResponse(minimalMatrix({
    revision: 3,
    units: [unit(UNIT_A), unit(UNIT_B)],
    suggestions: [orderingSuggestion({ status: "accepted" })],
  }));
  const reviewed = await review;

  assert.equal(reviewed.revision, 3);
  assert.equal(reviewed.suggestions[0].status, "accepted");
  assert.deepEqual(input, before);
  console.log("✓ review action waits for the saved server response");
})();

await (async () => {
  const input = minimalMatrix({
    revision: 2,
    units: [unit(UNIT_A), unit(UNIT_B)],
    suggestions: [orderingSuggestion()],
  });
  const before = clone(input);

  await assert.rejects(
    reviewSuggestionWithServer(
      input,
      "suggestion-00000000000a",
      "accept",
      async () => {
        throw new Error("Cycle detected");
      },
    ),
    /Cycle detected/,
  );
  assert.deepEqual(input, before);
  assert.equal(input.suggestions[0].status, "pending");

  await assert.rejects(
    reviewSuggestionWithServer(
      input,
      "suggestion-00000000000a",
      "reject",
      async () => clone(input),
    ),
    /newer revision/i,
  );
  assert.deepEqual(input, before);
  console.log("✓ failed or stale review preserves the current matrix");
})();
