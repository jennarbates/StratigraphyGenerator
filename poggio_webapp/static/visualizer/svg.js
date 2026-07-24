import { applyAlign } from "./alignment.js";
import { pointInsideBand } from "../boundary-label.js";
import { colorFor } from "./colors.js";
import {
  calibrationAxes,
  pointToSourcePixel,
  projectPolyline,
} from "./coordinates.mjs";
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

function validSourcePixel(point){
  return Array.isArray(point?.sourcePixel)
    && point.sourcePixel.length===2
    && Number.isFinite(point.sourcePixel[0])
    && Number.isFinite(point.sourcePixel[1]);
}

function projectablePoint(point){
  if(!point||typeof point!=="object")return false;
  if(Object.prototype.hasOwnProperty.call(point,"sourcePixel"))
    return validSourcePixel(point);
  return (
    Number.isFinite(point.xMeters)
      && Number.isFinite(point.depthMeters)
  )||(
    Number.isFinite(point.xCoordinateMeters)
      && Number.isFinite(point.yCoordinateMeters)
  );
}

function meterX(point){
  return Number.isFinite(point.xMeters)
    ? point.xMeters
    : point.xCoordinateMeters;
}

function meterDepth(point){
  return Number.isFinite(point.depthMeters)
    ? point.depthMeters
    : point.yCoordinateMeters;
}

function metricPoint(x, depth){
  return {xMeters:x,depthMeters:depth};
}

function imageDimension(value,name){
  if(!Number.isFinite(value)||value<=0)
    throw new RangeError(`${name} must be a positive finite number in calibrated mode.`);
  return value;
}

function buildCalibratedSVG(
  face,
  wrap,
  {calibration,imageWidth,imageHeight},
){
  const width=imageDimension(imageWidth,"imageWidth");
  const height=imageDimension(imageHeight,"imageHeight");
  const axes=calibrationAxes(calibration);
  const show=id=>$(id).checked;
  const s=[`<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">`];

  if(show("tGrid")&&face.gridLabelXMeters){
    const gridDepthMeters=Math.hypot(width,height)/axes.pxPerMeter;
    face.gridLabelXMeters.forEach((x,i)=>{if(typeof x!=="number")return;
      const lbl=(face.gridLabels||[])[i]||"";
      const [start,end]=projectPolyline([
        metricPoint(x,0),
        metricPoint(x,gridDepthMeters),
      ],calibration);
      const label=pointToSourcePixel(metricPoint(x,0),calibration);
      s.push(`<line x1="${start.x}" y1="${start.y}" x2="${end.x}" y2="${end.y}" stroke="var(--grid)"
        stroke-width="${width*0.0012}" stroke-dasharray="${width*0.004} ${width*0.004}"/>`);
      s.push(`<text x="${label.x}" y="${label.y-height*0.01}" font-size="${height*0.032}" fill="var(--ink-soft)"
        text-anchor="middle" font-family="monospace">${esc(lbl)}</text>`);});
  }

  const layerLabels=[];
  (face.layers||[]).forEach((l,li)=>{
    const mat=l.inferredMaterial||l.layerName||"?", col=colorFor(mat);
    const line=(pts,isSurf)=>{
      const P=(pts||[]).filter(projectablePoint);
      if(!P.length)return {source:[],pixels:[]};
      const pixels=projectPolyline(P,calibration);
      if(show("tBounds")&&pixels.length>1){
        const d=pixels.map((p,k)=>`${k?"L":"M"}${p.x},${p.y}`).join(" ");
        s.push(`<path d="${d}" fill="none" stroke="${isSurf?'var(--surface-line)':col}"
          stroke-width="${width*(isSurf?0.003:0.0022)}" stroke-linejoin="round" stroke-linecap="round" opacity="0.92"/>`);
      }
      if(show("tPoints"))P.forEach((p,i)=>{
        const pixel=pixels[i];
        s.push(`<circle class="pt" cx="${pixel.x}" cy="${pixel.y}"
        r="${width*0.0035}" fill="${col}" stroke="#fff" stroke-width="${width*0.0008}" opacity="${p.confidence?0.5:1}"
        data-info="${esc(mat)} · x=${meterX(p)}m depth=${meterDepth(p)}m${p.confidence?' · '+esc(p.confidence):''}"/>`);});
      return {source:P,pixels};
    };
    const topBoundary=line(l.topBoundary, li===0);
    const bottomBoundary=line(l.bottomBoundary, false);
    if(show("tLabels")){
      const labelsInside=l._labelBoundary==="inside";
      const inside=labelsInside
        ? pointInsideBand(
            topBoundary.source,
            bottomBoundary.source,
            meterX,
            meterDepth)
        : null;
      const fallback=bottomBoundary.source.length
        ? bottomBoundary.source[Math.floor(bottomBoundary.source.length/2)]
        : null;
      const labelPoint=inside
        ? pointToSourcePixel(metricPoint(inside.x,inside.y),calibration)
        : fallback
          ? pointToSourcePixel(fallback,calibration)
          : null;
      if(labelPoint){
        layerLabels.push(`<text x="${labelPoint.x}" y="${labelPoint.y-(inside?0:height*0.006)}" font-size="${height*0.026}"
          fill="${col}" text-anchor="middle" dominant-baseline="${inside?'middle':'auto'}"
          font-family="monospace" font-weight="${inside?'700':'400'}" paint-order="stroke fill"
          stroke="#fff" stroke-width="${height*0.006}" stroke-linejoin="round">${esc(mat)}</text>`);
      }
    }
  });

  if(show("tFeatures"))(face.layers||[]).forEach(l=>(l.featuresInLayer||[]).forEach(ft=>{
    const P=(ft.shapePoints||[]).filter(projectablePoint);
    if(P.length>1){
      const pixels=projectPolyline(P,calibration);
      const d=pixels.map((p,k)=>`${k?"L":"M"}${p.x},${p.y}`).join(" ");
      s.push(`<path d="${d}" fill="none" stroke="var(--feature)" stroke-width="${width*0.0035}" stroke-linejoin="round" opacity="0.9"/>`);
      P.forEach((p,i)=>{
        const pixel=pixels[i];
        s.push(`<circle class="pt" cx="${pixel.x}" cy="${pixel.y}" r="${width*0.003}"
        fill="var(--feature)" stroke="#fff" stroke-width="${width*0.0007}"
        data-info="${esc(ft.feature||'feature')} · x=${meterX(p)}m depth=${meterDepth(p)}m"/>`);});
    } else if(typeof ft.approxXMeters==="number"){
      const x=ft.approxXMeters,y=ft.approxYMeters||0;
      const w=ft.approxWidthMeters||width*0.03/axes.pxPerMeter;
      const h=ft.approxHeightMeters||height*0.03/axes.pxPerMeter;
      const corners=projectPolyline([
        metricPoint(x-w/2,y-h/2),
        metricPoint(x+w/2,y-h/2),
        metricPoint(x+w/2,y+h/2),
        metricPoint(x-w/2,y+h/2),
      ],calibration);
      const center=pointToSourcePixel(metricPoint(x,y),calibration);
      const d=corners.map((p,k)=>`${k?"L":"M"}${p.x},${p.y}`).join(" ")+" Z";
      s.push(`<path class="pt" d="${d}" fill="var(--feature)"
        fill-opacity="0.16" stroke="var(--feature)" stroke-width="${width*0.0018}"
        data-info="${esc(ft.feature||'feature')} · x=${x}m depth=${y}m ${w}×${h}m"/>`);
      s.push(`<circle class="pt" cx="${center.x}" cy="${center.y}" r="${width*0.003}" fill="var(--feature)" stroke="#fff"
        stroke-width="${width*0.0007}" data-info="${esc(ft.feature||'feature')} · x=${x}m depth=${y}m"/>`);
    }
  }));

  s.push(...layerLabels);
  s.push(`</svg>`);
  const old=wrap.querySelector("svg"); if(old)old.remove();
  wrap.insertAdjacentHTML("beforeend", s.join(""));
}

export function buildSVG(
  face,
  maxX,
  maxY,
  wrap,
  {
    calibration = null,
    imageWidth = null,
    imageHeight = null,
  } = {},
){
  const calibrated=calibration!==null;
  if(calibrated){
    buildCalibratedSVG(face,wrap,{calibration,imageWidth,imageHeight});
    return;
  }
  buildLegacySVG(face,maxX,maxY,wrap);
}

function buildLegacySVG(face, maxX, maxY, wrap){
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

  const layerLabels=[];
  (face.layers||[]).forEach((l,li)=>{
    const mat=l.inferredMaterial||l.layerName||"?", col=colorFor(mat);
    const line=(pts,isSurf)=>{
      const P=(pts||[]).filter(p=>typeof p.xCoordinateMeters==="number"&&typeof p.yCoordinateMeters==="number");
      if(!P.length)return P;
      if(show("tBounds")&&P.length>1){
        const d=P.map((p,k)=>`${k?"L":"M"}${X(p.xCoordinateMeters)},${Y(p.yCoordinateMeters)}`).join(" ");
        s.push(`<path d="${d}" fill="none" stroke="${isSurf?'var(--surface-line)':col}"
          stroke-width="${vbW*(isSurf?0.003:0.0022)}" stroke-linejoin="round" stroke-linecap="round" opacity="0.92"/>`);
      }
      if(show("tPoints"))P.forEach(p=>s.push(`<circle class="pt" cx="${X(p.xCoordinateMeters)}" cy="${Y(p.yCoordinateMeters)}"
        r="${vbW*0.0035}" fill="${col}" stroke="#fff" stroke-width="${vbW*0.0008}" opacity="${p.confidence?0.5:1}"
        data-info="${esc(mat)} · x=${p.xCoordinateMeters}m depth=${p.yCoordinateMeters}m${p.confidence?' · '+esc(p.confidence):''}"/>`));
      return P;
    };
    const topPoints=line(l.topBoundary, li===0);
    const bottomPoints=line(l.bottomBoundary, false);
    if(show("tLabels")){
      const labelsInside=l._labelBoundary==="inside";
      const inside=labelsInside
        ? pointInsideBand(
            topPoints,
            bottomPoints,
            p=>p.xCoordinateMeters,
            p=>p.yCoordinateMeters)
        : null;
      const fallback=bottomPoints.length
        ? bottomPoints[Math.floor(bottomPoints.length/2)]
        : null;
      const labelX=inside?inside.x:fallback?.xCoordinateMeters;
      const labelY=inside?inside.y:fallback?.yCoordinateMeters;
      if(typeof labelX==="number"&&typeof labelY==="number"){
        layerLabels.push(`<text x="${X(labelX)}" y="${Y(labelY)-(inside?0:vbH*0.006)}" font-size="${vbH*0.026}"
          fill="${col}" text-anchor="middle" dominant-baseline="${inside?'middle':'auto'}"
          font-family="monospace" font-weight="${inside?'700':'400'}" paint-order="stroke fill"
          stroke="#fff" stroke-width="${vbH*0.006}" stroke-linejoin="round">${esc(mat)}</text>`);
      }
    }
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

  s.push(...layerLabels);
  s.push(`</svg>`);
  const old=wrap.querySelector("svg"); if(old)old.remove();
  wrap.insertAdjacentHTML("beforeend", s.join(""));
  applyAlign(wrap.querySelector("svg"));
}
