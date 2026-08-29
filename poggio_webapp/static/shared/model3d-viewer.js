import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";

import {
  clampOpacity,
  deterministicSurfaceColor,
} from "../visualizer/model3d-core.mjs";

const DEFAULT_OPACITY = 0.72;
const CAMERA_VIEWS = new Set(["isometric", "top", "front", "side"]);

function normalizedSurfaces(model3d) {
  const values = Array.isArray(model3d) ? model3d : model3d?.surfaces;
  if (!Array.isArray(values)) {
    throw new TypeError("model3d must contain a surface array");
  }

  return values.map((surface, index) => {
    if (
      !surface
      || typeof surface.name !== "string"
      || surface.name.trim() === ""
      || typeof surface.url !== "string"
      || surface.url.trim() === ""
    ) {
      throw new TypeError(
        `surface ${index + 1} must have a non-empty name and URL`,
      );
    }
    return {
      // `name` identifies the surface and is what every lookup keys on;
      // `label` is what a reader sees. A manifest written before labels
      // existed has none, so the name stands in.
      name: surface.name,
      label: typeof surface.label === "string" && surface.label.trim() !== ""
        ? surface.label
        : surface.name,
      url: surface.url,
      index,
      color: null,
      object3d: null,
      materials: [],
      visible: true,
      error: null,
    };
  });
}

/**
 * Wall traces are optional and never fatal: a model whose traces are missing
 * or malformed still renders its surfaces, it just has no overlay showing
 * where the drawings actually recorded data.
 */
function normalizedWallTraces(model3d) {
  if (Array.isArray(model3d) || !Array.isArray(model3d?.wall_traces)) return [];

  return model3d.wall_traces.filter(
    (trace) => trace
      && typeof trace.face === "string"
      && typeof trace.surface === "string"
      && Array.isArray(trace.points)
      && trace.points.length >= 2
      && trace.points.every(
        (point) => Array.isArray(point)
          && point.length === 3
          && point.every(
            (value) => typeof value === "number" && Number.isFinite(value),
          ),
      ),
  );
}

function extentBox(model3d) {
  if (Array.isArray(model3d) || !Array.isArray(model3d?.extent)) return null;
  const extent = model3d.extent;
  if (
    extent.length !== 6
    || !extent.every((value) => typeof value === "number" && Number.isFinite(value))
  ) {
    return null;
  }
  return new THREE.Box3(
    new THREE.Vector3(extent[0], extent[2], extent[4]),
    new THREE.Vector3(extent[1], extent[3], extent[5]),
  );
}

function disposeMaterial(material) {
  if (Array.isArray(material)) {
    material.forEach(disposeMaterial);
  } else {
    material?.dispose?.();
  }
}

function disposeObject(object3d) {
  object3d?.traverse((child) => {
    child.geometry?.dispose?.();
    disposeMaterial(child.material);
  });
}

function errorMessage(error) {
  if (error instanceof Error && error.message) return error.message;
  return String(error);
}

/**
 * Shared Three.js renderer for GemPy surface OBJ files.
 *
 * Page-specific DOM controls belong in adapters. This class owns only the
 * rendering lifecycle and reports progress through `options.onProgress`.
 */
export class SurfaceModelViewer {
  constructor(container, model3d, options = {}) {
    if (!container || typeof container.appendChild !== "function") {
      throw new TypeError("container must be a DOM element");
    }

    this.container = container;
    this.options = options;
    this.surfaceEntries = normalizedSurfaces(model3d);
    this.wallTraceEntries = normalizedWallTraces(model3d);
    this.wallTracesVisible = options.wallTracesVisible !== false;
    this.wallTraceGroup = null;
    this.modelExtentBox = extentBox(model3d);
    this.baseBox = this.modelExtentBox?.clone() ?? null;
    this.modelCenter = this.baseBox?.getCenter(new THREE.Vector3()) ?? null;
    this.opacity = clampOpacity(options.opacity ?? DEFAULT_OPACITY);
    this.wireframe = Boolean(options.wireframe);
    this.verticalScale = 1;
    this.currentCameraView = "isometric";
    this.disposed = false;
    this.loadPromise = null;
    this.animationFrame = null;
    this.resizeObserver = null;
    this.boundsHelper = null;
    this.axesHelper = null;
    this.initializationError = null;
    this.createdCanvas = !options.canvas;
    this.canvas = options.canvas
      ?? container.ownerDocument.createElement("canvas");

    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.modelGroup = null;
    this.loader = null;

    try {
      this.initializeRenderer();
      this.setVerticalScale(options.verticalScale ?? 1);
    } catch (error) {
      this.resizeObserver?.disconnect();
      this.controls?.dispose();
      this.renderer?.dispose();
      this.renderer?.forceContextLoss?.();
      this.initializationError = new Error(
        `The 3D viewer could not start: ${errorMessage(error)}`,
        { cause: error },
      );
      if (this.createdCanvas) this.canvas.remove();
      this.emitProgress({
        phase: "error",
        error: this.initializationError,
      });
    }
  }

  initializeRenderer() {
    const view = this.container.ownerDocument.defaultView;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(
      this.options.background ?? "#ffffff",
    );

    this.camera = new THREE.PerspectiveCamera(45, 1, 0.01, 5000);
    this.camera.up.set(0, 0, 1);

    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
    });
    this.renderer.setPixelRatio(Math.min(view?.devicePixelRatio || 1, 2));
    if (this.createdCanvas) this.container.appendChild(this.canvas);
    this.canvas.setAttribute("aria-label", "Interactive 3D geological model");

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.rotateSpeed = 0.8;

    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x596273, 1.15));
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.35);
    keyLight.position.set(1, 1.6, 2);
    this.scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.4);
    fillLight.position.set(-1, -0.5, 0.8);
    this.scene.add(fillLight);

    this.modelGroup = new THREE.Group();
    this.scene.add(this.modelGroup);
    // Inside the model group so the traces follow the vertical exaggeration
    // the surfaces get; a trace drawn at true scale over a stretched model
    // would point at the wrong layer.
    this.wallTraceGroup = new THREE.Group();
    this.wallTraceGroup.visible = this.wallTracesVisible;
    this.modelGroup.add(this.wallTraceGroup);
    this.loader = new OBJLoader();

    const ResizeObserverClass = view?.ResizeObserver;
    if (ResizeObserverClass) {
      this.resizeObserver = new ResizeObserverClass(() => this.resize());
      this.resizeObserver.observe(this.container);
    }
    this.resize();
  }

  emitProgress(detail) {
    if (typeof this.options.onProgress !== "function") return;
    this.options.onProgress({
      loaded: this.surfaceEntries.filter((surface) => surface.object3d).length,
      failed: this.surfaceEntries.filter((surface) => surface.error).length,
      total: this.surfaceEntries.length,
      ...detail,
    });
  }

  async load() {
    if (this.loadPromise) return this.loadPromise;
    this.loadPromise = this.loadSurfaces();
    return this.loadPromise;
  }

  async loadSurfaces() {
    if (this.initializationError) throw this.initializationError;
    if (this.disposed) throw new Error("The 3D viewer has been disposed.");
    if (!this.surfaceEntries.length) {
      const error = new Error("No surface meshes were provided.");
      this.emitProgress({ phase: "error", error });
      throw error;
    }

    this.emitProgress({ phase: "loading", settled: 0 });
    let settled = 0;
    const tasks = this.surfaceEntries.map(async (surface) => {
      try {
        const object3d = await this.loader.loadAsync(surface.url);
        if (this.disposed) {
          disposeObject(object3d);
          throw new Error("The 3D viewer was disposed while loading.");
        }
        try {
          this.prepareSurface(surface, object3d);
        } catch (error) {
          disposeObject(object3d);
          throw error;
        }
        return surface;
      } catch (error) {
        surface.error = error instanceof Error
          ? error
          : new Error(errorMessage(error));
        throw surface.error;
      } finally {
        settled += 1;
        this.emitProgress({ phase: "loading", settled });
      }
    });

    const results = await Promise.allSettled(tasks);
    results.forEach((result, index) => {
      if (result.status === "rejected") {
        this.surfaceEntries[index].error = result.reason instanceof Error
          ? result.reason
          : new Error(errorMessage(result.reason));
      }
    });

    if (this.disposed) throw new Error("The 3D viewer has been disposed.");

    const loaded = this.surfaceEntries.filter((surface) => surface.object3d);
    const failed = this.surfaceEntries.filter((surface) => surface.error);
    if (!loaded.length) {
      const error = new Error("Couldn't load any 3D surface mesh files.");
      this.emitProgress({
        phase: "error",
        error,
        failures: failed.map((surface) => ({
          name: surface.name,
          message: errorMessage(surface.error),
        })),
      });
      throw error;
    }

    this.buildWallTraces();

    if (!this.modelExtentBox) {
      this.baseBox = new THREE.Box3().setFromObject(this.modelGroup);
      if (this.baseBox.isEmpty()) {
        const error = new Error("The loaded 3D surfaces contain no geometry.");
        this.emitProgress({ phase: "error", error });
        throw error;
      }
      this.modelCenter = this.baseBox.getCenter(new THREE.Vector3());
    }

    this.applyVerticalTransform();
    this.refreshHelpers();
    this.resetCamera();
    this.resize();
    this.startAnimation();

    const summary = this.loadSummary();
    this.emitProgress({
      phase: "complete",
      settled: this.surfaceEntries.length,
      failures: summary.failed.map((surface) => ({
        name: surface.name,
        message: surface.message,
      })),
    });
    return summary;
  }

  prepareSurface(surface, object3d) {
    const color = typeof this.options.colorFor === "function"
      ? this.options.colorFor(
        { name: surface.name, url: surface.url },
        surface.index,
      )
      : deterministicSurfaceColor(surface.name);
    const materials = [];
    let meshCount = 0;

    object3d.traverse((child) => {
      if (!child.isMesh) return;
      meshCount += 1;
      if (!child.geometry.getAttribute("normal")) {
        child.geometry.computeVertexNormals();
      }
      disposeMaterial(child.material);
      const material = new THREE.MeshStandardMaterial({
        color,
        side: THREE.DoubleSide,
        flatShading: true,
        roughness: 0.85,
        metalness: 0.02,
        opacity: this.opacity,
        transparent: this.opacity < 1,
        depthWrite: this.opacity >= 1,
        wireframe: this.wireframe,
      });
      child.material = material;
      materials.push(material);
    });

    if (!meshCount) {
      throw new Error(`Surface "${surface.name}" contains no mesh geometry.`);
    }

    surface.color = color;
    surface.object3d = object3d;
    surface.materials = materials;
    object3d.visible = surface.visible;
    this.modelGroup.add(object3d);
  }

  surfaceColorFor(surfaceName) {
    const entry = this.surfaceEntries.find(
      (surface) => surface.name === surfaceName,
    );
    if (entry?.color) return entry.color;
    if (typeof this.options.colorFor === "function") {
      return this.options.colorFor(
        { name: surfaceName, url: entry?.url ?? null },
        entry?.index ?? 0,
      );
    }
    return deterministicSurfaceColor(surfaceName);
  }

  clearWallTraces() {
    if (!this.wallTraceGroup) return;
    const lines = [...this.wallTraceGroup.children];
    lines.forEach((line) => {
      this.wallTraceGroup.remove(line);
      disposeObject(line);
    });
  }

  /**
   * Draw one polyline per traced wall boundary, in its surface's color.
   */
  buildWallTraces() {
    if (!this.wallTraceGroup) return 0;
    this.clearWallTraces();

    this.wallTraceEntries.forEach((trace) => {
      const positions = new Float32Array(trace.points.length * 3);
      trace.points.forEach((point, index) => {
        positions.set(point, index * 3);
      });
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(positions, 3),
      );
      const line = new THREE.Line(
        geometry,
        new THREE.LineBasicMaterial({
          color: this.surfaceColorFor(trace.surface),
        }),
      );
      line.name = `${trace.face}: ${trace.surface}`;
      this.wallTraceGroup.add(line);
    });

    this.wallTraceGroup.visible = this.wallTracesVisible;
    return this.wallTraceGroup.children.length;
  }

  setWallTracesVisible(visible) {
    this.wallTracesVisible = Boolean(visible);
    if (this.wallTraceGroup) {
      this.wallTraceGroup.visible = this.wallTracesVisible;
    }
    return this.wallTraceEntries.length > 0;
  }

  loadSummary() {
    return {
      total: this.surfaceEntries.length,
      wallTraces: this.wallTraceEntries.length,
      loaded: this.surfaceEntries
        .filter((surface) => surface.object3d)
        .map((surface) => ({
          name: surface.name,
          label: surface.label,
          color: surface.color,
          visible: surface.object3d.visible,
        })),
      failed: this.surfaceEntries
        .filter((surface) => surface.error)
        .map((surface) => ({
          name: surface.name,
          label: surface.label,
          message: errorMessage(surface.error),
        })),
    };
  }

  setSurfaceVisible(surfaceName, visible) {
    const matching = this.surfaceEntries.filter(
      (surface) => surface.name === surfaceName,
    );
    matching.forEach((surface) => {
      surface.visible = Boolean(visible);
      if (surface.object3d) surface.object3d.visible = surface.visible;
    });
    return matching.length > 0;
  }

  setOpacity(opacity) {
    this.opacity = clampOpacity(opacity);
    this.surfaceEntries.forEach((surface) => {
      surface.materials.forEach((material) => {
        material.opacity = this.opacity;
        material.transparent = this.opacity < 1;
        material.depthWrite = this.opacity >= 1;
        material.needsUpdate = true;
      });
    });
  }

  setWireframe(enabled) {
    this.wireframe = Boolean(enabled);
    this.surfaceEntries.forEach((surface) => {
      surface.materials.forEach((material) => {
        material.wireframe = this.wireframe;
        material.needsUpdate = true;
      });
    });
  }

  setVerticalScale(scale) {
    if (typeof scale !== "number" || !Number.isFinite(scale) || scale <= 0) {
      throw new TypeError("vertical scale must be a positive finite number");
    }
    this.verticalScale = scale;
    this.applyVerticalTransform();
    if (this.baseBox && this.modelCenter) {
      this.refreshHelpers();
      this.setCameraView(this.currentCameraView);
    }
  }

  applyVerticalTransform() {
    if (!this.modelGroup || !this.modelCenter) return;
    this.modelGroup.scale.set(1, 1, this.verticalScale);
    this.modelGroup.position.set(
      0,
      0,
      this.modelCenter.z * (1 - this.verticalScale),
    );
    this.modelGroup.updateMatrixWorld(true);
  }

  frameBox() {
    if (!this.baseBox || !this.modelCenter) return null;
    const box = this.baseBox.clone();
    box.min.z = this.modelCenter.z
      + ((box.min.z - this.modelCenter.z) * this.verticalScale);
    box.max.z = this.modelCenter.z
      + ((box.max.z - this.modelCenter.z) * this.verticalScale);
    return box;
  }

  refreshHelpers() {
    const box = this.frameBox();
    if (!box || box.isEmpty()) return;

    if (this.boundsHelper) {
      this.scene.remove(this.boundsHelper);
      disposeObject(this.boundsHelper);
    }
    if (this.axesHelper) {
      this.scene.remove(this.axesHelper);
      disposeObject(this.axesHelper);
    }

    this.boundsHelper = new THREE.Box3Helper(box, 0x657084);
    this.scene.add(this.boundsHelper);

    const size = box.getSize(new THREE.Vector3());
    const axesLength = Math.max(size.x, size.y, size.z, 1) * 0.24;
    this.axesHelper = new THREE.AxesHelper(axesLength);
    this.axesHelper.position.copy(box.min);
    this.axesHelper.userData.axisColors = {
      X: "#ff0000",
      Y: "#00ff00",
      Z: "#0000ff",
    };
    this.scene.add(this.axesHelper);
  }

  setCameraView(viewName) {
    if (!CAMERA_VIEWS.has(viewName)) {
      throw new TypeError(
        'camera view must be "isometric", "top", "front", or "side"',
      );
    }
    const box = this.frameBox();
    if (!box || box.isEmpty() || !this.camera || !this.controls) return false;

    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const radius = Math.max(sphere.radius, 0.5);
    const halfFov = THREE.MathUtils.degToRad(this.camera.fov / 2);
    const distance = (radius / Math.sin(halfFov)) * 1.15;
    const directions = {
      isometric: new THREE.Vector3(0.6, 0.5, 1).normalize(),
      top: new THREE.Vector3(0, 0, 1),
      front: new THREE.Vector3(0, 1, 0),
      side: new THREE.Vector3(1, 0, 0),
    };

    this.currentCameraView = viewName;
    this.camera.up.set(0, 0, 1);
    this.camera.near = Math.max(radius / 1000, 0.001);
    this.camera.far = Math.max(radius * 100, this.camera.near + 100);
    this.camera.position
      .copy(sphere.center)
      .addScaledVector(directions[viewName], distance);
    this.camera.updateProjectionMatrix();
    this.controls.target.copy(sphere.center);
    this.controls.minDistance = radius / 100;
    this.controls.maxDistance = radius * 50;
    this.controls.update();
    return true;
  }

  resetCamera() {
    return this.setCameraView("isometric");
  }

  resize() {
    if (this.disposed || !this.renderer || !this.camera) return;
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    if (!width || !height) return;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
  }

  startAnimation() {
    if (this.animationFrame !== null || this.disposed) return;
    const view = this.container.ownerDocument.defaultView;
    const render = () => {
      if (this.disposed) return;
      this.controls.update();
      this.renderer.render(this.scene, this.camera);
      this.animationFrame = view.requestAnimationFrame(render);
    };
    this.animationFrame = view.requestAnimationFrame(render);
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;

    const view = this.container.ownerDocument.defaultView;
    if (this.animationFrame !== null) {
      view.cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    this.controls?.dispose();

    this.surfaceEntries.forEach((surface) => {
      if (surface.object3d) {
        this.modelGroup?.remove(surface.object3d);
        disposeObject(surface.object3d);
        surface.object3d = null;
        surface.materials = [];
      }
    });
    this.clearWallTraces();
    if (this.boundsHelper) disposeObject(this.boundsHelper);
    if (this.axesHelper) disposeObject(this.axesHelper);
    this.boundsHelper = null;
    this.axesHelper = null;

    this.renderer?.renderLists?.dispose?.();
    this.renderer?.dispose();
    this.renderer?.forceContextLoss?.();
    this.canvas.remove();
  }
}

export default SurfaceModelViewer;
