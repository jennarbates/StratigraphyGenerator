import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

import {
  extentCenter,
  extentSize,
} from "./model3d-core.mjs";
import {
  decodeUint16LE,
  groupCellsByLithology,
  validateVolumeMetadata,
  visibleCellRange,
} from "./volume3d-core.mjs";

const AXES = Object.freeze(["x", "y", "z"]);
const CAMERA_VIEWS = new Set(["isometric", "top", "front", "side"]);
const DEFAULT_CELL_GAP = 0.035;
const MAX_CELL_GAP = 0.25;

function errorMessage(error) {
  if (error instanceof Error && error.message) return error.message;
  return String(error);
}

function validatedCellGap(value) {
  if (
    typeof value !== "number"
    || !Number.isFinite(value)
    || value < 0
    || value > MAX_CELL_GAP
  ) {
    throw new TypeError(
      `cell gap must be a finite number from 0 through ${MAX_CELL_GAP}`,
    );
  }
  return value;
}

function normalizedInput(rawModel, options) {
  const rawVolume = rawModel?.volume ?? rawModel;
  const rawExtent = rawModel?.volume ? rawModel.extent : options.extent;
  const volume = validateVolumeMetadata(rawVolume);

  // These helpers validate all six values and return detached calculations.
  extentCenter(rawExtent);
  extentSize(rawExtent);

  return {
    volume,
    extent: rawExtent.slice(),
  };
}

function disposeMaterial(material) {
  if (Array.isArray(material)) {
    material.forEach(disposeMaterial);
  } else {
    material?.dispose?.();
  }
}

function disposeHelper(helper) {
  if (!helper) return;
  helper.geometry?.dispose?.();
  disposeMaterial(helper.material);
}

function defaultLithologyColor(lithology) {
  // A golden-angle hue step gives stable, well-separated colors for numeric IDs.
  const hue = ((lithology.id * 137.508) + 24) % 360;
  return `hsl(${hue.toFixed(3)}, 55%, 52%)`;
}

/**
 * Isolated Three.js renderer for a raw GemPy lithology block.
 *
 * The renderer owns WebGL and volume-fetch lifecycles. Page controls belong
 * in an adapter and can call the public visibility, slice, camera, and
 * disposal methods without rebuilding the scene itself.
 */
export class VolumeModelViewer {
  constructor(container, rawModel, options = {}) {
    if (!container || typeof container.appendChild !== "function") {
      throw new TypeError("container must be a DOM element");
    }

    const normalized = normalizedInput(rawModel, options);
    this.container = container;
    this.options = options;
    this.volume = normalized.volume;
    this.extent = normalized.extent;
    this.center = extentCenter(this.extent);
    this.size = extentSize(this.extent);
    this.cellSize = this.size.map(
      (axisSize, axis) => axisSize / this.volume.shape[axis],
    );
    this.cellGap = validatedCellGap(options.cellGap ?? DEFAULT_CELL_GAP);
    this.expectedCount = this.volume.shape.reduce(
      (product, dimension) => product * dimension,
      1,
    );
    this.expectedByteLength = this.expectedCount * Uint16Array.BYTES_PER_ELEMENT;
    if (!Number.isSafeInteger(this.expectedByteLength)) {
      throw new TypeError("volume byte length must be a safe integer");
    }

    this.values = null;
    this.lithologyEntries = new Map();
    this.slices = Object.fromEntries(
      this.volume.shape.map((dimension, axis) => [AXES[axis], dimension - 1]),
    );
    this.currentCameraView = "isometric";
    this.helpersVisible = options.helpersVisible !== false;
    this.disposed = false;
    this.loadPromise = null;
    this.animationFrame = null;
    this.sliceFrame = null;
    this.resizeObserver = null;
    this.fetchController = null;
    this.initializationError = null;

    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.volumeGroup = null;
    this.cellGeometry = null;
    this.boundsHelper = null;
    this.axesHelper = null;

    this.createdCanvas = !options.canvas;
    this.canvas = options.canvas
      ?? container.ownerDocument.createElement("canvas");

    try {
      this.initializeRenderer();
    } catch (error) {
      this.resizeObserver?.disconnect();
      this.controls?.dispose();
      this.renderer?.dispose();
      this.renderer?.forceContextLoss?.();
      this.initializationError = new Error(
        `The lithology volume viewer could not start: ${errorMessage(error)}`,
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
    this.canvas.setAttribute(
      "aria-label",
      "Interactive 3D lithology volume",
    );

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.rotateSpeed = 0.8;

    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x596273, 1.2));
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.25);
    keyLight.position.set(1, 1.6, 2);
    this.scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.35);
    fillLight.position.set(-1, -0.5, 0.8);
    this.scene.add(fillLight);

    this.volumeGroup = new THREE.Group();
    this.scene.add(this.volumeGroup);
    this.createHelpers();

    const ResizeObserverClass = view?.ResizeObserver;
    if (ResizeObserverClass) {
      this.resizeObserver = new ResizeObserverClass(() => this.resize());
      this.resizeObserver.observe(this.container);
    }
    this.resize();
  }

  createHelpers() {
    const box = new THREE.Box3(
      new THREE.Vector3(
        this.extent[0],
        this.extent[2],
        this.extent[4],
      ),
      new THREE.Vector3(
        this.extent[1],
        this.extent[3],
        this.extent[5],
      ),
    );
    this.boundsHelper = new THREE.Box3Helper(box, 0x657084);
    this.boundsHelper.visible = this.helpersVisible;
    this.scene.add(this.boundsHelper);

    const axesLength = Math.max(...this.size, 1) * 0.24;
    this.axesHelper = new THREE.AxesHelper(axesLength);
    this.axesHelper.position.copy(box.min);
    this.axesHelper.visible = this.helpersVisible;
    this.axesHelper.userData.axisColors = {
      X: "#ff0000",
      Y: "#00ff00",
      Z: "#0000ff",
    };
    this.scene.add(this.axesHelper);
  }

  emitProgress(detail) {
    if (typeof this.options.onProgress !== "function") return;
    this.options.onProgress({
      total: this.expectedCount,
      visible: this.visibleInstanceCount(),
      lithologies: this.lithologyEntries.size,
      ...detail,
    });
  }

  async load() {
    if (this.loadPromise) return this.loadPromise;
    this.loadPromise = this.loadVolume();
    return this.loadPromise;
  }

  async loadVolume() {
    if (this.initializationError) throw this.initializationError;
    if (this.disposed) {
      throw new Error("The lithology volume viewer has been disposed.");
    }

    const fetchImpl = this.options.fetch ?? globalThis.fetch;
    if (typeof fetchImpl !== "function") {
      throw new TypeError("A fetch implementation is required.");
    }

    const AbortControllerClass = globalThis.AbortController;
    this.fetchController = AbortControllerClass
      ? new AbortControllerClass()
      : null;
    this.emitProgress({ phase: "loading" });

    try {
      const response = await fetchImpl(this.volume.url, {
        signal: this.fetchController?.signal,
      });
      if (!response || typeof response.arrayBuffer !== "function") {
        throw new TypeError("The volume request did not return a valid response.");
      }
      if (!response.ok) {
        const status = Number.isInteger(response.status)
          ? ` (HTTP ${response.status})`
          : "";
        throw new Error(`Could not load the lithology volume${status}.`);
      }

      const payload = await response.arrayBuffer();
      if (!(payload instanceof ArrayBuffer)) {
        throw new TypeError("The volume response body must be an ArrayBuffer.");
      }
      if (payload.byteLength !== this.expectedByteLength) {
        throw new RangeError(
          `Volume response contains ${payload.byteLength} bytes; `
          + `expected ${this.expectedByteLength}.`,
        );
      }
      if (this.disposed) {
        throw new Error("The lithology volume viewer was disposed while loading.");
      }

      this.values = decodeUint16LE(payload, this.expectedCount);
      this.createInstanceMeshes();
      const sliceSummary = this.rebuildInstances();
      this.resetCamera();
      this.resize();
      this.startAnimation();

      const summary = this.loadSummary();
      this.emitProgress({
        phase: "complete",
        durationMs: sliceSummary.durationMs,
      });
      return summary;
    } catch (error) {
      if (!this.disposed) {
        this.emitProgress({ phase: "error", error });
      }
      throw error;
    } finally {
      this.fetchController = null;
    }
  }

  createInstanceMeshes() {
    const groups = groupCellsByLithology(
      this.values,
      this.volume,
    );
    const cellScale = 1 - this.cellGap;
    this.cellGeometry = new THREE.BoxGeometry(
      this.cellSize[0] * cellScale,
      this.cellSize[1] * cellScale,
      this.cellSize[2] * cellScale,
    );

    groups.forEach((group, index) => {
      const descriptor = {
        id: group.id,
        name: group.name,
      };
      const color = typeof this.options.colorFor === "function"
        ? this.options.colorFor(descriptor, index)
        : defaultLithologyColor(descriptor);
      const material = new THREE.MeshStandardMaterial({
        color,
        flatShading: true,
        roughness: 0.82,
        metalness: 0.02,
      });
      const mesh = new THREE.InstancedMesh(
        this.cellGeometry,
        material,
        group.cells.length,
      );
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      mesh.frustumCulled = false;
      mesh.userData.lithology = descriptor;
      this.volumeGroup.add(mesh);
      this.lithologyEntries.set(group.id, {
        ...descriptor,
        color: new THREE.Color(color).getStyle(),
        cells: group.cells,
        mesh,
        material,
        visible: true,
      });
    });
  }

  rebuildInstances() {
    if (!this.values || this.disposed) {
      return {
        visible: 0,
        durationMs: 0,
      };
    }

    const started = globalThis.performance?.now?.() ?? Date.now();
    const matrix = new THREE.Matrix4();
    let totalVisible = 0;

    this.lithologyEntries.forEach((entry) => {
      let instance = 0;
      entry.cells.forEach(([x, y, z]) => {
        if (
          x > this.slices.x
          || y > this.slices.y
          || z > this.slices.z
        ) {
          return;
        }
        matrix.makeTranslation(
          this.extent[0] + ((x + 0.5) * this.cellSize[0]),
          this.extent[2] + ((y + 0.5) * this.cellSize[1]),
          this.extent[4] + ((z + 0.5) * this.cellSize[2]),
        );
        entry.mesh.setMatrixAt(instance, matrix);
        instance += 1;
      });
      entry.mesh.count = instance;
      entry.mesh.instanceMatrix.needsUpdate = true;
      totalVisible += instance;
    });

    const finished = globalThis.performance?.now?.() ?? Date.now();
    const summary = {
      visible: totalVisible,
      durationMs: finished - started,
    };
    this.emitProgress({
      phase: "slices",
      ...summary,
    });
    return summary;
  }

  scheduleSliceRebuild() {
    if (this.sliceFrame !== null || this.disposed || !this.values) return;
    const view = this.container.ownerDocument.defaultView;
    this.sliceFrame = view.requestAnimationFrame(() => {
      this.sliceFrame = null;
      this.rebuildInstances();
    });
  }

  setMaximumSlice(axis, maximum) {
    if (!AXES.includes(axis)) {
      throw new TypeError('slice axis must be "x", "y", or "z"');
    }
    const normalized = visibleCellRange(
      this.volume.shape,
      { [axis]: maximum },
    );
    const nextMaximum = normalized[axis].max;
    if (this.slices[axis] === nextMaximum) return false;
    this.slices[axis] = nextMaximum;
    this.scheduleSliceRebuild();
    return true;
  }

  setSlices(slices) {
    if (!slices || typeof slices !== "object" || Array.isArray(slices)) {
      throw new TypeError("slices must be an object");
    }
    const next = { ...this.slices };
    AXES.forEach((axis) => {
      if (slices[axis] !== undefined) next[axis] = slices[axis];
    });
    const normalized = visibleCellRange(this.volume.shape, next);
    const changed = AXES.some(
      (axis) => this.slices[axis] !== normalized[axis].max,
    );
    AXES.forEach((axis) => {
      this.slices[axis] = normalized[axis].max;
    });
    if (changed) this.scheduleSliceRebuild();
    return changed;
  }

  resetSlices() {
    return this.setSlices(Object.fromEntries(
      this.volume.shape.map((dimension, axis) => [AXES[axis], dimension - 1]),
    ));
  }

  setLithologyVisible(id, visible) {
    if (!Number.isInteger(id) || id < 0 || id > 65535) {
      throw new TypeError("lithology id must be an integer from 0 through 65535");
    }
    const entry = this.lithologyEntries.get(id);
    if (!entry) return false;
    entry.visible = Boolean(visible);
    entry.mesh.visible = entry.visible;
    this.emitProgress({ phase: "visibility" });
    return true;
  }

  setHelpersVisible(visible) {
    this.helpersVisible = Boolean(visible);
    if (this.boundsHelper) this.boundsHelper.visible = this.helpersVisible;
    if (this.axesHelper) this.axesHelper.visible = this.helpersVisible;
  }

  visibleInstanceCount() {
    let count = 0;
    this.lithologyEntries.forEach((entry) => {
      if (entry.visible) count += entry.mesh.count;
    });
    return count;
  }

  loadSummary() {
    return {
      total: this.expectedCount,
      visible: this.visibleInstanceCount(),
      shape: this.volume.shape.slice(),
      slices: { ...this.slices },
      cellSize: this.cellSize.slice(),
      lithologies: [...this.lithologyEntries.values()].map((entry) => ({
        id: entry.id,
        name: entry.name,
        color: entry.color,
        instances: entry.mesh.count,
        visible: entry.visible,
      })),
    };
  }

  setCameraView(viewName) {
    if (!CAMERA_VIEWS.has(viewName)) {
      throw new TypeError(
        'camera view must be "isometric", "top", "front", or "side"',
      );
    }
    if (!this.camera || !this.controls) return false;

    const target = new THREE.Vector3(...this.center);
    const radius = Math.max(Math.hypot(...this.size) / 2, 0.5);
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
      .copy(target)
      .addScaledVector(directions[viewName], distance);
    this.camera.updateProjectionMatrix();
    this.controls.target.copy(target);
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
    this.fetchController?.abort();
    this.fetchController = null;
    if (this.animationFrame !== null) {
      view.cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
    if (this.sliceFrame !== null) {
      view.cancelAnimationFrame(this.sliceFrame);
      this.sliceFrame = null;
    }
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    this.controls?.dispose();

    this.lithologyEntries.forEach((entry) => {
      this.volumeGroup?.remove(entry.mesh);
      entry.mesh.dispose?.();
      entry.material.dispose();
    });
    this.lithologyEntries.clear();
    this.cellGeometry?.dispose();
    this.cellGeometry = null;
    disposeHelper(this.boundsHelper);
    disposeHelper(this.axesHelper);
    this.boundsHelper = null;
    this.axesHelper = null;
    this.values = null;

    this.renderer?.renderLists?.dispose?.();
    this.renderer?.dispose();
    this.renderer?.forceContextLoss?.();
    this.canvas.remove();
  }
}

export function createVolume3dViewer(container, rawModel, options = {}) {
  return new VolumeModelViewer(container, rawModel, options);
}

export default VolumeModelViewer;
