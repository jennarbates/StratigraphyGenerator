import { PREREQS, STEPS, STRATA, state } from "./state.js";
import { $content, $steps } from "./ui.js";

let renderApp = null;
const PRIMARY_FLOW = [
  "scan",
  "preprocess",
  "draw",
  "normalize",
  "validate",
  "convert",
  "gempy",
  "visualize",
];

export function configureNavigation(renderer) {
  renderApp = renderer;
}

export function stepIndex(id) {
  return STEPS.findIndex((s) => s.id === id);
}

export function stepTitle(id) {
  const s = STEPS.find((x) => x.id === id);
  return s ? s.title : id;
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

function stepCompleteForDisplay(id) {
  if (id === "draw") {
    return !!(state.completed.draw || (state.completed.extract && !state.completed.draw));
  }
  if (id === "extract") {
    return !!(state.completed.extract && !state.completed.draw);
  }
  return !!state.completed[id];
}

export function renderSidebar() {
  $steps.innerHTML = "";
  let optionalLabelAdded = false;
  STEPS.forEach((s, i) => {
    if (s.optional && !optionalLabelAdded) {
      const label = document.createElement("div");
      label.className = "steps-section-label";
      label.textContent = "Optional alternative";
      $steps.appendChild(label);
      optionalLabelAdded = true;
    } else if (!s.optional && optionalLabelAdded) {
      const label = document.createElement("div");
      label.className = "steps-section-label";
      label.textContent = "Continue here";
      $steps.appendChild(label);
      optionalLabelAdded = false;
    }

    const el = document.createElement("button");
    const enabled = stepEnabled(s.id);
    const complete = stepCompleteForDisplay(s.id);
    el.className = "step" + (s.id === state.current ? " active" : "") + (!enabled ? " disabled" : "");
    el.type = "button";
    el.disabled = !enabled;
    el.setAttribute("aria-current", s.id === state.current ? "step" : "false");
    el.innerHTML = `
      <div class="step-num" style="background:${STRATA[i % STRATA.length]}">${s.num}</div>
      <div class="step-label">
        <div class="step-title">${s.title}</div>
        <div class="step-sub">${enabled ? s.sub : "Finish the earlier steps first"}</div>
      </div>
      ${complete
          ? `<div class="step-check${stepHasWarnings(s.id) ? " warn" : ""}">${stepHasWarnings(s.id) ? "Check" : "Done"}</div>`
          : ""}
    `;
    if (enabled) {
      el.addEventListener("click", () => goToStep(s.id));
    }
    $steps.appendChild(el);
  });

  const completed = PRIMARY_FLOW.filter(stepCompleteForDisplay).length;
  const progressText = document.getElementById("progressText");
  const progressBar = document.getElementById("progressBar");
  if (progressText) {
    progressText.textContent = completed
      ? `${completed} of ${PRIMARY_FLOW.length} steps done`
      : "Not started";
  }
  if (progressBar) {
    progressBar.style.width = `${(completed / PRIMARY_FLOW.length) * 100}%`;
  }
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

  const idx = PRIMARY_FLOW.indexOf(state.current);
  const isOptional = state.current === "extract";
  if (idx < 0 && !isOptional) return;

  const prevId = isOptional
    ? "draw"
    : (idx > 0 ? PRIMARY_FLOW[idx - 1] : null);
  const nextId = isOptional
    ? "normalize"
    : (idx < PRIMARY_FLOW.length - 1 ? PRIMARY_FLOW[idx + 1] : null);
  const prev = prevId ? STEPS.find((step) => step.id === prevId) : null;
  const next = nextId ? STEPS.find((step) => step.id === nextId) : null;

  const nav = document.createElement("div");
  nav.className = "step-nav";
  nav.id = "stepNav";

  if (prev) {
    const back = document.createElement("button");
    back.className = "secondary";
    back.innerHTML = `&larr; Back`;
    back.setAttribute("aria-label", `Back to ${stepTitle(prev.id)}`);
    back.addEventListener("click", () => goToStep(prev.id));
    nav.appendChild(back);
  }

  const spacer = document.createElement("div");
  spacer.className = "step-nav-spacer";
  nav.appendChild(spacer);

  if (!next) {
    const done = document.createElement("span");
    done.className = "step-nav-hint";
    done.textContent = "You have reached the final step.";
    nav.appendChild(done);
    $content.appendChild(nav);
    return;
  }

  const missing = missingPrereqs(next.id);
  if (missing.length) {
    const hint = document.createElement("span");
    hint.className = "step-nav-hint";
    hint.textContent = `Finish ${missing.map((id) => `“${stepTitle(id)}”`).join(" and ")} to continue.`;
    nav.appendChild(hint);
  }

  const fwd = document.createElement("button");
  fwd.innerHTML = missing.length
    ? "Finish this step to continue"
    : `Continue to ${stepTitle(next.id)} &rarr;`;
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
