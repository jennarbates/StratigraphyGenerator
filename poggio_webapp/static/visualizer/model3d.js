import { SurfaceModelViewer } from "../model3d-viewer.js";
import { validateModel3d } from "./model3d-core.mjs";

/**
 * Visualizer-specific construction adapter.
 *
 * Chunk A6 intentionally adds no visualizer navigation or controls; later
 * integration can use this function without duplicating renderer behavior.
 */
export function createModel3dViewer(container, rawModel3d, options = {}) {
  return new SurfaceModelViewer(
    container,
    validateModel3d(rawModel3d),
    options,
  );
}

export { SurfaceModelViewer };
