import { SurfaceModelViewer } from "../shared/model3d-viewer.js";
import { validateModel3d } from "./model3d-core.mjs";

class VisualizerSurfaceModelViewer extends SurfaceModelViewer {
  constructor(container, model3d, options = {}) {
    super(container, model3d, options);
    this.helpersVisible = options.helpersVisible !== false;
    this.applyHelpersVisibility();
  }

  refreshHelpers() {
    super.refreshHelpers();
    this.applyHelpersVisibility();
  }

  applyHelpersVisibility() {
    if (this.boundsHelper) this.boundsHelper.visible = this.helpersVisible;
    if (this.axesHelper) this.axesHelper.visible = this.helpersVisible;
  }

  setHelpersVisible(visible) {
    this.helpersVisible = Boolean(visible);
    this.applyHelpersVisibility();
  }
}

/**
 * Visualizer-specific construction adapter around the shared renderer.
 */
export function createModel3dViewer(container, rawModel3d, options = {}) {
  return new VisualizerSurfaceModelViewer(
    container,
    validateModel3d(rawModel3d),
    options,
  );
}

export { SurfaceModelViewer };
