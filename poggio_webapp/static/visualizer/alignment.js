// --- overlay alignment ----------------------------------------------------
// The SVG's meter-space viewBox is stretched over a rectangle of the image.
// Default: the whole image (the pre-webapp assumption — true for cropped
// scans, wrong for photos with margins). ALIGN holds that rectangle as
// fractions of the image, user-adjustable by dragging a box.
//
// Keyed per actual loaded image (state.imageKey), NOT just ?job=. The file
// pickers / drag-drop path never set ?job=, so keying on job alone meant
// every locally-loaded image collapsed onto one shared "viz_align_manual"
// box — align image A, then load image B, and B silently inherits A's box
// (wrong scale, wrong crop, no visible reason why). Falls back to ?job= and
// then "manual" only when state.imageKey hasn't been set yet.
import { state } from "./state.js";

const DEFAULT_ALIGN = {x:0, y:0, w:1, h:1};
let currentKey = null;
let ALIGN = {...DEFAULT_ALIGN};

function alignKey(){
  return "viz_align_" + (state.imageKey || new URLSearchParams(location.search).get("job") || "manual");
}

function isValid(a){
  return a && a.w>0.02 && a.h>0.02 && a.x>=0 && a.y>=0 &&
    a.x+a.w<=1.001 && a.y+a.h<=1.001;
}

// Re-reads ALIGN for whichever image is current. Cheap — call it any time
// before applying, not just once at load, since imageKey can change mid-session.
function refresh(){
  const key = alignKey();
  if(key === currentKey) return;
  currentKey = key;
  let loaded = DEFAULT_ALIGN;
  try{
    const saved = localStorage.getItem(key);
    if(saved){
      const parsed = JSON.parse(saved);
      // a corrupt or sliver-thin saved box would make the overlay invisible
      // with no hint why — snap back to full-image and forget it
      if(isValid(parsed)) loaded = parsed;
      else localStorage.removeItem(key);
    }
  }catch(e){ /* ignore corrupt storage */ }
  ALIGN = loaded;
}

export function applyAlign(svg){
  if(!svg) return;
  refresh();
  svg.style.inset = "auto";
  svg.style.left   = (ALIGN.x*100) + "%";
  svg.style.top    = (ALIGN.y*100) + "%";
  svg.style.width  = (ALIGN.w*100) + "%";
  svg.style.height = (ALIGN.h*100) + "%";
}

let alignArming = false;
document.getElementById("alignBtn").onclick = ()=>{
  alignArming = true;
  document.getElementById("alignBtn").textContent = "now drag a box on the image\u2026";
  document.body.style.cursor = "crosshair";
};
document.getElementById("alignReset").onclick = ()=>{
  ALIGN = {x:0, y:0, w:1, h:1};
  try{ localStorage.removeItem(alignKey()); }catch(e){}
  document.querySelectorAll(".canvas-wrap svg").forEach(applyAlign);
};

document.addEventListener("mousedown", e=>{
  if(!alignArming) return;
  const wrap = e.target.closest(".canvas-wrap");
  if(!wrap) return;
  e.preventDefault();
  const r0 = wrap.getBoundingClientRect();
  const x0 = e.clientX, y0 = e.clientY;
  const band = document.createElement("div");
  band.style.cssText = "position:fixed;border:2px dashed var(--accent);"+
    "background:rgba(124,74,45,.08);z-index:60;pointer-events:none;";
  document.body.appendChild(band);
  const move = ev=>{
    const x=Math.min(x0,ev.clientX), y=Math.min(y0,ev.clientY);
    band.style.left=x+"px"; band.style.top=y+"px";
    band.style.width=Math.abs(ev.clientX-x0)+"px";
    band.style.height=Math.abs(ev.clientY-y0)+"px";
  };
  const up = ev=>{
    document.removeEventListener("mousemove", move);
    document.removeEventListener("mouseup", up);
    band.remove();
    document.body.style.cursor = "";
    alignArming = false;
    document.getElementById("alignBtn").textContent = "Align overlay to drawing";
    const x=Math.min(x0,ev.clientX), y=Math.min(y0,ev.clientY);
    const w=Math.abs(ev.clientX-x0), h=Math.abs(ev.clientY-y0);
    if(w<10 || h<10) return;              // accidental click — ignore
    ALIGN = {
      x:(x-r0.left)/r0.width,  y:(y-r0.top)/r0.height,
      w:w/r0.width,            h:h/r0.height,
    };
    try{ localStorage.setItem(alignKey(), JSON.stringify(ALIGN)); }catch(e){}
    document.querySelectorAll(".canvas-wrap svg").forEach(applyAlign);
  };
  document.addEventListener("mousemove", move);
  document.addEventListener("mouseup", up);
});