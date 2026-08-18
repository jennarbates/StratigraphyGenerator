/* What the demo card should say, given what the server reports.
 *
 * Pure: no DOM, no fetch. The card has more states than it looks like -- two
 * scenarios that can each be seeded or not, either of which can be unavailable
 * because its record set is missing or is real -- and every one of them is a
 * sentence somebody reads. Working them out here means they can be asserted
 * without a browser.
 *
 * See static/module-layering.test.mjs for why this is .mjs and its wiring is
 * .js.
 */

const COPY = Object.freeze({
  stops: {
    action: "See it refuse",
    detail: "A trench with one corner elevation missing.",
  },
  complete: {
    action: "See it build",
    detail: "The same trench with that number supplied.",
  },
});

const FALLBACK = Object.freeze({
  action: "Load this demonstration",
  detail: "",
});

/* A scenario the server offers but this build has no wording for still gets a
 * button. New scenarios should appear in the interface the moment they exist,
 * rather than being invisible until someone remembers to add a string. */
export function scenarioCopy(name) {
  return COPY[name] || FALLBACK;
}

export function unavailableReason(scenario) {
  if (scenario.available) return null;
  if (!scenario.dataset) return "No record set is configured for this.";
  return (
    `Needs the ${scenario.dataset} record set, which is either missing or `
    + "holds real excavation records. The demonstration draws wall sections, "
    + "and those are never drawn under a real trench's label."
  );
}

/* The whole card, as data. `heading` and `lede` change once anything is
 * seeded, because at that point the useful action is opening the trenches
 * rather than loading more. */
export function demoCardModel(payload) {
  const scenarios = Array.isArray(payload?.scenarios) ? payload.scenarios : [];
  const seeded = scenarios.filter(scenario => scenario.seeded);
  const anySeeded = seeded.length > 0;

  return {
    heading: anySeeded ? "Demonstration loaded" : "Never used this before?",
    lede: anySeeded
      ? seededLede(seeded)
      : "Load a demonstration trench. No drawing needed.",
    actions: scenarios.map(scenario => ({
      scenario: scenario.name,
      label: scenarioCopy(scenario.name).action,
      detail: scenarioCopy(scenario.name).detail,
      disabled: !scenario.available,
      reason: unavailableReason(scenario),
      seededTrench: scenario.seeded?.trench || null,
    })),
    // Only offered once there is something to remove, so the control is never
    // a button that does nothing.
    canRemove: anySeeded,
    trenches: seeded.map(scenario => scenario.seeded.trench).filter(Boolean),
  };
}

function seededLede(seeded) {
  const trenches = seeded
    .map(scenario => scenario.seeded?.trench)
    .filter(Boolean)
    .sort();
  if (trenches.length === 0) return "Open the trenches to build it.";
  const list = trenches.length === 1
    ? trenches[0]
    : `${trenches.slice(0, -1).join(", ")} and ${trenches[trenches.length - 1]}`;
  return `Open ${list} on the trenches page and press Build.`;
}
