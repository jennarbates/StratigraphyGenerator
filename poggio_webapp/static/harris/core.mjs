const SCHEMA_VERSION = 1;

const MATRIX_FIELDS = [
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
];

const MATRIX_ID = /^[0-9a-f]{12}$/;
const UNIT_ID = /^unit-[0-9a-f]{12}$/;
const RELATION_ID = /^rel-[0-9a-f]{12}$/;
const CORRELATION_ID = /^corr-[0-9a-f]{12}$/;
const SUGGESTION_ID = /^suggestion-[0-9a-f]{12}$/;

const UNIT_TYPES = new Set([
  "deposit",
  "cut",
  "structure",
  "interface",
  "natural",
  "unknown",
]);
const RELATION_KINDS = new Set([
  "above",
  "cuts",
  "fills",
  "precedes",
  "other",
]);
const RELATION_SOURCES = new Set(["manual", "suggestion"]);
const SUGGESTION_TYPES = new Set(["ordering", "correlation"]);
const SUGGESTION_STATUSES = new Set([
  "pending",
  "accepted",
  "rejected",
]);
const SOURCE_SCHEMA_TYPES = new Set([
  "FieldWallProfile",
  "ArchaeologicalDiagram",
]);

function copyData(value) {
  if (Array.isArray(value)) {
    return value.map(copyData);
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, copyData(item)]),
    );
  }
  return value;
}

function invalid(path, requirement) {
  throw new TypeError(`${path} ${requirement}.`);
}

function requireObject(value, path) {
  if (
    value === null
    || typeof value !== "object"
    || Array.isArray(value)
  ) {
    invalid(path, "must be an object");
  }
}

function requireArray(value, path) {
  if (!Array.isArray(value)) {
    invalid(path, "must be an array");
  }
}

function requireString(value, path) {
  if (typeof value !== "string") {
    invalid(path, "must be a string");
  }
}

function requireNullableString(value, path) {
  if (value !== null && typeof value !== "string") {
    invalid(path, "must be a string or null");
  }
}

function requireIdentifier(value, pattern, path) {
  if (typeof value !== "string" || !pattern.test(value)) {
    invalid(path, "has an invalid identifier");
  }
}

function requireEnum(value, allowed, path) {
  if (!allowed.has(value)) {
    invalid(path, "has an unsupported value");
  }
}

function requireNonNegativeInteger(value, path) {
  if (!Number.isInteger(value) || value < 0) {
    invalid(path, "must be a non-negative integer");
  }
}

function validateSourceRef(sourceRef, path) {
  requireObject(sourceRef, path);
  requireIdentifier(sourceRef.job_id, MATRIX_ID, `${path}.job_id`);
  requireEnum(
    sourceRef.schema_type,
    SOURCE_SCHEMA_TYPES,
    `${path}.schema_type`,
  );
  requireString(sourceRef.face, `${path}.face`);
  requireNonNegativeInteger(sourceRef.layer_index, `${path}.layer_index`);
  requireNullableString(sourceRef.source_label, `${path}.source_label`);
}

function validateUnit(unit, path) {
  requireObject(unit, path);
  requireIdentifier(unit.id, UNIT_ID, `${path}.id`);
  requireString(unit.label, `${path}.label`);
  if (unit.label.trim() === "") {
    invalid(`${path}.label`, "must not be blank");
  }
  requireEnum(unit.unit_type, UNIT_TYPES, `${path}.unit_type`);
  requireNullableString(unit.description, `${path}.description`);
  requireArray(unit.source_refs, `${path}.source_refs`);
  unit.source_refs.forEach((sourceRef, index) => {
    validateSourceRef(sourceRef, `${path}.source_refs[${index}]`);
  });
}

function validateRelation(relation, path) {
  requireObject(relation, path);
  requireIdentifier(relation.id, RELATION_ID, `${path}.id`);
  requireIdentifier(relation.younger_id, UNIT_ID, `${path}.younger_id`);
  requireIdentifier(relation.older_id, UNIT_ID, `${path}.older_id`);
  requireEnum(relation.kind, RELATION_KINDS, `${path}.kind`);
  requireString(relation.evidence, `${path}.evidence`);
  requireEnum(relation.source, RELATION_SOURCES, `${path}.source`);
  requireNullableString(relation.notes, `${path}.notes`);
}

function validateCorrelation(correlation, path) {
  requireObject(correlation, path);
  requireIdentifier(correlation.id, CORRELATION_ID, `${path}.id`);
  requireArray(correlation.unit_ids, `${path}.unit_ids`);
  correlation.unit_ids.forEach((unitId, index) => {
    requireIdentifier(unitId, UNIT_ID, `${path}.unit_ids[${index}]`);
  });
  if (new Set(correlation.unit_ids).size < 2) {
    invalid(`${path}.unit_ids`, "must contain at least two distinct units");
  }
  requireNullableString(correlation.notes, `${path}.notes`);
}

function validateSuggestion(suggestion, path) {
  requireObject(suggestion, path);
  requireIdentifier(suggestion.id, SUGGESTION_ID, `${path}.id`);
  requireEnum(
    suggestion.suggestion_type,
    SUGGESTION_TYPES,
    `${path}.suggestion_type`,
  );
  requireEnum(
    suggestion.status,
    SUGGESTION_STATUSES,
    `${path}.status`,
  );
  requireArray(
    suggestion.correlation_unit_ids,
    `${path}.correlation_unit_ids`,
  );
  suggestion.correlation_unit_ids.forEach((unitId, index) => {
    requireIdentifier(
      unitId,
      UNIT_ID,
      `${path}.correlation_unit_ids[${index}]`,
    );
  });

  if (suggestion.suggestion_type === "ordering") {
    requireIdentifier(
      suggestion.younger_id,
      UNIT_ID,
      `${path}.younger_id`,
    );
    requireIdentifier(
      suggestion.older_id,
      UNIT_ID,
      `${path}.older_id`,
    );
    requireEnum(
      suggestion.relation_kind,
      RELATION_KINDS,
      `${path}.relation_kind`,
    );
    if (suggestion.correlation_unit_ids.length !== 0) {
      invalid(
        `${path}.correlation_unit_ids`,
        "must be empty for an ordering suggestion",
      );
    }
  } else {
    if (
      suggestion.younger_id !== null
      || suggestion.older_id !== null
      || suggestion.relation_kind !== null
    ) {
      invalid(
        path,
        "must use null ordering fields for a correlation suggestion",
      );
    }
    if (new Set(suggestion.correlation_unit_ids).size < 2) {
      invalid(
        `${path}.correlation_unit_ids`,
        "must contain at least two distinct units",
      );
    }
  }

  requireString(suggestion.reason, `${path}.reason`);
  requireArray(suggestion.source_refs, `${path}.source_refs`);
  suggestion.source_refs.forEach((sourceRef, index) => {
    validateSourceRef(sourceRef, `${path}.source_refs[${index}]`);
  });
}

function editableMatrix(matrix) {
  return validateMatrixPayload(matrix);
}

function trimmedString(value, path, { allowBlank = true } = {}) {
  requireString(value, path);
  const trimmed = value.trim();
  if (!allowBlank && trimmed === "") {
    invalid(path, "must not be blank");
  }
  return trimmed;
}

function nullableTrimmedString(value, path) {
  requireNullableString(value, path);
  return value === null ? null : value.trim();
}

function existingUnitIds(matrix) {
  return new Set(matrix.units.map(unit => unit.id));
}

function requireUnusedId(items, id, pattern, path) {
  requireIdentifier(id, pattern, path);
  if (items.some(item => item.id === id)) {
    invalid(path, "is already in use");
  }
}

export function validateMatrixPayload(raw) {
  requireObject(raw, "matrix");
  if (raw.schema_version !== SCHEMA_VERSION) {
    throw new RangeError(
      `Unsupported Harris Matrix schema version: ${String(
        raw.schema_version,
      )}.`,
    );
  }

  requireIdentifier(raw.matrix_id, MATRIX_ID, "matrix.matrix_id");
  requireNonNegativeInteger(raw.revision, "matrix.revision");
  for (const field of ["title", "site", "trench", "notes"]) {
    requireString(raw[field], `matrix.${field}`);
  }
  requireString(raw.created_at, "matrix.created_at");
  requireString(raw.updated_at, "matrix.updated_at");

  requireArray(raw.source_job_ids, "matrix.source_job_ids");
  raw.source_job_ids.forEach((jobId, index) => {
    requireIdentifier(
      jobId,
      MATRIX_ID,
      `matrix.source_job_ids[${index}]`,
    );
  });

  requireArray(raw.units, "matrix.units");
  raw.units.forEach((unit, index) => {
    validateUnit(unit, `matrix.units[${index}]`);
  });

  requireArray(raw.relations, "matrix.relations");
  raw.relations.forEach((relation, index) => {
    validateRelation(relation, `matrix.relations[${index}]`);
  });

  requireArray(raw.correlations, "matrix.correlations");
  raw.correlations.forEach((correlation, index) => {
    validateCorrelation(correlation, `matrix.correlations[${index}]`);
  });

  requireArray(raw.suggestions, "matrix.suggestions");
  raw.suggestions.forEach((suggestion, index) => {
    validateSuggestion(suggestion, `matrix.suggestions[${index}]`);
  });

  return copyData(raw);
}

export function updateMatrixMetadata(matrix, patch) {
  const updated = editableMatrix(matrix);
  requireObject(patch, "metadata patch");

  for (const field of ["title", "site", "trench"]) {
    if (Object.hasOwn(patch, field)) {
      updated[field] = trimmedString(
        patch[field],
        `metadata patch.${field}`,
      );
    }
  }
  if (Object.hasOwn(patch, "notes")) {
    requireString(patch.notes, "metadata patch.notes");
    updated.notes = patch.notes;
  }
  return updated;
}

export function addManualUnit(matrix, values, id) {
  const updated = editableMatrix(matrix);
  requireObject(values, "unit values");
  requireUnusedId(updated.units, id, UNIT_ID, "unit ID");

  const label = trimmedString(
    values.label,
    "unit values.label",
    { allowBlank: false },
  );
  const unitType = values.unit_type ?? "unknown";
  requireEnum(unitType, UNIT_TYPES, "unit values.unit_type");
  const description = values.description === undefined
    ? null
    : nullableTrimmedString(
      values.description,
      "unit values.description",
    );

  updated.units.push({
    id,
    label,
    unit_type: unitType,
    description,
    source_refs: [],
  });
  return updated;
}

export function updateUnit(matrix, unitId, patch) {
  const updated = editableMatrix(matrix);
  requireObject(patch, "unit patch");
  const unitIndex = updated.units.findIndex(unit => unit.id === unitId);
  if (unitIndex === -1) {
    invalid("unit ID", "must identify an existing unit");
  }

  const nextUnit = { ...updated.units[unitIndex] };
  if (Object.hasOwn(patch, "label")) {
    nextUnit.label = trimmedString(
      patch.label,
      "unit patch.label",
      { allowBlank: false },
    );
  }
  if (Object.hasOwn(patch, "unit_type")) {
    requireEnum(patch.unit_type, UNIT_TYPES, "unit patch.unit_type");
    nextUnit.unit_type = patch.unit_type;
  }
  if (Object.hasOwn(patch, "description")) {
    nextUnit.description = nullableTrimmedString(
      patch.description,
      "unit patch.description",
    );
  }
  updated.units[unitIndex] = nextUnit;
  return updated;
}

export function removeUnitCascade(matrix, unitId) {
  const updated = editableMatrix(matrix);
  updated.units = updated.units.filter(unit => unit.id !== unitId);
  updated.relations = updated.relations.filter(
    relation => (
      relation.younger_id !== unitId
      && relation.older_id !== unitId
    ),
  );
  updated.correlations = updated.correlations.flatMap(correlation => {
    const unitIds = correlation.unit_ids.filter(id => id !== unitId);
    return unitIds.length < 2
      ? []
      : [{ ...correlation, unit_ids: unitIds }];
  });
  updated.suggestions = updated.suggestions.filter(suggestion => {
    if (suggestion.status !== "pending") {
      return true;
    }
    return (
      suggestion.younger_id !== unitId
      && suggestion.older_id !== unitId
      && !suggestion.correlation_unit_ids.includes(unitId)
    );
  });
  return updated;
}

export function addManualRelation(matrix, values, id) {
  const updated = editableMatrix(matrix);
  requireObject(values, "relation values");
  requireUnusedId(updated.relations, id, RELATION_ID, "relation ID");

  const units = existingUnitIds(updated);
  if (
    !units.has(values.younger_id)
    || !units.has(values.older_id)
  ) {
    invalid(
      "relation endpoints",
      "must both identify an existing unit",
    );
  }
  if (values.younger_id === values.older_id) {
    invalid(
      "relation endpoints",
      "must identify different younger and older units",
    );
  }

  const kind = values.kind ?? "above";
  requireEnum(kind, RELATION_KINDS, "relation values.kind");
  const evidence = values.evidence === undefined
    ? ""
    : trimmedString(values.evidence, "relation values.evidence");
  const notes = values.notes === undefined
    ? null
    : nullableTrimmedString(values.notes, "relation values.notes");

  updated.relations.push({
    id,
    younger_id: values.younger_id,
    older_id: values.older_id,
    kind,
    evidence,
    source: "manual",
    notes,
  });
  return updated;
}

export function removeRelation(matrix, relationId) {
  const updated = editableMatrix(matrix);
  updated.relations = updated.relations.filter(
    relation => relation.id !== relationId,
  );
  return updated;
}

export function setCorrelation(matrix, unitIds, id, notes) {
  const updated = editableMatrix(matrix);
  requireArray(unitIds, "correlation unit IDs");
  const distinctUnitIds = [...new Set(unitIds)].sort();
  if (distinctUnitIds.length < 2) {
    invalid(
      "correlation unit IDs",
      "must contain at least two distinct units",
    );
  }
  const units = existingUnitIds(updated);
  if (distinctUnitIds.some(unitId => !units.has(unitId))) {
    invalid(
      "correlation unit IDs",
      "must all identify existing units",
    );
  }
  distinctUnitIds.forEach((unitId, index) => {
    requireIdentifier(
      unitId,
      UNIT_ID,
      `correlation unit IDs[${index}]`,
    );
  });
  requireIdentifier(id, CORRELATION_ID, "correlation ID");

  const selected = new Set(distinctUnitIds);
  const overlapping = updated.correlations.filter(
    correlation => correlation.unit_ids.some(unitId => selected.has(unitId)),
  );
  const overlappingIds = new Set(
    overlapping.map(correlation => correlation.id),
  );

  if (
    overlapping.length === 0
    && updated.correlations.some(correlation => correlation.id === id)
  ) {
    invalid("correlation ID", "is already in use");
  }

  const mergedUnitIds = new Set(distinctUnitIds);
  overlapping.forEach(correlation => {
    correlation.unit_ids.forEach(unitId => mergedUnitIds.add(unitId));
  });

  let retainedId = id;
  let retainedNotes = null;
  if (overlapping.length > 0) {
    retainedId = overlapping
      .map(correlation => correlation.id)
      .sort()[0];
    retainedNotes = overlapping.find(
      correlation => correlation.id === retainedId
    ).notes;
  }

  const merged = {
    id: retainedId,
    unit_ids: [...mergedUnitIds].sort(),
    notes: notes === undefined
      ? retainedNotes
      : nullableTrimmedString(notes, "correlation notes"),
  };
  updated.correlations = updated.correlations
    .filter(correlation => !overlappingIds.has(correlation.id))
    .concat(merged)
    .sort((first, second) => first.id.localeCompare(second.id));
  return updated;
}

export function removeCorrelation(matrix, correlationId) {
  const updated = editableMatrix(matrix);
  updated.correlations = updated.correlations.filter(
    correlation => correlation.id !== correlationId,
  );
  return updated;
}

export function saveRequestPayload(matrix) {
  const validated = validateMatrixPayload(matrix);
  return Object.fromEntries(
    MATRIX_FIELDS.map(field => [field, copyData(validated[field])]),
  );
}

export function applySavedResponse(current, saved) {
  const currentMatrix = validateMatrixPayload(current);
  const savedMatrix = validateMatrixPayload(saved);
  if (savedMatrix.matrix_id !== currentMatrix.matrix_id) {
    throw new Error(
      "Saved response matrix ID does not match the current matrix ID.",
    );
  }
  if (savedMatrix.revision <= currentMatrix.revision) {
    throw new Error(
      "Saved response must have a strictly newer revision.",
    );
  }
  return savedMatrix;
}
