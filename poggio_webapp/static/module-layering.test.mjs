// The browser/headless split, enforced rather than assumed.
//
// `three` is vendored under static/vendor/three and resolved in the browser by
// the import map in templates/index.html. Node has no import map, so a bare
// `import ... from "three"` is unresolvable outside a browser -- and the files
// that need it also need WebGL, a canvas, and a document, so making the
// specifier resolve would not make them runnable.
//
// The split that makes this a non-problem already exists: pure logic lives in
// `*.mjs` modules with no browser dependency, and `*.js` files are the glue
// that wires those modules to three.js and the DOM. Only the pure side is
// tested. Nothing checked that, so the day someone imports three into a core
// module the JS suite would start failing with a module-resolution error that
// says nothing about the actual mistake.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { readdir } from "node:fs/promises";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const STATIC_DIR = dirname(fileURLToPath(import.meta.url));

// The only files allowed to reach three.js. Both drive a WebGL canvas, so they
// are browser-only by nature and not merely by convention.
const BROWSER_ONLY = new Set([
  "shared/model3d-viewer.js",
  "visualizer/volume3d.js",
]);

const THREE_IMPORT = /^\s*import\s[^;]*?from\s+["']three(?:\/[^"']*)?["']/m;

async function jsFiles(dir) {
  const found = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (entry.name === "vendor" || entry.name === "node_modules") continue;
    const full = resolve(dir, entry.name);
    if (entry.isDirectory()) found.push(...(await jsFiles(full)));
    else if (/\.(mjs|js)$/.test(entry.name)) found.push(full);
  }
  return found;
}

test("only the browser-only glue files import three", async () => {
  const offenders = [];
  for (const file of await jsFiles(STATIC_DIR)) {
    const name = relative(STATIC_DIR, file).replaceAll("\\", "/");
    if (BROWSER_ONLY.has(name)) continue;
    if (THREE_IMPORT.test(readFileSync(file, "utf8"))) offenders.push(name);
  }
  assert.deepEqual(
    offenders,
    [],
    `these files import three but are not listed as browser-only, so the ` +
      `headless test suite can no longer import them: ${offenders.join(", ")}. ` +
      `Either move the logic into a '*.mjs' module with no three dependency, ` +
      `or add the file to BROWSER_ONLY if it genuinely drives a canvas.`,
  );
});

test("every browser-only file still exists and still imports three", async () => {
  // Guards the other direction: a stale allowlist entry would silently permit
  // a three import in a file that had since become testable.
  for (const name of BROWSER_ONLY) {
    const source = readFileSync(resolve(STATIC_DIR, name), "utf8");
    assert.ok(
      THREE_IMPORT.test(source),
      `${name} is listed as browser-only but no longer imports three -- ` +
        `remove it from BROWSER_ONLY so the layering check covers it`,
    );
  }
});

// Relative import specifiers only -- a bare specifier is either three (test 1's
// business) or a node: builtin, and neither is a file in this tree.
const RELATIVE_IMPORTS = /^\s*(?:import|export)\s[^;]*?from\s+["'](\.[^"']*)["']/gm;

function importsOf(file) {
  const source = readFileSync(file, "utf8");
  return [...source.matchAll(RELATIVE_IMPORTS)].map(([, spec]) =>
    resolve(dirname(file), spec),
  );
}

test("no test file reaches a browser-only module, even transitively", async () => {
  // The failure this prevents is the confusing one: `node --test` on a path
  // that reaches a browser-only file dies with ERR_MODULE_NOT_FOUND for
  // 'three', which reads as a broken install rather than a layering mistake.
  //
  // Transitive because the mistake that actually happens is one hop removed:
  // a core module grows an import of the glue file, and the test that imported
  // the core module starts failing for reasons nowhere near itself.
  const browserOnly = new Set(
    [...BROWSER_ONLY].map((name) => resolve(STATIC_DIR, name)),
  );
  const offenders = [];

  for (const entry of await jsFiles(STATIC_DIR)) {
    if (!entry.endsWith(".test.mjs")) continue;
    const seen = new Set([entry]);
    const queue = [[entry, [relative(STATIC_DIR, entry)]]];
    while (queue.length) {
      const [file, path] = queue.shift();
      for (const target of importsOf(file)) {
        if (seen.has(target)) continue;
        seen.add(target);
        const trail = [...path, relative(STATIC_DIR, target)];
        if (browserOnly.has(target)) {
          offenders.push(trail.join(" -> "));
          continue;
        }
        queue.push([target, trail]);
      }
    }
  }

  assert.deepEqual(
    offenders,
    [],
    `these import chains start at a test and end at a browser-only module, ` +
      `so the headless suite cannot resolve them: ${offenders.join("; ")}`,
  );
});
