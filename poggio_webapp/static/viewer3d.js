// viewer3d.js — renders the GemPy per-surface .obj meshes as an orbitable
// 3D scene on the results page, in place of the flat matplotlib section PNG.
//
// Data source: a <script type="application/json" id="viewer3d-meshes"> tag
// holding [{name, url}, ...] written by app.py's _job_record().mesh_urls.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";

const root = document.getElementById("viewer3d");
if (root) {
  init(root);
}

function init(root) {
  const meshDataEl = document.getElementById("viewer3d-meshes");
  const meshList = meshDataEl ? JSON.parse(meshDataEl.textContent || "[]") : [];
  const canvas = document.getElementById("viewer3d-canvas");
  const wrap = root.querySelector(".viewer3d-canvas-wrap");
  const statusEl = document.getElementById("viewer3d-status");
  const legendEl = document.getElementById("viewer3d-legend");
  const veSlider = document.getElementById("viewer3d-ve");
  const veLabel = document.getElementById("viewer3d-ve-val");
  const resetBtn = document.getElementById("viewer3d-reset");

  if (!meshList.length) {
    if (statusEl) statusEl.textContent = "No mesh data was produced for this model.";
    return;
  }

  const style = getComputedStyle(document.documentElement);
  const strataVars = ["--strata-1", "--strata-2", "--strata-3", "--strata-4", "--strata-5"];
  const palette = strataVars.map((v) => (style.getPropertyValue(v) || "#8a8c53").trim());
  const colorFor = (i) => palette[i % palette.length];

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(style.getPropertyValue("--panel")?.trim() || "#ffffff");

  const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 5000);

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.rotateSpeed = 0.8;

  scene.add(new THREE.AmbientLight(0xffffff, 0.55));
  const key = new THREE.DirectionalLight(0xffffff, 1.1);
  key.position.set(1, 1.6, 1);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.4);
  fill.position.set(-1, 0.6, -1);
  scene.add(fill);

  // GemPy's Z axis is elevation; rotate so it reads as "up" on screen, and
  // scale that same local axis (pre-rotation) for vertical exaggeration.
  const modelGroup = new THREE.Group();
  modelGroup.rotation.x = -Math.PI / 2;
  scene.add(modelGroup);

  let initialCameraPos = null;
  let initialTarget = null;
  let loadedCount = 0;
  let failedCount = 0;

  const loader = new OBJLoader();
  const surfaces = [];

  meshList.forEach((entry, i) => {
    const color = colorFor(i);
    loader.load(
      entry.url,
      (obj) => {
        const material = new THREE.MeshStandardMaterial({
          color,
          side: THREE.DoubleSide,
          flatShading: true,
          roughness: 0.85,
          metalness: 0.02,
        });
        obj.traverse((child) => {
          if (child.isMesh) {
            child.material = material;
          }
        });
        modelGroup.add(obj);
        surfaces.push({ name: entry.name, color, object3d: obj });
        loadedCount += 1;
        if (loadedCount + failedCount === meshList.length) onAllSettled();
      },
      undefined,
      () => {
        failedCount += 1;
        if (loadedCount + failedCount === meshList.length) onAllSettled();
      }
    );
  });

  function onAllSettled() {
    if (!loadedCount) {
      if (statusEl) statusEl.textContent = "Couldn't load the 3D mesh files.";
      return;
    }
    if (statusEl) {
      statusEl.textContent = failedCount
        ? `Loaded ${loadedCount} of ${meshList.length} surfaces (${failedCount} failed).`
        : "";
      statusEl.style.display = statusEl.textContent ? "block" : "none";
    }
    buildLegend();
    fitCameraToModel();
    resize();
    animate();
  }

  function buildLegend() {
    if (!legendEl) return;
    legendEl.innerHTML = "";
    surfaces.forEach((s) => {
      const row = document.createElement("label");
      row.className = "viewer3d-legend-row";
      const swatch = document.createElement("span");
      swatch.className = "viewer3d-swatch";
      swatch.style.background = s.color;
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = true;
      checkbox.addEventListener("change", () => {
        s.object3d.visible = checkbox.checked;
      });
      const text = document.createElement("span");
      text.textContent = s.name;
      row.append(checkbox, swatch, text);
      legendEl.appendChild(row);
    });
  }

  function fitCameraToModel() {
    modelGroup.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(modelGroup);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const radius = Math.max(size.length() / 2, 0.5);

    camera.near = radius / 100;
    camera.far = radius * 100;
    camera.updateProjectionMatrix();

    const dist = radius / Math.sin((Math.PI / 180) * (camera.fov / 2));
    const dir = new THREE.Vector3(0.6, 0.5, 1).normalize();
    camera.position.copy(center).addScaledVector(dir, dist * 1.15);
    controls.target.copy(center);
    controls.update();

    initialCameraPos = camera.position.clone();
    initialTarget = center.clone();
  }

  function resize() {
    if (!wrap) return;
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    if (!w || !h) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  }

  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }

  if (window.ResizeObserver && wrap) {
    new ResizeObserver(resize).observe(wrap);
  }
  window.addEventListener("resize", resize);

  if (veSlider) {
    veSlider.addEventListener("input", () => {
      const ve = parseFloat(veSlider.value);
      modelGroup.scale.z = ve;
      if (veLabel) veLabel.textContent = `${ve}\u00d7`;
    });
    // apply the default value once the model exists
    modelGroup.scale.z = parseFloat(veSlider.value);
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      if (!initialCameraPos || !initialTarget) return;
      camera.position.copy(initialCameraPos);
      controls.target.copy(initialTarget);
      controls.update();
    });
  }
}
