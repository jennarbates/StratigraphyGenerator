/**
 * Before/after comparison slider.
 *
 * Progressive enhancement: the page contains two ordinary <figure> elements
 * side by side. With JavaScript off that is a perfectly readable comparison,
 * and it is what the README shows. With JavaScript on the two are stacked and
 * a draggable divider wipes between them, which is the only way to see a small
 * rotation — a few degrees of skew is invisible in two separate stills.
 *
 * Keyboard: focus the divider and use the arrow keys, Home, or End.
 */

const STEP = 2;
const BIG_STEP = 10;

function clamp(value) {
  return Math.max(0, Math.min(100, value));
}

function build(root) {
  const figures = [...root.querySelectorAll("figure")];
  if (figures.length !== 2) return;

  const [before, after] = figures;
  const beforeImg = before.querySelector("img");
  const afterImg = after.querySelector("img");
  if (!beforeImg || !afterImg) return;

  const caption = (figure) => {
    const el = figure.querySelector("figcaption");
    return el ? el.textContent.trim() : "";
  };
  const labels = [caption(before), caption(after)];

  const stage = document.createElement("div");
  stage.className = "pc-compare-stage";

  const base = document.createElement("div");
  base.className = "pc-compare-base";
  base.appendChild(afterImg.cloneNode(true));

  const overlay = document.createElement("div");
  overlay.className = "pc-compare-overlay";
  overlay.appendChild(beforeImg.cloneNode(true));

  const divider = document.createElement("div");
  divider.className = "pc-compare-divider";
  divider.tabIndex = 0;
  divider.setAttribute("role", "slider");
  divider.setAttribute("aria-label", "Reveal more of the before or after image");
  divider.setAttribute("aria-valuemin", "0");
  divider.setAttribute("aria-valuemax", "100");

  const legend = document.createElement("p");
  legend.className = "pc-compare-legend";
  legend.innerHTML =
    `<span>&#9664; ${labels[0] || "Before"}</span><span>${labels[1] || "After"} &#9654;</span>`;

  let position = 50;

  function apply() {
    // Clip rather than resize, so both images stay in exact register.
    overlay.style.clipPath = `inset(0 ${100 - position}% 0 0)`;
    divider.style.left = `${position}%`;
    divider.setAttribute("aria-valuenow", String(Math.round(position)));
    divider.setAttribute(
      "aria-valuetext",
      `${Math.round(position)}% ${labels[0] || "before"}`,
    );
  }

  function setFromClientX(clientX) {
    const rect = stage.getBoundingClientRect();
    if (!rect.width) return;
    position = clamp(((clientX - rect.left) / rect.width) * 100);
    apply();
  }

  let dragging = false;
  const onMove = (event) => {
    if (!dragging) return;
    event.preventDefault();
    setFromClientX(event.touches ? event.touches[0].clientX : event.clientX);
  };
  const stop = () => {
    dragging = false;
  };

  const start = (event) => {
    dragging = true;
    setFromClientX(event.touches ? event.touches[0].clientX : event.clientX);
  };

  stage.addEventListener("mousedown", start);
  stage.addEventListener("touchstart", start, { passive: true });
  window.addEventListener("mousemove", onMove);
  window.addEventListener("touchmove", onMove, { passive: false });
  window.addEventListener("mouseup", stop);
  window.addEventListener("touchend", stop);

  divider.addEventListener("keydown", (event) => {
    const moves = {
      ArrowLeft: -STEP,
      ArrowRight: STEP,
      PageDown: -BIG_STEP,
      PageUp: BIG_STEP,
    };
    if (event.key === "Home") {
      position = 0;
    } else if (event.key === "End") {
      position = 100;
    } else if (event.key in moves) {
      position = clamp(position + moves[event.key]);
    } else {
      return;
    }
    event.preventDefault();
    apply();
  });

  stage.append(base, overlay, divider);
  root.replaceChildren(stage, legend);
  apply();
}

export function init(doc = document) {
  for (const root of doc.querySelectorAll("[data-pc-compare]")) {
    if (root.dataset.pcReady) continue;
    root.dataset.pcReady = "true";
    build(root);
  }
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => init());
  } else {
    init();
  }
}
