const VIEW_MODES = new Set(["2d", "3d"]);
const MODEL_RENDERER_TYPES = new Set(["surfaces", "volume"]);

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

/**
 * Resolve the renderer and matching controls within the 3D visualizer.
 *
 * Surfaces remain the compatibility default when both renderers are
 * available. A volume-only payload can still select the voxel renderer.
 */
export function modelRendererTypeModel({
  hasSurfaces,
  hasVolume,
  requestedType = null,
}) {
  if (typeof hasSurfaces !== "boolean" || typeof hasVolume !== "boolean") {
    throw new TypeError("hasSurfaces and hasVolume must be booleans");
  }
  if (
    requestedType !== null
    && !MODEL_RENDERER_TYPES.has(requestedType)
  ) {
    throw new TypeError(
      'requestedType must be null, "surfaces", or "volume"',
    );
  }
  if (!hasSurfaces && !hasVolume) {
    throw new TypeError("at least one 3D renderer must be available");
  }

  let type = requestedType;
  if (type === "surfaces" && !hasSurfaces) type = null;
  if (type === "volume" && !hasVolume) type = null;
  if (type === null) type = hasSurfaces ? "surfaces" : "volume";

  return {
    type,
    canSelectSurfaces: hasSurfaces,
    canSelectVolume: hasVolume,
    showSurfaceControls: type === "surfaces",
    showVolumeControls: type === "volume",
  };
}
