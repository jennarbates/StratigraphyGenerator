export const $ = (id) => document.getElementById(id);

export function esc(value) {
  return String(value).replace(
    /[&<>"]/g,
    (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
    })[char],
  );
}
