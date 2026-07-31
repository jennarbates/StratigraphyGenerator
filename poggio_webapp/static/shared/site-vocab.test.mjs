import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_FEATURE_TYPE,
  DRAWN_FEATURE_TYPES,
  featureTypeOptions,
} from "./site-vocab.mjs";

test("every feature key is unique", () => {
  const keys = DRAWN_FEATURE_TYPES.map((entry) => entry.key);
  assert.equal(new Set(keys).size, keys.length);
});

test("the default feature type is one of the offered keys", () => {
  assert.ok(DRAWN_FEATURE_TYPES.some((e) => e.key === DEFAULT_FEATURE_TYPE));
});

test("options carry the key as the value and the label as the text", () => {
  const html = featureTypeOptions("bone");
  assert.match(html, /<option value="bone" selected>Bone<\/option>/);
  assert.match(html, /<option value="stone">Stone<\/option>/);
});

test("exactly one option is selected", () => {
  const selected = featureTypeOptions("cut").match(/ selected>/g);
  assert.equal(selected.length, 1);
});

test("a value recorded before this vocabulary existed is preserved", () => {
  // Quietly rewriting one recorder's observation into a different one is
  // worse than showing a value the list no longer offers.
  const html = featureTypeOptions("rock/stone");
  assert.match(html, /value="rock\/stone" selected/);
  assert.match(html, /recorded earlier/);
  assert.equal(html.match(/ selected>/g).length, 1);
});

test("an unset value selects nothing rather than inventing a legacy option", () => {
  for (const empty of [undefined, null, ""]) {
    const html = featureTypeOptions(empty);
    assert.equal(html.match(/ selected>/g), null);
    assert.doesNotMatch(html, /recorded earlier/);
  }
});

test("a legacy value containing markup is escaped", () => {
  const html = featureTypeOptions('"><script>x</script>');
  assert.doesNotMatch(html, /<script>/);
});
