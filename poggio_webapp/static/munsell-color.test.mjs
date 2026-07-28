import assert from "node:assert/strict";
import test from "node:test";

import {
  munsellToHex,
  parseMunsellNotation,
} from "./munsell-color.js";


test("parses common Munsell soil notation", () => {
  assert.deepEqual(parseMunsellNotation("10YR 5/3"), {
    neutral: false,
    hueNumber: 10,
    hueFamily: "YR",
    value: 5,
    chroma: 3,
  });
  assert.deepEqual(parseMunsellNotation("7.5 yr 4 / 4"), {
    neutral: false,
    hueNumber: 7.5,
    hueFamily: "YR",
    value: 4,
    chroma: 4,
  });
});


test("finds Munsell notation inside field-wall surface names", () => {
  assert.equal(
    munsellToHex("Locus 1042 (10YR 5/3 brown)"),
    munsellToHex("10YR 5/3"),
  );
  assert.equal(
    munsellToHex("Locus_1042_10YR_5_3"),
    munsellToHex("10YR 5/3"),
  );
});


test("value changes display lightness and chroma changes saturation", () => {
  assert.notEqual(munsellToHex("10YR 3/3"), munsellToHex("10YR 7/3"));
  assert.notEqual(munsellToHex("10YR 5/2"), munsellToHex("10YR 5/8"));
});


test("different hue families produce different display colors", () => {
  assert.notEqual(munsellToHex("5YR 5/4"), munsellToHex("5BG 5/4"));
});


test("neutral notation produces grey", () => {
  const neutral = munsellToHex("N 5/");
  assert.match(neutral, /^#([0-9a-f]{2})\1\1$/);
});


test("invalid or absent notation uses the caller's fallback", () => {
  assert.equal(munsellToHex("brown soil", "#123456"), "#123456");
  assert.equal(munsellToHex(null, "#abcdef"), "#abcdef");
  assert.equal(munsellToHex("12YR 5/3", "#fedcba"), "#fedcba");
});
