// Saved-job results-page adapter for the shared surface renderer.

import { munsellToHex } from "./shared/munsell-color.js";
import { SurfaceModelViewer } from "./shared/model3d-viewer.js";

function showStatus(statusEl, message) {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.style.display = message ? "block" : "none";
}

function parseMeshList(meshDataEl) {
  if (!meshDataEl) return [];
  const value = JSON.parse(meshDataEl.textContent || "[]");
  if (!Array.isArray(value)) {
    throw new TypeError("Saved model mesh data must be an array.");
  }
  return value;
}

function addLegendRows(legendEl, summary, viewer) {
  if (!legendEl) return;
  legendEl.replaceChildren();
  summary.loaded.forEach((surface) => {
    const row = document.createElement("label");
    row.className = "viewer3d-legend-row";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.addEventListener("change", () => {
      viewer.setSurfaceVisible(surface.name, checkbox.checked);
    });

    const swatch = document.createElement("span");
    swatch.className = "viewer3d-swatch";
    swatch.style.background = surface.color;

    const text = document.createElement("span");
    text.textContent = surface.name;
    row.append(checkbox, swatch, text);
    legendEl.appendChild(row);
  });
}

export async function initResultsSurfaceViewer(root) {
  const meshDataEl = document.getElementById("viewer3d-meshes");
  const canvas = document.getElementById("viewer3d-canvas");
  const wrap = root.querySelector(".viewer3d-canvas-wrap");
  const statusEl = document.getElementById("viewer3d-status");
  const legendEl = document.getElementById("viewer3d-legend");
  const veSlider = document.getElementById("viewer3d-ve");
  const veLabel = document.getElementById("viewer3d-ve-val");
  const resetBtn = document.getElementById("viewer3d-reset");

  let meshList;
  try {
    meshList = parseMeshList(meshDataEl);
  } catch (error) {
    showStatus(statusEl, "Couldn't read the 3D mesh list.");
    console.error("Invalid saved-job 3D mesh data.", error);
    return null;
  }
  if (!meshList.length) {
    showStatus(statusEl, "No mesh data was produced for this model.");
    return null;
  }
  if (!wrap || !canvas) {
    showStatus(statusEl, "The 3D viewer container is unavailable.");
    return null;
  }

  const style = getComputedStyle(document.documentElement);
  const palette = [
    "--strata-1",
    "--strata-2",
    "--strata-3",
    "--strata-4",
    "--strata-5",
  ].map((name) => (
    style.getPropertyValue(name) || "#8a8c53"
  ).trim());
  const verticalScale = Number.parseFloat(veSlider?.value ?? "3");

  const viewer = new SurfaceModelViewer(wrap, meshList, {
    canvas,
    background: style.getPropertyValue("--panel")?.trim() || "#ffffff",
    verticalScale,
    colorFor: (surface, index) => (
      munsellToHex(surface.name, palette[index % palette.length])
    ),
    onProgress: (progress) => {
      if (progress.phase === "loading") {
        const suffix = progress.settled
          ? ` (${progress.settled} of ${progress.total})`
          : "";
        showStatus(statusEl, `Loading 3D model\u2026${suffix}`);
      } else if (progress.phase === "error") {
        showStatus(statusEl, "Couldn't load the 3D mesh files.");
      }
    },
  });

  const onScaleInput = () => {
    const value = Number.parseFloat(veSlider.value);
    viewer.setVerticalScale(value);
    if (veLabel) veLabel.textContent = `${value}\u00d7`;
  };
  const onReset = () => viewer.resetCamera();
  veSlider?.addEventListener("input", onScaleInput);
  resetBtn?.addEventListener("click", onReset);

  try {
    const summary = await viewer.load();
    addLegendRows(legendEl, summary, viewer);
    showStatus(
      statusEl,
      summary.failed.length
        ? `Loaded ${summary.loaded.length} of ${summary.total} surfaces `
          + `(${summary.failed.length} failed).`
        : "",
    );
  } catch (error) {
    showStatus(statusEl, "Couldn't load the 3D mesh files.");
    console.error("Saved-job 3D viewer failed to load.", error);
  }

  return {
    viewer,
    dispose() {
      veSlider?.removeEventListener("input", onScaleInput);
      resetBtn?.removeEventListener("click", onReset);
      viewer.dispose();
    },
  };
}

const root = document.getElementById("viewer3d");
if (root) {
  initResultsSurfaceViewer(root).catch((error) => {
    console.error("Saved-job 3D viewer initialization failed.", error);
  });
}
