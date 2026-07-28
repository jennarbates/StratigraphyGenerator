import assert from "node:assert/strict";
import test from "node:test";

import { munsellToHex } from "../munsell-color.js";
import { colorFor } from "./colors.js";


test("field-wall labels use their embedded Munsell display color", () => {
  assert.equal(
    colorFor("Locus 1042 (10YR 5/3 brown)"),
    munsellToHex("10YR 5/3"),
  );
});


test("non-Munsell material names keep stable categorical colors", () => {
  assert.equal(colorFor("clay fill"), colorFor("clay fill"));
  assert.match(colorFor("clay fill"), /^#[0-9a-f]{6}$/i);
});
