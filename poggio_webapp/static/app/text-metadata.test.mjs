// Run with: node poggio_webapp/static/app/text-metadata.test.mjs
import assert from "node:assert/strict";

import {
  acceptAllHighConfidenceProposals,
  applyVerifiedTextToDrawState,
  areTextCandidateReviewsComplete,
  buildVerifiedLocusChoices,
  buildVerifiedTextPayload,
  changeTextCandidateFinalValue,
  createTextReviewRows,
  flattenTextCandidates,
  getVerifiedLoci,
  setTextCandidateReviewStatus,
  verifiedLocusDisplayLabel,
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

test("verified loci produce chooser display labels", () => {
  assert.equal(
    verifiedLocusDisplayLabel({
      locusNumber: "1042",
      munsellRaw: "10YR 5/3",
      description: "brown silty soil",
    }),
    "1042 — 10YR 5/3 — brown silty soil",
  );
  assert.equal(
    verifiedLocusDisplayLabel({
      locusNumber: "1043",
      munsellRaw: "7.5YR 4/4",
      description: null,
    }),
    "1043 — 7.5YR 4/4",
  );
});

test("missing chooser metadata never renders null text", () => {
  const missingMunsell = verifiedLocusDisplayLabel({
    locusNumber: "1044",
    munsellRaw: null,
    description: "silty soil",
  });
  const missingDescription = verifiedLocusDisplayLabel({
    locusNumber: "1045",
    munsellRaw: "5YR 4/6",
    description: null,
  });

  assert.equal(missingMunsell, "1044 — Munsell unreadable — silty soil");
  assert.equal(missingDescription, "1045 — 5YR 4/6");
  assert.equal(missingMunsell.includes("null"), false);
  assert.equal(missingDescription.includes("null"), false);
});

test("chooser marks loci with existing top boundaries unavailable", () => {
  const choices = buildVerifiedLocusChoices(
    verifiedData({
      loci: [
        {
          locusNumber: "1042",
          munsellRaw: "10YR 5/3",
          description: "brown silty soil",
        },
        {
          locusNumber: "1043",
          munsellRaw: "7.5YR 4/4",
          description: null,
        },
      ],
    }),
    [
      { kind: "top", name: "1042", points: [] },
      { kind: "bottom", name: "1043", points: [] },
    ],
  );

  assert.equal(
    choices.find((choice) => choice.locusNumber === "1042").available,
    false,
  );
  assert.equal(
    choices.find((choice) => choice.locusNumber === "1043").available,
    true,
  );
});

test("chooser always includes manual entry and excludes invalid locus numbers", () => {
  const choices = buildVerifiedLocusChoices(verifiedData({
    loci: [
      { locusNumber: null, munsellRaw: null, description: null },
      { locusNumber: "", munsellRaw: "10YR 5/3", description: null },
      { locusNumber: "   ", munsellRaw: null, description: "blank" },
      { locusNumber: 1042, munsellRaw: null, description: "not a string" },
      { locusNumber: "1043", munsellRaw: null, description: null },
    ],
  }));

  assert.deepEqual(
    choices.filter((choice) => choice.kind === "verified")
      .map((choice) => choice.locusNumber),
    ["1043"],
  );
  assert.deepEqual(choices.at(-1), {
    kind: "manual",
    locusNumber: null,
    label: "Add a missing locus manually",
    munsellRaw: null,
    description: null,
    available: true,
  });
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

test("autofill fills a blank trench and preserves an existing face", () => {
  const result = applyVerifiedTextToDrawState(
    {
      trenchLabel: "",
      faceLabel: "Manual face",
      squareCm: null,
      lociMeta: {},
    },
    verifiedData(),
  );

  assert.equal(result.trenchLabel, "T104");
  assert.equal(result.faceLabel, "Manual face");
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

test("autofill creates locus metadata", () => {
  const result = applyVerifiedTextToDrawState(
    {
      trenchLabel: "",
      faceLabel: "",
      squareCm: null,
      lociMeta: {},
    },
    verifiedData(),
  );

  assert.deepEqual(result.lociMeta, {
    1042: {
      a: "10YR 5/3",
      b: "brown silty soil",
    },
  });
});

test("autofill preserves existing Munsell and locus descriptions", () => {
  const result = applyVerifiedTextToDrawState(
    {
      trenchLabel: "",
      faceLabel: "",
      squareCm: null,
      lociMeta: {
        1042: {
          a: "manual colour",
          b: "manual description",
        },
      },
    },
    verifiedData(),
  );

  assert.deepEqual(result.lociMeta, {
    1042: {
      a: "manual colour",
      b: "manual description",
    },
  });
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

test("replacement verified text fills remaining blanks only", () => {
  const firstVerified = verifiedData({
    document: {
      ...verifiedData().document,
      faceLabel: null,
    },
  });
  const secondVerified = verifiedData({
    document: {
      ...verifiedData().document,
      trenchLabel: "T999",
      faceLabel: "West face",
    },
  });
  const once = applyVerifiedTextToDrawState(
    {
      trenchLabel: "",
      faceLabel: "",
      squareCm: null,
      lociMeta: {},
    },
    firstVerified,
  );
  const twice = applyVerifiedTextToDrawState(once, secondVerified);

  assert.equal(twice.trenchLabel, "T104");
  assert.equal(twice.faceLabel, "West face");
});

test("input objects are not mutated", () => {
  const drawState = {
    trenchLabel: "",
    faceLabel: "",
    squareCm: null,
    lociMeta: {},
    clicks: [[5, 6], [7, 8], [9, 10]],
    boundaries: [{ name: "1042", points: [[1, 2]] }],
    features: [{
      feature_type: "rock/stone",
      description: "stone",
      points: [[11, 12], [13, 14], [15, 16]],
      closed: true,
    }],
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
  assert.deepEqual(result.clicks, drawSnapshot.clicks);
  assert.deepEqual(result.boundaries, drawSnapshot.boundaries);
  assert.deepEqual(result.features, drawSnapshot.features);
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
