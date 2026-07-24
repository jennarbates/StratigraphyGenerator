import { applyAlign } from "./alignment.js";
import { colorFor } from "./colors.js";
import { $, esc } from "./dom.js";

// extent across a face's points
export function faceExtent(face){
  let maxX=0,maxY=0;
  const scan=pts=>(pts||[]).forEach(p=>{if(typeof p.xCoordinateMeters==="number")maxX=Math.max(maxX,p.xCoordinateMeters);
    if(typeof p.yCoordinateMeters==="number")maxY=Math.max(maxY,p.yCoordinateMeters);});
  (face.layers||[]).forEach(l=>{scan(l.topBoundary);scan(l.bottomBoundary);
    (l.featuresInLayer||[]).forEach(ft=>scan(ft.shapePoints));});
  (face.gridLabelXMeters||[]).forEach(x=>{if(typeof x==="number")maxX=Math.max(maxX,x);});
  return {maxX:maxX||1,maxY:maxY||1};
}

export function buildSVG(face, maxX, maxY, wrap){
  const vbPad=0.04, vbW=maxX*(1+2*vbPad), vbH=maxY*(1+2*vbPad);
  const ox=maxX*vbPad, oy=maxY*vbPad;
  const X=x=>x+ox, Y=y=>y+oy;
  const show=id=>$(id).checked;
  const s=[`<svg viewBox="0 0 ${vbW} ${vbH}" preserveAspectRatio="none">`];

  if(show("tGrid")&&face.gridLabelXMeters){
    face.gridLabelXMeters.forEach((x,i)=>{if(typeof x!=="number")return;
      const lbl=(face.gridLabels||[])[i]||"";
      s.push(`<line x1="${X(x)}" y1="${Y(0)}" x2="${X(x)}" y2="${Y(maxY)}" stroke="var(--grid)"
        stroke-width="${vbW*0.0012}" stroke-dasharray="${vbW*0.004} ${vbW*0.004}"/>`);
      s.push(`<text x="${X(x)}" y="${Y(0)-vbH*0.01}" font-size="${vbH*0.032}" fill="var(--ink-soft)"
        text-anchor="middle" font-family="monospace">${esc(lbl)}</text>`);});
  }

  (face.layers||[]).forEach((l,li)=>{
    const mat=l.inferredMaterial||l.layerName||"?", col=colorFor(mat);
    const line=(pts,isSurf)=>{
      const P=(pts||[]).filter(p=>typeof p.xCoordinateMeters==="number"&&typeof p.yCoordinateMeters==="number");
      if(!P.length)return;
      if(show("tBounds")&&P.length>1){
        const d=P.map((p,k)=>`${k?"L":"M"}${X(p.xCoordinateMeters)},${Y(p.yCoordinateMeters)}`).join(" ");
        s.push(`<path d="${d}" fill="none" stroke="${isSurf?'var(--surface-line)':col}"
          stroke-width="${vbW*(isSurf?0.003:0.0022)}" stroke-linejoin="round" stroke-linecap="round" opacity="0.92"/>`);
      }
      if(show("tPoints"))P.forEach(p=>s.push(`<circle class="pt" cx="${X(p.xCoordinateMeters)}" cy="${Y(p.yCoordinateMeters)}"
        r="${vbW*0.0035}" fill="${col}" stroke="#fff" stroke-width="${vbW*0.0008}" opacity="${p.confidence?0.5:1}"
        data-info="${esc(mat)} · x=${p.xCoordinateMeters}m depth=${p.yCoordinateMeters}m${p.confidence?' · '+esc(p.confidence):''}"/>`));
      if(show("tLabels")&&!isSurf&&P.length){const mid=P[Math.floor(P.length/2)];
        s.push(`<text x="${X(mid.xCoordinateMeters)}" y="${Y(mid.yCoordinateMeters)-vbH*0.006}" font-size="${vbH*0.026}"
          fill="${col}" text-anchor="middle" font-family="monospace" paint-order="stroke" stroke="#fff"
          stroke-width="${vbH*0.006}">${esc(mat)}</text>`);}
    };
    line(l.topBoundary, li===0);
    line(l.bottomBoundary, false);
  });

  if(show("tFeatures"))(face.layers||[]).forEach(l=>(l.featuresInLayer||[]).forEach(ft=>{
    const P=(ft.shapePoints||[]).filter(p=>typeof p.xCoordinateMeters==="number");
    if(P.length>1){
      const d=P.map((p,k)=>`${k?"L":"M"}${X(p.xCoordinateMeters)},${Y(p.yCoordinateMeters)}`).join(" ");
      s.push(`<path d="${d}" fill="none" stroke="var(--feature)" stroke-width="${vbW*0.0035}" stroke-linejoin="round" opacity="0.9"/>`);
      P.forEach(p=>s.push(`<circle class="pt" cx="${X(p.xCoordinateMeters)}" cy="${Y(p.yCoordinateMeters)}" r="${vbW*0.003}"
        fill="var(--feature)" stroke="#fff" stroke-width="${vbW*0.0007}"
        data-info="${esc(ft.feature||'feature')} · x=${p.xCoordinateMeters}m depth=${p.yCoordinateMeters}m"/>`));
    } else if(typeof ft.approxXMeters==="number"){
      const x=ft.approxXMeters,y=ft.approxYMeters||0,w=ft.approxWidthMeters||maxX*0.03,h=ft.approxHeightMeters||maxY*0.03;
      s.push(`<rect class="pt" x="${X(x-w/2)}" y="${Y(y-h/2)}" width="${w}" height="${h}" fill="var(--feature)"
        fill-opacity="0.16" stroke="var(--feature)" stroke-width="${vbW*0.0018}"
        data-info="${esc(ft.feature||'feature')} · x=${x}m depth=${y}m ${w}×${h}m"/>`);
      s.push(`<circle class="pt" cx="${X(x)}" cy="${Y(y)}" r="${vbW*0.003}" fill="var(--feature)" stroke="#fff"
        stroke-width="${vbW*0.0007}" data-info="${esc(ft.feature||'feature')} · x=${x}m depth=${y}m"/>`);
    }
  }));

  s.push(`</svg>`);
  const old=wrap.querySelector("svg"); if(old)old.remove();
  wrap.insertAdjacentHTML("beforeend", s.join(""));
  applyAlign(wrap.querySelector("svg"));
}
