const HUE_CENTERS = {
  R: 0,
  YR: 30,
  Y: 60,
  GY: 95,
  G: 130,
  BG: 170,
  B: 210,
  PB: 250,
  P: 290,
  RP: 325,
};
const HUE_FAMILIES = Object.keys(HUE_CENTERS);

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function hueDegrees(family, hueNumber) {
  const familyIndex = HUE_FAMILIES.indexOf(family);
  const center = HUE_CENTERS[family];
  const relativeAmount = (hueNumber - 5) / 10;
  const adjacentIndex = relativeAmount < 0
    ? (familyIndex - 1 + HUE_FAMILIES.length) % HUE_FAMILIES.length
    : (familyIndex + 1) % HUE_FAMILIES.length;
  let adjacent = HUE_CENTERS[HUE_FAMILIES[adjacentIndex]];

  if (relativeAmount < 0 && adjacent > center) adjacent -= 360;
  if (relativeAmount >= 0 && adjacent < center) adjacent += 360;
  return (center + (Math.abs(relativeAmount) * (adjacent - center)) + 360) % 360;
}

/**
 * Read standard chromatic notation such as "10YR 5/3", neutral notation
 * such as "N 5/", or notation embedded in a locus/surface label.
 */
export function parseMunsellNotation(value) {
  if (typeof value !== "string") return null;
  const normalized = value.toUpperCase().trim();
  if (!normalized) return null;

  const chromatic = normalized.match(
    /(?:^|[\s_(])(\d+(?:\.\d+)?)\s*(YR|GY|BG|PB|RP|R|Y|G|B|P)[\s_]+(\d+(?:\.\d+)?)\s*(?:\/|[\s_])\s*(\d+(?:\.\d+)?)(?=$|[\s_)])/,
  );
  if (chromatic) {
    const hueNumber = Number(chromatic[1]);
    const valueNumber = Number(chromatic[3]);
    const chroma = Number(chromatic[4]);
    if (
      hueNumber >= 0
      && hueNumber <= 10
      && valueNumber >= 0
      && valueNumber <= 10
      && chroma >= 0
      && chroma <= 30
    ) {
      return {
        neutral: false,
        hueNumber,
        hueFamily: chromatic[2],
        value: valueNumber,
        chroma,
      };
    }
  }

  const neutral = normalized.match(
    /(?:^|[\s_(])N[\s_]*(\d+(?:\.\d+)?)\s*\/?(?=$|[\s_)])/,
  );
  if (!neutral) return null;
  const valueNumber = Number(neutral[1]);
  if (valueNumber < 0 || valueNumber > 10) return null;
  return {
    neutral: true,
    hueNumber: null,
    hueFamily: "N",
    value: valueNumber,
    chroma: 0,
  };
}

function hslToHex(hue, saturation, lightness) {
  const s = saturation / 100;
  const l = lightness / 100;
  const chroma = (1 - Math.abs((2 * l) - 1)) * s;
  const section = hue / 60;
  const secondary = chroma * (1 - Math.abs((section % 2) - 1));
  let red = 0;
  let green = 0;
  let blue = 0;

  if (section < 1) [red, green, blue] = [chroma, secondary, 0];
  else if (section < 2) [red, green, blue] = [secondary, chroma, 0];
  else if (section < 3) [red, green, blue] = [0, chroma, secondary];
  else if (section < 4) [red, green, blue] = [0, secondary, chroma];
  else if (section < 5) [red, green, blue] = [secondary, 0, chroma];
  else [red, green, blue] = [chroma, 0, secondary];

  const offset = l - (chroma / 2);
  return `#${[red, green, blue].map((component) => (
    Math.round((component + offset) * 255)
      .toString(16)
      .padStart(2, "0")
  )).join("")}`;
}

/**
 * Approximate a physical Munsell chip as an sRGB display color.
 *
 * This intentionally returns a fallback for unparseable text. Displays,
 * lighting, and the physical Munsell system differ, so the result is a useful
 * visual correspondence rather than a colorimetric replacement for a chip.
 */
export function munsellToHex(value, fallback = null) {
  const parsed = parseMunsellNotation(value);
  if (!parsed) return fallback;

  const lightness = clamp(8 + (parsed.value * 8), 4, 92);
  if (parsed.neutral || parsed.chroma === 0) {
    return hslToHex(0, 0, lightness);
  }

  const saturation = clamp(12 + (parsed.chroma * 6.5), 0, 82);
  return hslToHex(
    hueDegrees(parsed.hueFamily, parsed.hueNumber),
    saturation,
    lightness,
  );
}
