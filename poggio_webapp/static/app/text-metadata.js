const DOCUMENT_SCALAR_FIELDS = Object.freeze([
  "trenchLabel",
  "faceLabel",
  "date",
  "gridSquareCm",
  "northArrowPresent",
]);

const DOCUMENT_LIST_FIELDS = Object.freeze([
  "illustrators",
  "gridTiePoints",
  "marginalia",
  "otherText",
]);

const LOCUS_FIELDS = Object.freeze([
  "locusNumber",
  "munsellRaw",
  "description",
]);

const REVIEW_STATUSES = new Set([
  "accepted",
  "corrected",
  "unreadable",
]);

const CONFIDENCE_LEVELS = new Set([
  "high",
  "medium",
  "low",
]);

function isRecord(value) {
  return value !== null
    && typeof value === "object"
    && !Array.isArray(value);
}

function isBlank(value) {
  return value === null
    || value === undefined
    || (typeof value === "string" && value.trim() === "");
}

function readableText(value) {
  return typeof value === "string" && value.trim() !== ""
    ? value.trim()
    : null;
}

function cloneValue(value, seen = new WeakMap()) {
  if (value === null || typeof value !== "object") return value;
  if (seen.has(value)) return seen.get(value);

  const clone = Array.isArray(value) ? [] : {};
  seen.set(value, clone);
  Object.keys(value).forEach((key) => {
    clone[key] = cloneValue(value[key], seen);
  });
  return clone;
}

function candidateRow(fieldPath, candidate) {
  if (!isRecord(candidate)) return null;
  return {
    fieldPath,
    raw: candidate.raw,
    proposed: candidate.proposed,
    confidence: candidate.confidence,
    bbox: Array.isArray(candidate.bbox) ? [...candidate.bbox] : candidate.bbox,
    notes: candidate.notes ?? null,
  };
}

/**
 * Flatten structured extraction candidates into deterministic review rows.
 */
export function flattenTextCandidates(candidateData) {
  if (!isRecord(candidateData)) return [];

  const rows = [];
  const documentData = isRecord(candidateData.document)
    ? candidateData.document
    : {};

  DOCUMENT_SCALAR_FIELDS.forEach((fieldName) => {
    const row = candidateRow(
      `document.${fieldName}`,
      documentData[fieldName],
    );
    if (row) rows.push(row);
  });

  DOCUMENT_LIST_FIELDS.forEach((fieldName) => {
    const candidates = Array.isArray(documentData[fieldName])
      ? documentData[fieldName]
      : [];
    candidates.forEach((candidate, index) => {
      const row = candidateRow(
        `document.${fieldName}.${index}`,
        candidate,
      );
      if (row) rows.push(row);
    });
  });

  const loci = Array.isArray(candidateData.loci) ? candidateData.loci : [];
  loci.forEach((locus, locusIndex) => {
    if (!isRecord(locus)) return;
    LOCUS_FIELDS.forEach((fieldName) => {
      const row = candidateRow(
        `loci.${locusIndex}.${fieldName}`,
        locus[fieldName],
      );
      if (row) rows.push(row);
    });
  });

  return rows;
}

function validBoundingBox(value) {
  if (!Array.isArray(value) || value.length !== 4) return null;
  if (!value.every(
    (part) => Number.isInteger(part) && part >= 0 && part <= 1000,
  )) {
    return null;
  }
  if (value[0] >= value[2] || value[1] >= value[3]) return null;
  return [...value];
}

function auditScalar(value) {
  return value === null
    || typeof value === "string"
    || typeof value === "number"
    || typeof value === "boolean"
    ? value
    : null;
}

function correctedValue(reviewRow) {
  const possibleKeys = [
    "correctedValue",
    "finalValue",
    "final",
    "value",
  ];
  const key = possibleKeys.find((name) => (
    Object.prototype.hasOwnProperty.call(reviewRow, name)
  ));
  return key === undefined ? null : reviewRow[key];
}

function normalizeFinalValue(fieldPath, value) {
  if (value === null || value === undefined) return null;

  if (fieldPath === "document.gridSquareCm") {
    if (typeof value === "string" && value.trim() === "") return null;
    const number = typeof value === "number" ? value : Number(value);
    return Number.isFinite(number) ? number : null;
  }

  if (fieldPath === "document.northArrowPresent") {
    if (value === true || value === false) return value;
    if (value === "true") return true;
    if (value === "false") return false;
    return null;
  }

  return readableText(value);
}

function finalForReview(candidate, reviewRow, fieldPath) {
  const status = REVIEW_STATUSES.has(reviewRow?.status)
    ? reviewRow.status
    : "unreadable";

  if (status === "unreadable") {
    return { status, final: null };
  }

  const sourceValue = status === "corrected"
    ? correctedValue(reviewRow)
    : candidate.proposed;
  return {
    status,
    final: normalizeFinalValue(fieldPath, sourceValue),
  };
}

function emptyVerifiedDocument() {
  return {
    trenchLabel: null,
    faceLabel: null,
    date: null,
    gridSquareCm: null,
    northArrowPresent: null,
    illustrators: [],
    gridTiePoints: [],
    marginalia: [],
    otherText: [],
  };
}

function emptyVerifiedLocus() {
  return {
    locusNumber: null,
    munsellRaw: null,
    description: null,
  };
}

function assignFinalValue(payload, fieldPath, final) {
  const documentMatch = fieldPath.match(
    /^document\.([A-Za-z][A-Za-z0-9]*)(?:\.(\d+))?$/,
  );
  if (documentMatch) {
    const [, fieldName, listIndex] = documentMatch;
    if (DOCUMENT_SCALAR_FIELDS.includes(fieldName) && listIndex === undefined) {
      payload.document[fieldName] = final;
      return;
    }
    if (DOCUMENT_LIST_FIELDS.includes(fieldName) && listIndex !== undefined) {
      payload.document[fieldName][Number(listIndex)] = final;
    }
    return;
  }

  const locusMatch = fieldPath.match(
    /^loci\.(\d+)\.(locusNumber|munsellRaw|description)$/,
  );
  if (!locusMatch) return;
  const locusIndex = Number(locusMatch[1]);
  if (locusIndex >= payload.loci.length) return;
  payload.loci[locusIndex][locusMatch[2]] = final;
}

/**
 * Build the backend's VerifiedFieldWallText contract from review decisions.
 */
export function buildVerifiedTextPayload(candidateData, reviewRows) {
  const candidateRows = flattenTextCandidates(candidateData);
  const reviewsByPath = new Map();
  if (Array.isArray(reviewRows)) {
    reviewRows.forEach((row) => {
      if (isRecord(row) && typeof row.fieldPath === "string") {
        reviewsByPath.set(row.fieldPath, row);
      }
    });
  }

  const locusCount = isRecord(candidateData) && Array.isArray(candidateData.loci)
    ? candidateData.loci.length
    : 0;
  const payload = {
    schemaVersion: 1,
    sheetType: "fieldwall",
    reviewCompleted: true,
    document: emptyVerifiedDocument(),
    loci: Array.from({ length: locusCount }, emptyVerifiedLocus),
    audit: [],
  };

  candidateRows.forEach((candidate) => {
    const review = reviewsByPath.get(candidate.fieldPath);
    const { status, final } = finalForReview(
      candidate,
      review,
      candidate.fieldPath,
    );
    assignFinalValue(payload, candidate.fieldPath, final);
    payload.audit.push({
      fieldPath: candidate.fieldPath,
      raw: typeof candidate.raw === "string" ? candidate.raw : null,
      proposed: auditScalar(candidate.proposed),
      final,
      status,
      confidence: CONFIDENCE_LEVELS.has(candidate.confidence)
        ? candidate.confidence
        : "low",
      bbox: validBoundingBox(candidate.bbox),
    });
  });

  DOCUMENT_LIST_FIELDS.forEach((fieldName) => {
    payload.document[fieldName] = payload.document[fieldName].filter(
      (value) => readableText(value) !== null,
    );
  });

  return payload;
}

function hasVerifiedContract(verifiedData) {
  return isRecord(verifiedData)
    && verifiedData.schemaVersion === 1
    && verifiedData.sheetType === "fieldwall"
    && verifiedData.reviewCompleted === true;
}

/**
 * Return verified locus metadata that has a readable final locus number.
 */
export function getVerifiedLoci(verifiedData) {
  if (!hasVerifiedContract(verifiedData) || !Array.isArray(verifiedData.loci)) {
    return [];
  }

  return verifiedData.loci.flatMap((locus) => {
    if (!isRecord(locus)) return [];
    const locusNumber = readableText(locus.locusNumber);
    if (locusNumber === null) return [];
    return [{
      locusNumber,
      munsellRaw: readableText(locus.munsellRaw),
      description: readableText(locus.description),
    }];
  });
}

/**
 * Apply readable verified text to empty draw fields without mutating state.
 */
export function applyVerifiedTextToDrawState(drawState, verifiedData) {
  const nextState = isRecord(drawState) ? cloneValue(drawState) : {};
  if (!hasVerifiedContract(verifiedData)) return nextState;

  const documentData = isRecord(verifiedData.document)
    ? verifiedData.document
    : {};
  const trenchLabel = readableText(documentData.trenchLabel);
  const faceLabel = readableText(documentData.faceLabel);
  const squareCm = documentData.gridSquareCm;

  if (isBlank(nextState.trenchLabel) && trenchLabel !== null) {
    nextState.trenchLabel = trenchLabel;
  }
  if (isBlank(nextState.faceLabel) && faceLabel !== null) {
    nextState.faceLabel = faceLabel;
  }
  if (
    (nextState.squareCm === null || nextState.squareCm === undefined)
    && typeof squareCm === "number"
    && Number.isFinite(squareCm)
    && squareCm > 0
  ) {
    nextState.squareCm = squareCm;
  }

  if (!isRecord(nextState.lociMeta)) nextState.lociMeta = {};
  getVerifiedLoci(verifiedData).forEach((locus) => {
    const current = isRecord(nextState.lociMeta[locus.locusNumber])
      ? nextState.lociMeta[locus.locusNumber]
      : {};
    const updated = { ...current };

    if (isBlank(updated.a) && locus.munsellRaw !== null) {
      updated.a = locus.munsellRaw;
    }
    if (isBlank(updated.b) && locus.description !== null) {
      updated.b = locus.description;
    }
    if (Object.keys(updated).length > 0) {
      Object.defineProperty(
        nextState.lociMeta,
        locus.locusNumber,
        {
          value: updated,
          writable: true,
          enumerable: true,
          configurable: true,
        },
      );
    }
  });

  return nextState;
}
