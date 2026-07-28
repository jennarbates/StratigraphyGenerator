const VIEW_MODES = new Set(["2d", "3d"]);

/**
 * Resolve the available visualizer modes without depending on the DOM.
 *
 * A model-only payload cannot display the 2D drawing, while a visualizer
 * without a model retains the existing manual 2D loading workflow.
 */
export function viewModeModel({
  hasModel3d,
  hasExtraction,
  openedFromJob = false,
  requestedMode = null,
}) {
  if (
    typeof hasModel3d !== "boolean"
    || typeof hasExtraction !== "boolean"
    || typeof openedFromJob !== "boolean"
  ) {
    throw new TypeError(
      "hasModel3d, hasExtraction, and openedFromJob must be booleans",
    );
  }
  if (requestedMode !== null && !VIEW_MODES.has(requestedMode)) {
    throw new TypeError('requestedMode must be null, "2d", or "3d"');
  }

  const canSelect3d = hasModel3d;
  const canSelect2d = hasExtraction || !hasModel3d;
  let mode;

  if (!hasModel3d) {
    mode = "2d";
  } else if (!hasExtraction) {
    mode = "3d";
  } else if (requestedMode !== null) {
    mode = requestedMode;
  } else {
    mode = openedFromJob ? "3d" : "2d";
  }

  return {
    mode,
    canSelect2d,
    canSelect3d,
    show2dControls: mode === "2d",
    show3dControls: mode === "3d",
  };
}
