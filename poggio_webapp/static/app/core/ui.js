export const $content = document.getElementById("content");
export const $steps = document.getElementById("steps");
export const $jobBadge = document.getElementById("jobBadge");

// Renders a friendly error banner with the raw traceback tucked into a
// collapsed <details> so it's available without being the message.
export function errorBanner(e) {
  let html = banner("err", e.message);
  if (e.detail) {
    const pre = document.createElement("pre");
    pre.textContent = e.detail;
    html += `<details class="err-detail"><summary>Technical detail</summary>` +
            pre.outerHTML + `</details>`;
  }
  return html;
}

export function banner(kind, text) {
  return `<div class="banner ${kind}">${text}</div>`;
}

// HTML-escape untrusted strings interpolated into innerHTML (e.g. locus
// numbers read off the sheet). Was referenced by the boundary-review legend
// but never defined — a latent ReferenceError hidden behind the old
// assign-route bug.
export function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

export function renderJsonTree(value, key = null, depth = 0) {
  const wrap = document.createElement("div");
  if (Array.isArray(value) || (value !== null && typeof value === "object")) {
    const isArr = Array.isArray(value);
    const entries = isArr ? value.map((v, i) => [i, v]) : Object.entries(value);
    const node = document.createElement("div");
    node.className = "jt-node";
    const toggle = document.createElement("span");
    toggle.className = "jt-toggle";
    toggle.textContent = entries.length ? "▾ " : "  ";
    const label = document.createElement("span");
    label.innerHTML = (key !== null ? `<span class="jt-key">${key}:</span> ` : "") +
      (isArr ? `[${entries.length}]` : `{${entries.length}}`);
    const head = document.createElement("div");
    head.appendChild(toggle);
    head.appendChild(label);
    node.appendChild(head);

    const children = document.createElement("div");
    children.className = "jt-children jt-indent";
    entries.forEach(([k, v]) => children.appendChild(renderJsonTree(v, isArr ? null : k, depth + 1)));
    node.appendChild(children);

    if (depth > 1) {
      node.classList.add("jt-collapsed");
      toggle.textContent = "▸ ";
    }
    toggle.addEventListener("click", () => {
      node.classList.toggle("jt-collapsed");
      toggle.textContent = node.classList.contains("jt-collapsed") ? "▸ " : "▾ ";
    });
    wrap.appendChild(node);
  } else {
    let cls = "jt-null", text = "null";
    if (typeof value === "string") { cls = "jt-str"; text = `"${value}"`; }
    else if (typeof value === "number") { cls = "jt-num"; text = String(value); }
    else if (typeof value === "boolean") { cls = "jt-bool"; text = String(value); }
    wrap.innerHTML = (key !== null ? `<span class="jt-key">${key}:</span> ` : "") +
      `<span class="${cls}">${text}</span>`;
  }
  return wrap;
}

export function dataTable(rows) {
  if (!rows || !rows.length) return "<p class='lede'>No rows.</p>";
  const cols = Object.keys(rows[0]);
  let html = "<div class='table-wrap'><table class='data-table'><thead><tr>";
  cols.forEach((c) => (html += `<th>${c}</th>`));
  html += "</tr></thead><tbody>";
  rows.forEach((r) => {
    html += "<tr>" + cols.map((c) => `<td>${r[c]}</td>`).join("") + "</tr>";
  });
  html += "</tbody></table></div>";
  return html;
}
