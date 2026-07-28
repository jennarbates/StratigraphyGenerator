function readableLocusNumber(value) {
  if (typeof value !== "string") return null;
  const locusNumber = value.trim();
  return locusNumber || null;
}

/**
 * Return the existing top boundary for a locus, or add it when the locus is
 * selected for the first time.
 *
 * The drawing stage keeps its boundary array mutable, so this helper follows
 * the same convention and returns the index that should become active.
 */
export function ensureLocusTopBoundary(boundaries, locusNumber) {
  if (!Array.isArray(boundaries)) {
    return { index: -1, created: false };
  }

  const name = readableLocusNumber(locusNumber);
  if (name === null) {
    return { index: -1, created: false };
  }

  const existingIndex = boundaries.findIndex(
    (boundary) => (
      boundary
      && boundary.kind === "top"
      && readableLocusNumber(boundary.name) === name
    ),
  );
  if (existingIndex >= 0) {
    return { index: existingIndex, created: false };
  }

  boundaries.push({ kind: "top", name, points: [] });
  return { index: boundaries.length - 1, created: true };
}
