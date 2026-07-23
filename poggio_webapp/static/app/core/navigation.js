import { PREREQS, STEPS, STRATA, state } from "./state.js";
import { $content, $steps } from "./ui.js";

let renderApp = null;

export function configureNavigation(renderer) {
  renderApp = renderer;
}

export function stepIndex(id) {
  return STEPS.findIndex((s) => s.id === id);
}

export function stepTitle(id) {
  const s = STEPS.find((x) => x.id === id);
  return s ? `${s.num} · ${s.title}` : id;
}

export function missingPrereqs(id) {
  return (PREREQS[id] || []).filter((p) => !state.completed[p]);
}

export function stepEnabled(id) {
  if (stepIndex(id) === 0) return true;
  return missingPrereqs(id).length === 0;
}

export function stepHasWarnings(id) {
  if (id !== "validate") return false;
  const report = state.validate && state.validate.report;
  return !!(report && report.warnings && report.warnings.length);
}

export function renderSidebar() {
  $steps.innerHTML = "";
  STEPS.forEach((s, i) => {
    const el = document.createElement("div");
    const enabled = stepEnabled(s.id);
    el.className = "step" + (s.id === state.current ? " active" : "") + (!enabled ? " disabled" : "");
    el.innerHTML = `
      <div class="step-num" style="background:${STRATA[i % STRATA.length]}">${s.num}</div>
      <div class="step-label">
        <div class="step-title">${s.title}</div>
        <div class="step-sub">${s.sub}</div>
      </div>
      ${state.completed[s.id]
          ? `<div class="step-check${stepHasWarnings(s.id) ? " warn" : ""}">&#10003;</div>`
          : ""}
    `;
    if (enabled) {
      el.addEventListener("click", () => goToStep(s.id));
    }
    $steps.appendChild(el);
  });
}

// ---------------------------------------------------------------------------
// step navigation footer
// ---------------------------------------------------------------------------

export function goToStep(id) {
  state.current = id;
  if (renderApp) renderApp();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* Appended to the bottom of every panel by render(). Removed and rebuilt each
   time so the Next button's enabled state tracks the current step's progress
   -- stages call refreshChrome() when they complete. */
export function renderStepNav() {
  const existing = document.getElementById("stepNav");
  if (existing) existing.remove();

  const idx = stepIndex(state.current);
  if (idx < 0) return;

  const prev = idx > 0 ? STEPS[idx - 1] : null;
  const next = idx < STEPS.length - 1 ? STEPS[idx + 1] : null;

  const nav = document.createElement("div");
  nav.className = "step-nav";
  nav.id = "stepNav";

  if (prev) {
    const back = document.createElement("button");
    back.className = "secondary";
    back.innerHTML = `&larr; ${stepTitle(prev.id)}`;
    back.addEventListener("click", () => goToStep(prev.id));
    nav.appendChild(back);
  }

  const spacer = document.createElement("div");
  spacer.className = "step-nav-spacer";
  nav.appendChild(spacer);

  if (!next) {
    const done = document.createElement("span");
    done.className = "step-nav-hint";
    done.textContent = "last step — nothing further to run";
    nav.appendChild(done);
    $content.appendChild(nav);
    return;
  }

  const missing = missingPrereqs(next.id);
  if (missing.length) {
    const hint = document.createElement("span");
    hint.className = "step-nav-hint";
    hint.textContent = `run ${missing.map(stepTitle).join(" and ")} first`;
    nav.appendChild(hint);
  }

  const fwd = document.createElement("button");
  fwd.innerHTML = `Next: ${stepTitle(next.id)} &rarr;`;
  fwd.disabled = missing.length > 0;
  if (!fwd.disabled) fwd.addEventListener("click", () => goToStep(next.id));
  nav.appendChild(fwd);

  $content.appendChild(nav);
}

/* Sidebar + footer both reflect completion state, so they refresh together. */
export function refreshChrome() {
  renderSidebar();
  renderStepNav();
}
