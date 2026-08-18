/**
 * Pipeline stage explorer.
 *
 * Progressive enhancement: the page contains an ordinary list of stages, each
 * with its module, input, output, and route. With JavaScript off that list is
 * the whole story, readable top to bottom, and it is what the README shows.
 * With JavaScript on it becomes a tab list beside a detail panel, which turns
 * eight prose sections into one navigable object.
 *
 * Keyboard: arrow keys move between stages, Home and End jump to the ends,
 * following the ARIA authoring practice for tabs with automatic activation.
 */

function build(root) {
  const items = [...root.querySelectorAll("[data-stage]")];
  if (items.length < 2) return;

  const tablist = document.createElement("div");
  tablist.className = "pc-explorer-tabs";
  tablist.setAttribute("role", "tablist");
  tablist.setAttribute("aria-label", "Pipeline stages");
  tablist.setAttribute("aria-orientation", "vertical");

  const panels = document.createElement("div");
  panels.className = "pc-explorer-panels";

  const tabs = [];

  items.forEach((item, index) => {
    const name = item.dataset.stage;
    const heading = item.querySelector("h4, h3, strong");
    const title = heading ? heading.textContent.trim() : name;

    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "pc-explorer-tab";
    tab.textContent = title;
    tab.id = `pc-tab-${name}`;
    tab.setAttribute("role", "tab");
    tab.setAttribute("aria-controls", `pc-panel-${name}`);
    tabs.push(tab);
    tablist.appendChild(tab);

    const panel = document.createElement("div");
    panel.className = "pc-explorer-panel";
    panel.id = `pc-panel-${name}`;
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", tab.id);
    panel.tabIndex = 0;
    // Keep the authored markup, minus the heading the tab now carries.
    const body = item.cloneNode(true);
    const bodyHeading = body.querySelector("h4, h3");
    if (bodyHeading) bodyHeading.remove();
    panel.appendChild(body);
    panels.appendChild(panel);

    tab.addEventListener("click", () => select(index));
  });

  function select(index, focus = false) {
    tabs.forEach((tab, i) => {
      const active = i === index;
      tab.setAttribute("aria-selected", active ? "true" : "false");
      tab.tabIndex = active ? 0 : -1;
      panels.children[i].hidden = !active;
    });
    if (focus) tabs[index].focus();
  }

  tablist.addEventListener("keydown", (event) => {
    const current = tabs.findIndex((tab) => tab.tabIndex === 0);
    const moves = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 };
    let next;
    if (event.key === "Home") {
      next = 0;
    } else if (event.key === "End") {
      next = tabs.length - 1;
    } else if (event.key in moves) {
      next = (current + moves[event.key] + tabs.length) % tabs.length;
    } else {
      return;
    }
    event.preventDefault();
    select(next, true);
  });

  const shell = document.createElement("div");
  shell.className = "pc-explorer-shell";
  shell.append(tablist, panels);
  root.replaceChildren(shell);
  select(0);
}

export function init(doc = document) {
  for (const root of doc.querySelectorAll("[data-pc-explorer]")) {
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
