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

function hasReviewStatus(row) {
  return isRecord(row) && REVIEW_STATUSES.has(row.status);
}

function candidatesFrom(value) {
  return Array.isArray(value) ? value : flattenTextCandidates(value);
}

/**
 * Convert a [xMin, yMin, xMax, yMax] box from normalized 0-1000
 * coordinates to source-image pixel coordinates.
 *
 * The input is never changed. Edges outside the normalized range are clamped
 * to the image, while malformed or empty boxes return null.
 */
export function normalizedBboxToPixels(bbox, imageWidth, imageHeight) {
  if (
    !Array.isArray(bbox)
    || bbox.length !== 4
    || !bbox.every((coordinate) => Number.isFinite(coordinate))
    || !Number.isFinite(imageWidth)
    || !Number.isFinite(imageHeight)
    || imageWidth <= 0
    || imageHeight <= 0
  ) {
    return null;
  }

  const [xMin, yMin, xMax, yMax] = bbox;
  if (xMin >= xMax || yMin >= yMax) return null;

  const clampNormalized = (coordinate) => (
    Math.min(1000, Math.max(0, coordinate))
  );
  const pixels = [
    Math.floor((clampNormalized(xMin) / 1000) * imageWidth),
    Math.floor((clampNormalized(yMin) / 1000) * imageHeight),
    Math.ceil((clampNormalized(xMax) / 1000) * imageWidth),
    Math.ceil((clampNormalized(yMax) / 1000) * imageHeight),
  ];
  pixels[0] = Math.min(imageWidth, Math.max(0, pixels[0]));
  pixels[1] = Math.min(imageHeight, Math.max(0, pixels[1]));
  pixels[2] = Math.min(imageWidth, Math.max(0, pixels[2]));
  pixels[3] = Math.min(imageHeight, Math.max(0, pixels[3]));

  return pixels[0] < pixels[2] && pixels[1] < pixels[3]
    ? pixels
    : null;
}

/**
 * Add context around a pixel box without allowing the crop to leave the
 * source image.
 */
export function padPixelBbox(bbox, imageWidth, imageHeight, padding) {
  if (
    !Array.isArray(bbox)
    || bbox.length !== 4
    || !bbox.every((coordinate) => Number.isFinite(coordinate))
    || !Number.isFinite(imageWidth)
    || !Number.isFinite(imageHeight)
    || imageWidth <= 0
    || imageHeight <= 0
  ) {
    return null;
  }

  const [xMin, yMin, xMax, yMax] = bbox;
  if (xMin >= xMax || yMin >= yMax) return null;
  const safePadding = Number.isFinite(padding) ? Math.max(0, padding) : 0;
  const padded = [
    Math.max(0, Math.floor(xMin - safePadding)),
    Math.max(0, Math.floor(yMin - safePadding)),
    Math.min(imageWidth, Math.ceil(xMax + safePadding)),
    Math.min(imageHeight, Math.ceil(yMax + safePadding)),
  ];

  return padded[0] < padded[2] && padded[1] < padded[3]
    ? padded
    : null;
}

/**
 * Create editable review rows without changing the extraction candidates.
 *
 * When verified data is supplied, its audit trail restores previously saved
 * decisions. Otherwise every candidate starts unreviewed with the proposal in
 * the editable final-value field.
 */
export function createTextReviewRows(candidateData, verifiedData = null) {
  const auditByPath = new Map();
  if (isRecord(verifiedData) && Array.isArray(verifiedData.audit)) {
    verifiedData.audit.forEach((entry) => {
      if (isRecord(entry) && typeof entry.fieldPath === "string") {
        auditByPath.set(entry.fieldPath, entry);
      }
    });
  }

  return flattenTextCandidates(candidateData).map((candidate) => {
    const saved = auditByPath.get(candidate.fieldPath);
    if (!hasReviewStatus(saved)) {
      return {
        fieldPath: candidate.fieldPath,
        status: null,
        finalValue: candidate.proposed ?? null,
      };
    }
    return {
      fieldPath: candidate.fieldPath,
      status: saved.status,
      finalValue: saved.status === "unreadable"
        ? null
        : (saved.final ?? null),
    };
  });
}

/**
 * A review is complete only when every displayed candidate has a decision.
 * An extraction with no candidates is therefore complete.
 */
export function areTextCandidateReviewsComplete(
  candidateDataOrRows,
  reviewRows,
) {
  const candidates = candidatesFrom(candidateDataOrRows);
  const reviewedPaths = new Set(
    Array.isArray(reviewRows)
      ? reviewRows
        .filter(hasReviewStatus)
        .map((row) => row.fieldPath)
      : [],
  );
  return candidates.every((candidate) => reviewedPaths.has(candidate.fieldPath));
}

/**
 * Apply one explicit review decision and return a new row.
 */
export function setTextCandidateReviewStatus(candidate, reviewRow, status) {
  if (!isRecord(candidate) || typeof candidate.fieldPath !== "string") {
    throw new TypeError("candidate must have a fieldPath");
  }
  if (!REVIEW_STATUSES.has(status)) {
    throw new RangeError(`Unknown review status: ${status}`);
  }

  const next = {
    ...(isRecord(reviewRow) ? reviewRow : {}),
    fieldPath: candidate.fieldPath,
    status,
  };
  if (status === "accepted") {
    next.finalValue = candidate.proposed ?? null;
  } else if (status === "unreadable") {
    next.finalValue = null;
  } else if (!Object.prototype.hasOwnProperty.call(next, "finalValue")) {
    next.finalValue = candidate.proposed ?? null;
  }
  return next;
}

/**
 * Store an edited final value. Editing an accepted proposal makes the review
 * an explicit correction; typing after "unreadable" likewise makes the value
 * readable again.
 */
export function changeTextCandidateFinalValue(
  candidate,
  reviewRow,
  finalValue,
) {
  if (!isRecord(candidate) || typeof candidate.fieldPath !== "string") {
    throw new TypeError("candidate must have a fieldPath");
  }
  const previousStatus = hasReviewStatus(reviewRow)
    ? reviewRow.status
    : null;
  return {
    ...(isRecord(reviewRow) ? reviewRow : {}),
    fieldPath: candidate.fieldPath,
    status: previousStatus === "accepted" || previousStatus === "unreadable"
      ? "corrected"
      : previousStatus,
    finalValue,
  };
}

/**
 * Accept only high-confidence candidates that do not yet have a decision.
 * Medium/low-confidence and already reviewed rows are returned unchanged.
 */
export function acceptAllHighConfidenceProposals(
  candidateDataOrRows,
  reviewRows,
) {
  const candidates = candidatesFrom(candidateDataOrRows);
  const reviewsByPath = new Map();
  if (Array.isArray(reviewRows)) {
    reviewRows.forEach((row) => {
      if (isRecord(row) && typeof row.fieldPath === "string") {
        reviewsByPath.set(row.fieldPath, row);
      }
    });
  }

  return candidates.map((candidate) => {
    const existing = reviewsByPath.get(candidate.fieldPath) || {
      fieldPath: candidate.fieldPath,
      status: null,
      finalValue: candidate.proposed ?? null,
    };
    if (candidate.confidence !== "high" || hasReviewStatus(existing)) {
      return { ...existing };
    }
    return setTextCandidateReviewStatus(candidate, existing, "accepted");
  });
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
 * Format one verified locus for the tracing chooser.
 */
export function verifiedLocusDisplayLabel(locus) {
  if (!isRecord(locus)) return null;
  const locusNumber = readableText(locus.locusNumber);
  if (locusNumber === null) return null;

  const munsell = readableText(locus.munsellRaw) ?? "Munsell unreadable";
  const description = readableText(locus.description);
  return [locusNumber, munsell, description]
    .filter((value) => value !== null)
    .join(" · ");
}

/**
 * Build chooser rows from verified text and the boundaries already traced.
 *
 * The manual row is always last so a missing model result can still be added.
 */
export function buildVerifiedLocusChoices(verifiedData, boundaries = []) {
  const usedLocusNumbers = new Set(
    Array.isArray(boundaries)
      ? boundaries.flatMap((boundary) => {
        if (!isRecord(boundary) || boundary.kind !== "top") return [];
        const name = readableText(boundary.name);
        return name === null ? [] : [name];
      })
      : [],
  );
  const seenLocusNumbers = new Set();
  const choices = [];

  getVerifiedLoci(verifiedData).forEach((locus) => {
    if (seenLocusNumbers.has(locus.locusNumber)) return;
    seenLocusNumbers.add(locus.locusNumber);
    choices.push({
      kind: "verified",
      locusNumber: locus.locusNumber,
      label: verifiedLocusDisplayLabel(locus),
      munsellRaw: locus.munsellRaw,
      description: locus.description,
      available: !usedLocusNumbers.has(locus.locusNumber),
    });
  });

  choices.push({
    kind: "manual",
    locusNumber: null,
    label: "Add a missing locus manually",
    munsellRaw: null,
    description: null,
    available: true,
  });
  return choices;
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
