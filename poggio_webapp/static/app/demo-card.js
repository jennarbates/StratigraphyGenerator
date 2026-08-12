/* The demo card in the sidebar: wiring only.
 *
 * Every sentence it renders comes from demo-mode.mjs, which is where the state
 * logic is and where it is tested. This file fetches, builds nodes, and
 * navigates.
 */

import { demoCardModel } from "./demo-mode.mjs";

const host = document.querySelector("[data-demo-card]");

async function readDemo() {
  const response = await fetch("/api/demo", {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error("could not read the demonstration state");
  return response.json();
}

async function post(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? "DELETE" : "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: body === undefined ? null : JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || payload.description || "that did not work");
  }
  return payload;
}

function button(action, onSeed) {
  const wrap = document.createElement("div");
  const control = document.createElement("button");
  const detail = document.createElement("span");

  control.type = "button";
  control.className = "demo-action";
  control.textContent = action.label;
  control.disabled = action.disabled;
  // The reason lives on the button rather than beside it: an operator who
  // cannot press something wants to know why at the point they try.
  if (action.reason) control.title = action.reason;
  control.addEventListener("click", () => void onSeed(action.scenario, control));

  detail.className = "demo-detail";
  detail.textContent = action.reason || action.detail;

  wrap.className = "demo-action-row";
  wrap.append(control, detail);
  return wrap;
}

function render(model, handlers) {
  const heading = document.createElement("strong");
  const lede = document.createElement("span");
  const status = document.createElement("span");

  heading.textContent = model.heading;
  lede.textContent = model.lede;
  status.className = "demo-status";
  status.setAttribute("aria-live", "polite");

  const nodes = [heading, lede];
  for (const action of model.actions) {
    nodes.push(button(action, handlers.seed));
  }
  if (model.canRemove) {
    const open = document.createElement("a");
    open.className = "demo-open";
    open.href = "/trenches";
    open.textContent = "Open the trenches page";
    nodes.push(open);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "demo-remove";
    remove.textContent = "Remove the demonstration";
    remove.addEventListener("click", () => void handlers.remove(remove));
    nodes.push(remove);
  }
  nodes.push(status);

  host.replaceChildren(...nodes);
  return status;
}

async function refresh(message = "") {
  let payload;
  try {
    payload = await readDemo();
  } catch (_error) {
    host.hidden = true;
    return;
  }
  host.hidden = false;
  const status = render(demoCardModel(payload), handlers);
  status.textContent = message;
}

const handlers = {
  async seed(scenario, control) {
    control.disabled = true;
    control.textContent = "Loading…";
    try {
      const summary = await post("/api/demo/seed", { scenario });
      await refresh(
        `Seeded trench ${summary.trench}. Open the trenches page to build it.`,
      );
    } catch (error) {
      await refresh(error.message);
    }
  },
  async remove(control) {
    control.disabled = true;
    control.textContent = "Removing…";
    try {
      await post("/api/demo");
      await refresh("Demonstration removed.");
    } catch (error) {
      await refresh(error.message);
    }
  },
};

if (host) void refresh();
