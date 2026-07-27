// Run with: node poggio_webapp/static/app/text-metadata.test.mjs
import assert from "node:assert/strict";

import {
  acceptAllHighConfidenceProposals,
  applyVerifiedTextToDrawState,
  areTextCandidateReviewsComplete,
  buildVerifiedTextPayload,
  changeTextCandidateFinalValue,
  createTextReviewRows,
  flattenTextCandidates,
  getVerifiedLoci,
  setTextCandidateReviewStatus,
} from "./text-metadata.js";

function test(name, callback) {
  callback();
  console.log(`✓ ${name}`);
}

function candidate(raw, proposed, confidence = "high") {
  return {
    raw,
    proposed,
    confidence,
    bbox: [10, 20, 100, 120],
    notes: null,
  };
}

function candidateData() {
  return {
    schemaVersion: 1,
    sheetType: "fieldwall",
    document: {
      trenchLabel: candidate("T 104", "T104"),
      faceLabel: candidate("S baulk", "South baulk", "medium"),
      date: null,
      gridSquareCm: candidate("20 cm", 20),
      northArrowPresent: candidate("N arrow", true),
      illustrators: [
        candidate("A Recorder", "A. Recorder"),
        candidate("B Recorder", "B. Recorder"),
      ],
      gridTiePoints: [],
      marginalia: [],
      otherText: [candidate("unclear", null, "low")],
    },
    loci: [
      {
        locusNumber: candidate("1042", "1042"),
        munsellRaw: candidate("10 yr 5 / 3", "10YR 5/3", "medium"),
        description: candidate("brown soil", "brown soil"),
      },
      {
        locusNumber: candidate("?", null, "low"),
        munsellRaw: candidate("7.5YR 4/2", "7.5YR 4/2"),
        description: null,
      },
    ],
  };
}

function verifiedData(overrides = {}) {
  return {
    schemaVersion: 1,
    sheetType: "fieldwall",
    reviewCompleted: true,
    document: {
      trenchLabel: "T104",
      faceLabel: "South baulk",
      date: null,
      gridSquareCm: 20,
      northArrowPresent: true,
      illustrators: [],
      gridTiePoints: [],
      marginalia: [],
      otherText: [],
    },
    loci: [
      {
        locusNumber: "1042",
        munsellRaw: "10YR 5/3",
        description: "brown silty soil",
      },
      {
        locusNumber: null,
        munsellRaw: "7.5YR 4/2",
        description: "unidentified layer",
      },
    ],
    audit: [],
    ...overrides,
  };
}

test("candidate flattening produces stable field paths", () => {
  const rows = flattenTextCandidates(candidateData());

  assert.deepEqual(
    rows.map((row) => row.fieldPath),
    [
      "document.trenchLabel",
      "document.faceLabel",
      "document.gridSquareCm",
      "document.northArrowPresent",
      "document.illustrators.0",
      "document.illustrators.1",
      "document.otherText.0",
      "loci.0.locusNumber",
      "loci.0.munsellRaw",
      "loci.0.description",
      "loci.1.locusNumber",
      "loci.1.munsellRaw",
    ],
  );
});

test("lists receive stable numeric paths", () => {
  const data = candidateData();
  data.document.illustrators.splice(
    1,
    0,
    candidate("Inserted", "Inserted"),
  );

  assert.deepEqual(
    flattenTextCandidates(data)
      .filter((row) => row.fieldPath.startsWith("document.illustrators"))
      .map((row) => row.fieldPath),
    [
      "document.illustrators.0",
      "document.illustrators.1",
      "document.illustrators.2",
    ],
  );
});

test("completion requires every displayed candidate to have a review status", () => {
  const data = candidateData();
  const candidates = flattenTextCandidates(data);
  const reviews = createTextReviewRows(data);

  assert.equal(
    areTextCandidateReviewsComplete(candidates, reviews),
    false,
  );

  const completed = reviews.map((row, index) => ({
    ...row,
    status: index % 2 === 0 ? "accepted" : "unreadable",
  }));
  assert.equal(
    areTextCandidateReviewsComplete(candidates, completed),
    true,
  );
});

test("bulk acceptance affects only unreviewed high-confidence proposals", () => {
  const data = candidateData();
  const candidates = flattenTextCandidates(data);
  const reviews = createTextReviewRows(data);
  const alreadyCorrected = candidates.find(
    (row) => row.fieldPath === "document.trenchLabel",
  );
  reviews[candidates.indexOf(alreadyCorrected)] = {
    fieldPath: alreadyCorrected.fieldPath,
    status: "corrected",
    finalValue: "T-104",
  };

  const result = acceptAllHighConfidenceProposals(candidates, reviews);
  const byPath = new Map(result.map((row) => [row.fieldPath, row]));

  assert.deepEqual(byPath.get("document.trenchLabel"), {
    fieldPath: "document.trenchLabel",
    status: "corrected",
    finalValue: "T-104",
  });
  assert.equal(
    byPath.get("document.gridSquareCm").status,
    "accepted",
  );
  assert.equal(
    byPath.get("document.faceLabel").status,
    null,
  );
  assert.equal(
    byPath.get("document.otherText.0").status,
    null,
  );
});

test("editing an accepted value makes it corrected", () => {
  const row = flattenTextCandidates(candidateData()).find(
    (candidateRow) => candidateRow.fieldPath === "document.trenchLabel",
  );
  const accepted = setTextCandidateReviewStatus(row, null, "accepted");
  const edited = changeTextCandidateFinalValue(accepted, accepted, "T-104");

  assert.equal(accepted.status, "accepted");
  assert.equal(accepted.finalValue, "T104");
  assert.equal(edited.status, "corrected");
  assert.equal(edited.finalValue, "T-104");
});

test("unreadable decisions clear the final output", () => {
  const data = candidateData();
  const candidateRow = flattenTextCandidates(data).find(
    (row) => row.fieldPath === "document.trenchLabel",
  );
  const unreadable = setTextCandidateReviewStatus(
    candidateRow,
    {
      fieldPath: candidateRow.fieldPath,
      status: "corrected",
      finalValue: "T-104",
    },
    "unreadable",
  );
  const payload = buildVerifiedTextPayload(data, [unreadable]);

  assert.equal(unreadable.finalValue, null);
  assert.equal(payload.document.trenchLabel, null);
  assert.equal(
    payload.audit.find(
      (row) => row.fieldPath === candidateRow.fieldPath,
    ).final,
    null,
  );
});

test("empty candidate lists are already complete and build an empty payload", () => {
  const data = {
    schemaVersion: 1,
    sheetType: "fieldwall",
    document: {},
    loci: [],
  };
  const reviews = createTextReviewRows(data);
  const payload = buildVerifiedTextPayload(data, reviews);

  assert.deepEqual(reviews, []);
  assert.equal(areTextCandidateReviewsComplete(data, reviews), true);
  assert.deepEqual(payload.document, {
    trenchLabel: null,
    faceLabel: null,
    date: null,
    gridSquareCm: null,
    northArrowPresent: null,
    illustrators: [],
    gridTiePoints: [],
    marginalia: [],
    otherText: [],
  });
  assert.deepEqual(payload.loci, []);
  assert.deepEqual(payload.audit, []);
});

test("accepted, corrected, and unreadable reviews build the verified contract", () => {
  const data = candidateData();
  const reviews = flattenTextCandidates(data).map((row) => ({
    fieldPath: row.fieldPath,
    status: "accepted",
  }));
  reviews.find(
    (row) => row.fieldPath === "document.faceLabel",
  ).status = "corrected";
  reviews.find(
    (row) => row.fieldPath === "document.faceLabel",
  ).correctedValue = "West face";
  reviews.find(
    (row) => row.fieldPath === "document.otherText.0",
  ).status = "unreadable";
  reviews.find(
    (row) => row.fieldPath === "loci.1.locusNumber",
  ).status = "unreadable";

  const payload = buildVerifiedTextPayload(data, reviews);

  assert.deepEqual(payload.document, {
    trenchLabel: "T104",
    faceLabel: "West face",
    date: null,
    gridSquareCm: 20,
    northArrowPresent: true,
    illustrators: ["A. Recorder", "B. Recorder"],
    gridTiePoints: [],
    marginalia: [],
    otherText: [],
  });
  assert.deepEqual(payload.loci, [
    {
      locusNumber: "1042",
      munsellRaw: "10YR 5/3",
      description: "brown soil",
    },
    {
      locusNumber: null,
      munsellRaw: "7.5YR 4/2",
      description: null,
    },
  ]);
  assert.equal(payload.schemaVersion, 1);
  assert.equal(payload.sheetType, "fieldwall");
  assert.equal(payload.reviewCompleted, true);
});

test("audit entries preserve raw and proposed values", () => {
  const data = candidateData();
  const payload = buildVerifiedTextPayload(data, [
    {
      fieldPath: "document.trenchLabel",
      status: "corrected",
      correctedValue: "T-104",
    },
  ]);
  const audit = payload.audit.find(
    (row) => row.fieldPath === "document.trenchLabel",
  );

  assert.deepEqual(audit, {
    fieldPath: "document.trenchLabel",
    raw: "T 104",
    proposed: "T104",
    final: "T-104",
    status: "corrected",
    confidence: "high",
    bbox: [10, 20, 100, 120],
  });
  assert.equal(
    payload.audit.find(
      (row) => row.fieldPath === "document.faceLabel",
    ).final,
    null,
  );
});

test("loci without a final locus number are excluded from choices", () => {
  assert.deepEqual(getVerifiedLoci(verifiedData()), [
    {
      locusNumber: "1042",
      munsellRaw: "10YR 5/3",
      description: "brown silty soil",
    },
  ]);
});

test("autofill fills blanks and preserves manual values", () => {
  const drawState = {
    trenchLabel: "Manual trench",
    faceLabel: "   ",
    squareCm: null,
    lociMeta: {
      1042: {
        a: "manual colour",
        b: "",
      },
    },
  };

  const result = applyVerifiedTextToDrawState(drawState, verifiedData());

  assert.deepEqual(result, {
    trenchLabel: "Manual trench",
    faceLabel: "South baulk",
    squareCm: 20,
    lociMeta: {
      1042: {
        a: "manual colour",
        b: "brown silty soil",
      },
    },
  });
});

test("autofill does not replace an existing grid size", () => {
  const result = applyVerifiedTextToDrawState(
    {
      trenchLabel: "",
      faceLabel: "",
      squareCm: 25,
      lociMeta: {},
    },
    verifiedData(),
  );

  assert.equal(result.squareCm, 25);
});

test("autofill is idempotent", () => {
  const original = {
    trenchLabel: "",
    faceLabel: "",
    squareCm: null,
    lociMeta: {},
  };
  const once = applyVerifiedTextToDrawState(original, verifiedData());
  const twice = applyVerifiedTextToDrawState(once, verifiedData());

  assert.deepEqual(twice, once);
});

test("input objects are not mutated", () => {
  const drawState = {
    trenchLabel: "",
    faceLabel: "",
    squareCm: null,
    lociMeta: {},
    boundaries: [{ name: "1042", points: [[1, 2]] }],
  };
  const verified = verifiedData();
  const drawSnapshot = structuredClone(drawState);
  const verifiedSnapshot = structuredClone(verified);
  const result = applyVerifiedTextToDrawState(drawState, verified);

  assert.deepEqual(drawState, drawSnapshot);
  assert.deepEqual(verified, verifiedSnapshot);
  assert.notEqual(result, drawState);
  assert.notEqual(result.lociMeta, drawState.lociMeta);
  assert.notEqual(result.boundaries, drawState.boundaries);
});

test("unreadable and malformed verified data are ignored safely", () => {
  const drawState = {
    trenchLabel: "",
    faceLabel: "",
    squareCm: null,
    lociMeta: {},
  };
  const unreadable = verifiedData({
    document: {
      trenchLabel: null,
      faceLabel: "",
      gridSquareCm: null,
    },
    loci: [
      {
        locusNumber: "1042",
        munsellRaw: null,
        description: null,
      },
    ],
  });

  assert.deepEqual(
    applyVerifiedTextToDrawState(drawState, unreadable),
    drawState,
  );
  assert.deepEqual(
    applyVerifiedTextToDrawState(drawState, { loci: "not-a-list" }),
    drawState,
  );
  assert.deepEqual(getVerifiedLoci(null), []);
});
