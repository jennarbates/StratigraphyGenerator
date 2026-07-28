import { colorFor } from "./colors.js";
import { $, esc } from "./dom.js";
import {
  alignmentUiModel,
  hasExactCalibration,
} from "./alignment-policy.mjs";
import { createModel3dViewer } from "./model3d.js";
import { buildSVG, faceExtent } from "./svg.js";
import { state } from "./state.js";
import { viewModeModel } from "./view-mode.mjs";

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
  const status=$("model3dStatus");
  const surfaces=state.model3d.surfaces.length;
  $("model3dSummary").textContent=`${surfaces} surface${surfaces===1?"":"s"} · Z-up · ${state.model3d.coordinate_system.units}`;
  status.textContent=`Loading 0 of ${surfaces} surfaces…`;
  container.replaceChildren();

  let viewer;
  try{
    viewer=createModel3dViewer(container,state.model3d,{
      onProgress:detail=>{
        if(state.modelViewer!==viewer) return;
        if(detail.phase==="loading"){
          status.textContent=`Loading ${detail.settled||0} of ${detail.total} surfaces…`;
        }else if(detail.phase==="complete"){
          status.textContent=`Loaded ${detail.loaded} of ${detail.total} surfaces.`;
        }else if(detail.phase==="error"){
          status.textContent="The 3D model could not be displayed.";
        }
      },
    });
  }catch(error){
    status.textContent="The 3D model could not be displayed.";
    console.warn("3D model viewer initialization failed",error);
    return;
  }

  state.modelViewer=viewer;
  viewer.load().catch(error=>{
    if(state.modelViewer!==viewer) return;
    status.textContent="The 3D model could not be displayed.";
    console.warn("3D model viewer load failed",error);
  });
}

function disposeModelViewer(){
  if(!state.modelViewer) return;
  const viewer=state.modelViewer;
  state.modelViewer=null;
  viewer.dispose();
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
