/**
 * The site's drawn-feature vocabulary, mirrored from
 * poggio_webapp/pipeline/site_vocab.py.
 *
 * The browser cannot import the Python module, so this list is duplicated --
 * and tests/test_site_vocab_parity.py fails if the two ever drift apart. The
 * Python module is the source; edit it first.
 *
 * Values stored on a feature are the `key`, not the label: a key is an
 * identifier and must survive a wording change. Labels the recorder sees can
 * be reworded freely.
 */

export const DRAWN_FEATURE_TYPES = [
  { key: "stone", label: "Stone" },
  { key: "terracotta", label: "Terracotta (tile)" },
  { key: "bone", label: "Bone" },
  { key: "pottery", label: "Pottery/Ceramic" },
  { key: "architectural", label: "Architectural terracotta" },
  { key: "plaster", label: "Plaster" },
  { key: "metal", label: "Metal" },
  { key: "wall", label: "Wall" },
  { key: "cut", label: "Cut" },
  { key: "interface", label: "Interface / surface" },
  { key: "natural", label: "Natural" },
  { key: "void", label: "Void" },
  { key: "tree-stump", label: "Tree stump" },
  { key: "other", label: "Other" },
];

export const DEFAULT_FEATURE_TYPE = "stone";

function escapeAttribute(value) {
  return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/**
 * `<option>` markup for a feature-type select.
 *
 * A `selected` value that is not in the vocabulary is preserved as its own
 * leading option rather than being silently replaced. Jobs recorded before
 * this vocabulary existed carry values like "rock/stone", and quietly
 * rewriting one recorder's observation into a different one is worse than
 * showing a value the list no longer offers.
 */
export function featureTypeOptions(selected) {
  const known = DRAWN_FEATURE_TYPES.some((entry) => entry.key === selected);
  const legacy = (!known && selected)
    ? `<option value="${escapeAttribute(selected)}" selected>`
      + `${escapeAttribute(selected)} (recorded earlier)</option>`
    : "";
  return legacy + DRAWN_FEATURE_TYPES.map((entry) => (
    `<option value="${entry.key}"${entry.key === selected ? " selected" : ""}>`
    + `${entry.label}</option>`
  )).join("");
}
