import assert from "node:assert/strict";
import test from "node:test";

import { demoCardModel, scenarioCopy, unavailableReason } from "./demo-mode.mjs";

const STOPS = {
  name: "stops",
  dataset: "T905",
  available: true,
  seeded: null,
};

const COMPLETE = {
  name: "complete",
  dataset: "T905",
  available: true,
  seeded: null,
};

function seeded(scenario, trench) {
  return { ...scenario, seeded: { trench, jobs: ["a", "b", "c", "d"] } };
}

test("with nothing seeded the card invites, and offers both scenarios", () => {
  const model = demoCardModel({ scenarios: [STOPS, COMPLETE] });
  assert.equal(model.heading, "Never used this before?");
  assert.equal(model.canRemove, false);
  assert.deepEqual(model.actions.map(a => a.label), [
    "See it refuse",
    "See it build",
  ]);
  assert.ok(model.actions.every(action => !action.disabled));
});

test("once seeded the card points at the trenches page and names the trench", () => {
  const model = demoCardModel({
    scenarios: [seeded(STOPS, "T905"), COMPLETE],
  });
  assert.equal(model.heading, "Demonstration loaded");
  assert.match(model.lede, /Open T905 on the trenches page/);
  assert.equal(model.canRemove, true);
  assert.deepEqual(model.trenches, ["T905"]);
});

test("both seeded reads as a list rather than a run-on", () => {
  const model = demoCardModel({
    scenarios: [seeded(STOPS, "T905"), seeded(COMPLETE, "T906")],
  });
  assert.match(model.lede, /Open T905 and T906 on the trenches page/);
  assert.deepEqual(model.trenches, ["T905", "T906"]);
});

test("an unavailable scenario is disabled and says why", () => {
  const model = demoCardModel({
    scenarios: [{ ...STOPS, available: false, dataset: "T111" }],
  });
  const [action] = model.actions;
  assert.equal(action.disabled, true);
  assert.match(action.reason, /T111/);
  // The reason replaces the sales pitch: a button you cannot press should not
  // still be advertising what it would have done.
  assert.equal(action.detail, "A trench with one corner elevation missing.");
  assert.match(action.reason, /never drawn under a real trench's label/);
});

test("an available scenario has no reason attached", () => {
  assert.equal(unavailableReason(STOPS), null);
});

test("a scenario this build has no wording for still gets a button", () => {
  const model = demoCardModel({
    scenarios: [{ name: "future", dataset: "T907", available: true, seeded: null }],
  });
  assert.equal(model.actions[0].label, "Load this demonstration");
  assert.equal(model.actions[0].disabled, false);
  assert.equal(scenarioCopy("future").detail, "");
});

test("a payload with no scenarios does not throw", () => {
  for (const payload of [null, undefined, {}, { scenarios: null }]) {
    const model = demoCardModel(payload);
    assert.deepEqual(model.actions, []);
    assert.equal(model.canRemove, false);
  }
});
