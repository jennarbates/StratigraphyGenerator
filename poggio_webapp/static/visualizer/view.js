import { colorFor } from "./colors.js";
import { $, esc } from "./dom.js";
import {
  alignmentUiModel,
  hasExactCalibration,
} from "./alignment-policy.mjs";
import { createModel3dViewer } from "./model3d.js";
import {
  cameraControlModel,
  extentSize,
  model3dControlState,
  modelLoadStatusSummary,
  setAllSurfaceVisibility,
} from "./model3d-core.mjs";
import { buildSVG, faceExtent } from "./svg.js";
import { state } from "./state.js";
import { viewModeModel } from "./view-mode.mjs";

let model3dControls = null;

export function ready(){
  const primary = state.dataA || state.dataB;
  const mode = resolvedViewMode();
  state.viewMode = mode.mode;
  if(!primary){
    $("controls").style.display="none";
    applyViewMode(mode);
    return;
  }
  const faces = primary.trenchProfiles || [];
  // switching to a JSON with fewer faces must not leave state.activeFace pointing
  // past the end (the old "no face #3" after a 3-face -> 1-face swap)
  if(state.activeFace >= faces.length) state.activeFace = 0;
  const m = primary.metadata || {};
  $("meta").innerHTML = m.trenchLabel
    ? `Trench <b>${m.trenchLabel}</b> · ${(m.credits&&m.credits.year)||"—"} · ${faces.length} face(s)` : "";

  const tabs=$("faceTabs"); tabs.innerHTML="";
  faces.forEach((f,i)=>{const b=document.createElement("button");
    b.className="face-tab"+(i===state.activeFace?" active":"");
    b.textContent=f.face||("Face "+(i+1));
    b.onclick=()=>{state.activeFace=i;draw();document.querySelectorAll(".face-tab").forEach((t,j)=>t.classList.toggle("active",j===i));};
    tabs.appendChild(b);});

  const legend=$("legend"); legend.innerHTML=""; const seen=new Set();
  [state.dataA,state.dataB].forEach(D=>{ if(!D)return;
    (D.trenchProfiles||[]).forEach(f=>(f.layers||[]).forEach(l=>{
      const mat=l.inferredMaterial||l.layerName||"?"; if(seen.has(mat))return; seen.add(mat);
      const row=document.createElement("div");row.className="legend-item";
      row.innerHTML=`<span class="swatch" style="background:${colorFor(mat)}"></span>${mat}`;
      legend.appendChild(row);}));});

  $("controls").style.display="block";
  ["tFill","tBounds","tPoints","tFeatures","tGrid","tLabels"].forEach(id=>$(id).onchange=draw);
  draw();
  applyViewMode(mode);
}

function resolvedViewMode(requestedMode=state.viewModeExplicit?state.viewMode:null){
  return viewModeModel({
    hasModel3d: Boolean(state.model3d),
    hasExtraction: Boolean(state.dataA || state.dataB),
    openedFromJob: state.openedFromJob,
    requestedMode,
  });
}

function selectViewMode(requestedMode){
  const mode=resolvedViewMode(requestedMode);
  if(mode.mode!==requestedMode) return;
  state.viewMode=requestedMode;
  state.viewModeExplicit=true;
  applyViewMode(mode);
  if(requestedMode==="2d"&&(state.dataA||state.dataB)) draw();
}

function applyViewMode(mode){
  const mode2d=$("mode2d"), mode3d=$("mode3d");
  mode2d.disabled=!mode.canSelect2d;
  mode2d.classList.toggle("active",mode.mode==="2d");
  mode2d.setAttribute("aria-pressed",String(mode.mode==="2d"));
  mode2d.onclick=()=>selectViewMode("2d");

  mode3d.hidden=!mode.canSelect3d;
  mode3d.classList.toggle("active",mode.mode==="3d");
  mode3d.setAttribute("aria-pressed",String(mode.mode==="3d"));
  mode3d.onclick=()=>selectViewMode("3d");

  $("controls2d").hidden=!mode.show2dControls;
  $("controls3d").hidden=!mode.show3dControls;
  $("view2d").hidden=mode.mode!=="2d";
  $("view3d").hidden=mode.mode!=="3d";

  if(mode.mode==="3d"){
    window.onresize=null;
    startModelViewer();
  }else{
    disposeModelViewer();
  }
}

function startModelViewer(){
  if(state.modelViewer){
    state.modelViewer.resize();
    return;
  }
  const container=$("model3dCanvas");
  const surfaces=state.model3d.surfaces.length;
  const units=state.model3d.coordinate_system.units;
  const size=extentSize(state.model3d.extent);
  $("model3dSummary").textContent=[
    `${surfaces} surface${surfaces===1?"":"s"}`,
    `${size.map(value=>Number(value.toFixed(2))).join(" × ")} ${units}`,
    "Z-up",
  ].join(" · ");
  container.replaceChildren();
  model3dControls=model3dControlState(state.model3d,name=>colorFor(name));
  setModelLoadUi({
    phase:"loading",
    loaded:0,
    failed:0,
    settled:0,
    total:surfaces,
  });

  let viewer;
  try{
    viewer=createModel3dViewer(container,state.model3d,{
      opacity:model3dControls.opacity,
      wireframe:model3dControls.wireframe,
      helpersVisible:model3dControls.helpersVisible,
      colorFor:surface=>colorFor(surface.name),
      onProgress:detail=>{
        if(viewer&&state.modelViewer!==viewer) return;
        setModelLoadUi(detail);
      },
    });
  }catch(error){
    setModelLoadUi({
      phase:"error",
      loaded:0,
      failed:0,
      total:surfaces,
    });
    console.warn("3D model viewer initialization failed",error);
    return;
  }

  state.modelViewer=viewer;
  viewer.canvas?.setAttribute(
    "aria-describedby",
    "model3dInstructions model3dStatus model3dWarning",
  );
  bindModel3dControls(viewer);
  viewer.load().catch(error=>{
    if(state.modelViewer!==viewer) return;
    const summary=viewer.loadSummary();
    setModelLoadUi({
      phase:"error",
      loaded:summary.loaded.length,
      failed:summary.failed.length,
      total:summary.total,
      failures:summary.failed,
    });
    console.warn("3D model viewer load failed",error);
  });
}

function disposeModelViewer(){
  if(!state.modelViewer) return;
  const viewer=state.modelViewer;
  state.modelViewer=null;
  model3dControls=null;
  viewer.dispose();
}

function bindModel3dControls(viewer){
  renderSurfaceControls(viewer);

  $("model3dShowAll").onclick=()=>setEverySurfaceVisible(viewer,true);
  $("model3dHideAll").onclick=()=>setEverySurfaceVisible(viewer,false);

  const opacity=$("model3dOpacity");
  opacity.value=String(model3dControls.opacity);
  updateOpacityOutput(model3dControls.opacity);
  opacity.oninput=event=>{
    const value=Number(event.target.value);
    model3dControls.opacity=value;
    updateOpacityOutput(value);
    viewer.setOpacity(value);
  };

  const wireframe=$("model3dWireframe");
  wireframe.checked=model3dControls.wireframe;
  wireframe.onchange=event=>{
    model3dControls.wireframe=event.target.checked;
    viewer.setWireframe(event.target.checked);
  };

  const helpers=$("model3dHelpers");
  helpers.checked=model3dControls.helpersVisible;
  helpers.onchange=event=>{
    model3dControls.helpersVisible=event.target.checked;
    viewer.setHelpersVisible(event.target.checked);
  };

  cameraControlModel().forEach(control=>{
    const button=$(cameraButtonId(control.id));
    if(control.command==="reset"){
      button.onclick=()=>{
        if(viewer.resetCamera()) updateCameraControls("isometric");
      };
      return;
    }
    button.onclick=()=>{
      if(viewer.setCameraView(control.view)) updateCameraControls(control.view);
    };
  });
  updateCameraControls(model3dControls.cameraView);
  setCameraControlsEnabled(false);

  $("model3dUse2d").onclick=()=>selectViewMode("2d");
  configureModelRecovery(false);
}

function renderSurfaceControls(viewer){
  const root=$("model3dSurfaces");
  root.replaceChildren();
  model3dControls.surfaces.forEach((surface,index)=>{
    const label=document.createElement("label");
    label.className="model3d-surface";

    const input=document.createElement("input");
    input.type="checkbox";
    input.checked=surface.visible;
    input.id=`model3dSurface${index}`;
    input.onchange=event=>{
      model3dControls.surfaces[index]={
        ...model3dControls.surfaces[index],
        visible:event.target.checked,
      };
      viewer.setSurfaceVisible(surface.name,event.target.checked);
    };

    const swatch=document.createElement("span");
    swatch.className="model3d-swatch";
    swatch.style.backgroundColor=surface.color;
    swatch.setAttribute("aria-hidden","true");

    const name=document.createElement("span");
    name.className="model3d-surface-name";
    name.textContent=surface.name;

    label.append(input,swatch,name);
    root.appendChild(label);
  });
}

function setEverySurfaceVisible(viewer,visible){
  model3dControls.surfaces=setAllSurfaceVisibility(
    model3dControls.surfaces,
    visible,
  );
  model3dControls.surfaces.forEach((surface,index)=>{
    const checkbox=$(`model3dSurface${index}`);
    if(checkbox) checkbox.checked=visible;
    viewer.setSurfaceVisible(surface.name,visible);
  });
}

function updateOpacityOutput(value){
  $("model3dOpacityValue").textContent=`${Math.round(value*100)}%`;
}

function cameraButtonId(id){
  const suffix=id.charAt(0).toUpperCase()+id.slice(1);
  return `model3dCamera${suffix}`;
}

function updateCameraControls(activeView){
  if(model3dControls) model3dControls.cameraView=activeView;
  cameraControlModel(activeView).forEach(control=>{
    if(control.pressed===null) return;
    $(cameraButtonId(control.id)).setAttribute(
      "aria-pressed",
      String(control.pressed),
    );
  });
}

function setCameraControlsEnabled(enabled){
  cameraControlModel().forEach(control=>{
    $(cameraButtonId(control.id)).disabled=!enabled;
  });
}

function setModelLoadUi(detail){
  const summary=modelLoadStatusSummary(detail);
  $("model3dStatus").textContent=summary.status;

  const warning=$("model3dWarning");
  const messages=[];
  if(summary.warning) messages.push(summary.warning);
  (state.model3d?.warnings||[]).forEach(message=>messages.push(message));
  warning.textContent=messages.join(" ");
  warning.hidden=messages.length===0;

  if(detail.phase==="complete"){
    setCameraControlsEnabled(detail.loaded>0);
  }else if(detail.phase==="error"){
    setCameraControlsEnabled(false);
  }
  configureModelRecovery(summary.recoverable);
}

function configureModelRecovery(visible){
  const recovery=$("model3dRecovery");
  recovery.hidden=!visible;

  const use2d=$("model3dUse2d");
  use2d.hidden=!(state.dataA||state.dataB);

  const downloads=$("model3dDownloads");
  const job=new URLSearchParams(location.search).get("job");
  downloads.hidden=!job;
  if(job) downloads.href=`/jobs/${encodeURIComponent(job)}`;
}

function drawablePoints(face){
  let n=0;
  const scan=pts=>(pts||[]).forEach(p=>{
    if(typeof p.xCoordinateMeters==="number"&&typeof p.yCoordinateMeters==="number")n++;});
  (face.layers||[]).forEach(l=>{scan(l.topBoundary);scan(l.bottomBoundary);
    (l.featuresInLayer||[]).forEach(ft=>scan(ft.shapePoints));});
  return n;
}

function panelHTML(tag, label, face){
  const {maxX,maxY}=faceExtent(face);
  const nPts=drawablePoints(face);
  return `<div class="panel">
    <div class="panel-head"><span class="${tag}">${label}</span>
      <div class="face-title">${esc(face.face||"Face")}
        <span class="chip">${(face.layers||[]).length} layers</span>
        <span class="chip">${nPts} points</span>
        <span class="chip">~${maxX.toFixed(1)}m × ${maxY.toFixed(1)}m</span></div></div>
    ${nPts===0?`<p class="hint" style="color:#8a3b2c;margin:4px 0 8px">This face has
      <b>no drawable boundary points</b> — its layers carry empty or non-numeric
      coordinates, so there is nothing to overlay. The extraction itself is the
      problem (e.g. a run where no vertex markers were found), not the visualizer.</p>`:""}
    <div class="canvas-wrap" id="wrap_${tag}">${state.imageUrl?`<img src="${state.imageUrl}">`:
      `<div style="width:640px;height:280px;background:repeating-linear-gradient(90deg,#faf7f0,#faf7f0 39px,#f0ebe0 40px)"></div>`}</div>
  </div>`;
}

export function draw(){
  const main=$("view2d");
  const A=state.dataA, B=state.compare?state.dataB:null;
  const primary=A||B; if(!primary){return;}
  const empty = $("empty"); if(empty) empty.style.display="none";

  const faceA = A ? (A.trenchProfiles||[])[state.activeFace] : null;
  const faceB = B ? (B.trenchProfiles||[])[state.activeFace] : null;
  if(!faceA && !faceB){
    const anyFaces = [A,B].some(D=>D && (D.trenchProfiles||[]).length);
    main.innerHTML = anyFaces
      ? `<div class="empty">This run has no face #${state.activeFace+1}.</div>`
      : `<div class="empty">No faces found in this JSON.<br>
         Expected either an illustrator extraction (<code>trenchProfiles</code>)
         or a field-wall extraction (<code>loci</code>/<code>layers</code>) —
         this file has neither, so there is nothing to draw.
         Grid configs, points.csv exports, and GemPy outputs are not visualizer inputs.</div>`;
    return;
  }

  const html=[];
  html.push(`<p class="hint">Coordinates are face-local: x along the face, depth positive downward. Hover any point for its value.</p>`);
  html.push(`<div class="panels">`);
  if(faceA) html.push(panelHTML("tagA", state.compare?"RUN A":"", faceA));
  if(B && faceB) html.push(panelHTML("tagB","RUN B", faceB));
  html.push(`</div>`);

  if(state.compare && A && B){
    html.push(`<div class="cmpnote">Same face, two runs. Compare boundary <b>shape</b> between panels:
      if Run A and Run B track the drawing's lines differently, the extraction changed. If layers within a
      panel are parallel copies of one another, that panel still has the offset artifact.</div>`);
  }

  const notes = primary.inferred_notes;
  if(notes&&notes.length){
    html.push(`<h2 class="section" style="border:none">Methodology notes${state.compare?" (Run A)":""}</h2><ul class="notes">`);
    (Array.isArray(notes)?notes:[notes]).forEach(n=>html.push(`<li>${esc(n)}</li>`));
    html.push(`</ul>`);
  }
  main.innerHTML=html.join("");

  const render=(tag,face)=>{
    if(!face)return;
    const wrap=$("wrap_"+tag); const img=wrap.querySelector("img");
    const {maxX,maxY}=faceExtent(face);
    const go=()=>{
      const imageWidth=img?.naturalWidth||null;
      const imageHeight=img?.naturalHeight||null;
      const calibration=hasExactCalibration(state.calibration)
        ? state.calibration
        : null;
      if(calibration&&(!imageWidth||!imageHeight))return;
      buildSVG(face,maxX,maxY,wrap,{
        calibration,
        imageWidth,
        imageHeight,
      });
      attachTips(wrap);
    };
    if(img&&(!img.naturalWidth||!img.naturalHeight))img.onload=go; else go();
  };
  render("tagA",faceA);
  if(B) render("tagB",faceB);
  updateAlignUI();
  if(state.viewMode==="2d"){
    window.onresize=()=>{render("tagA",faceA); if(B)render("tagB",faceB);};
  }
}

function updateAlignUI(){
  const btn=$("alignBtn"), reset=$("alignReset"), hint=$("alignHint");
  if(!btn||!reset||!hint) return;
  const model=alignmentUiModel(state.calibration);
  btn.disabled = model.controlsDisabled;
  reset.disabled = model.controlsDisabled;
  btn.style.opacity = reset.style.opacity = model.controlsDisabled ? 0.5 : 1;
  hint.textContent = model.message;
}

function attachTips(root=document){
  const tip=$("tip");
  root.querySelectorAll(".pt").forEach(el=>{
    el.addEventListener("mousemove",e=>{const info=el.getAttribute("data-info");if(!info)return;
      tip.textContent=info;tip.style.opacity=1;tip.style.left=(e.clientX+12)+"px";tip.style.top=(e.clientY+12)+"px";});
    el.addEventListener("mouseleave",()=>tip.style.opacity=0);
  });
}
