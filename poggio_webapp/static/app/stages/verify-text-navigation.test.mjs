// Run with: node poggio_webapp/static/app/stages/verify-text-navigation.test.mjs
import assert from "node:assert/strict";

const elements = new Map();
function element(id = null) {
  return {
    id,
    innerHTML: "",
    textContent: "",
    style: {},
    children: [],
    appendChild(child) {
      this.children.push(child);
      if (child.id) elements.set(child.id, child);
      return child;
    },
    addEventListener() {},
    setAttribute() {},
    remove() {},
  };
}

globalThis.document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, element(id));
    return elements.get(id);
  },
  createElement() {
    return element();
  },
};
globalThis.window = { scrollTo() {} };

const {
  STEPS,
  invalidateDownstream,
  state,
} = await import("../core/state.js");
const { stepEnabled } = await import("../core/navigation.js");
const { completeVerifyText } = await import("./verify-text.js");

const FRESH_VERIFY_TEXT = {
  status: "not_started",
  taskId: null,
  candidates: null,
  verified: null,
  error: null,
  appliedToDraw: false,
};

function test(name, callback) {
  return Promise.resolve()
    .then(callback)
    .then(() => console.log(`✓ ${name}`));
}

function resetCompletion() {
  state.completed = {};
  state.verifyText = structuredClone(FRESH_VERIFY_TEXT);
}

await test("the verification step follows preprocessing and precedes drawing", () => {
  const ids = STEPS.map((step) => step.id);
  assert.equal(ids.indexOf("verifyText"), ids.indexOf("preprocess") + 1);
  assert.equal(ids.indexOf("draw"), ids.indexOf("verifyText") + 1);
  assert.equal(STEPS.find((step) => step.id === "verifyText").title, "Check the writing");
});

await test("fresh state contains the complete verification object", () => {
  assert.deepEqual(state.verifyText, FRESH_VERIFY_TEXT);
});

await test("drawing stays blocked until verification is complete", () => {
  resetCompletion();
  state.completed.scan = true;
  state.completed.preprocess = true;
  assert.equal(stepEnabled("verifyText"), true);
  assert.equal(stepEnabled("draw"), false);
});

await test("field-wall skip calls the skip route and unlocks drawing", async () => {
  resetCompletion();
  state.jobId = "field-wall-job";
  state.sheetType = "fieldwall";
  state.completed.scan = true;
  state.completed.preprocess = true;
  const calls = [];

  await completeVerifyText(async (path, payload) => {
    calls.push({ path, payload });
    return { status: "skipped" };
  });

  assert.deepEqual(calls, [{
    path: "/api/jobs/field-wall-job/text-verification/skip",
    payload: {},
  }]);
  assert.equal(state.verifyText.status, "skipped");
  assert.equal(state.completed.verifyText, true);
  assert.equal(stepEnabled("draw"), true);
});

await test("illustrator continue completes without an API request", async () => {
  resetCompletion();
  state.sheetType = "illustrator";
  state.completed.scan = true;
  state.completed.preprocess = true;
  let requestCount = 0;

  await completeVerifyText(async () => {
    requestCount += 1;
    throw new Error("illustrator should not make a request");
  });

  assert.equal(requestCount, 0);
  assert.equal(state.verifyText.status, "skipped");
  assert.equal(state.completed.verifyText, true);
  assert.equal(stepEnabled("draw"), true);
});

await test("preprocessing invalidation resets verification without deleting traced geometry", () => {
  resetCompletion();
  state.completed.scan = true;
  state.completed.preprocess = true;
  state.completed.verifyText = true;
  state.completed.draw = true;
  state.verifyText = {
    status: "verified",
    taskId: "task-123",
    candidates: { labels: ["1042"] },
    verified: { loci: [{ locusNumber: "1042" }] },
    error: "old error",
    appliedToDraw: true,
  };
  const drawSnapshot = structuredClone(state.draw);
  drawSnapshot.boundaries = [{
    name: "1042",
    points: [[10, 20], [30, 40]],
  }];
  state.draw = structuredClone(drawSnapshot);

  const stale = invalidateDownstream("preprocess");

  assert.equal(stale.has("verifyText"), true);
  assert.deepEqual(state.verifyText, FRESH_VERIFY_TEXT);
  assert.deepEqual(state.draw, drawSnapshot);
  assert.equal(state.completed.draw, true);
});
