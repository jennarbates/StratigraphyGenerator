// Small DOM helpers shared across the front-end bundles.

/**
 * Escape text for interpolation into HTML.
 *
 * There were three of these: app/core/ui.js escaped & < > " and ',
 * visualizer/dom.js and app/stages/scan.js escaped the same set without the
 * apostrophe. This is the five-character version, so the two that were missing
 * ' now escape it too -- strictly more escaping, and &#39; renders as '.
 *
 * String(value), not String(value ?? ""): esc(undefined) yields the literal
 * text "undefined", which is what all three did. That is arguably a defect, but
 * it is a behaviour change rather than a deduplication and does not belong in
 * the same commit.
 */
export function esc(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[character]));
}

/**
 * Escape text for an HTML attribute value.
 *
 * The same rule; kept as a separate name because the call sites in
 * app/stages/scan.js read more clearly for it.
 */
export const escapeAttribute = esc;

export const $ = (id) => document.getElementById(id);
