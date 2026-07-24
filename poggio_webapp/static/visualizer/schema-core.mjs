export function ingest(d){
  if(!d||typeof d!=="object") return d;
  // Already in trenchProfiles shape (a real illustrator extraction, OR a
  // field sheet pre-adapted server-side by fieldwall_to_profiles). The
  // server adapter keys depth as `depthMeters` because that is what the
  // coordinate converter reads — remap in place so the visualizer's
  // xCoordinateMeters/yCoordinateMeters filter can see the points.
  if(d.trenchProfiles){
    const fix=p=>{ if(!p||typeof p!=="object")return;
      if(typeof p.xCoordinateMeters!=="number"&&typeof p.xMeters==="number")
        p.xCoordinateMeters=p.xMeters;
      if(typeof p.yCoordinateMeters!=="number"&&typeof p.depthMeters==="number")
        p.yCoordinateMeters=p.depthMeters; };
    (d.trenchProfiles||[]).forEach(f=>(f.layers||[]).forEach(l=>{
      (l.topBoundary||[]).forEach(fix);
      (l.bottomBoundary||[]).forEach(fix);
      (l.featuresInLayer||[]).forEach(ft=>{
        (ft.shapePoints||[]).forEach(fix);
        if(typeof ft.approxYMeters!=="number"&&typeof ft.approxDepthMeters==="number")
          ft.approxYMeters=ft.approxDepthMeters; });
    }));
    return d;
  }
  if(!(d.loci||d.layers)) return d;
  const munsell={};
  (d.loci||[]).forEach(e=>{
    const num=String(e.locusNumber??"").trim();
    if(!num||num in munsell)return;   // duplicate loci: keep the first, like the Python adapter
    let m=e.munsell;
    if(m&&typeof m==="object")
      m=[m.raw,m.colorName].filter(v=>v&&String(v).trim().toLowerCase()!=="none").join(" ");
    munsell[num]=(m&&String(m).trim())||null;
  });
  const pt=p=>{
    const adapted={
      xCoordinateMeters:(typeof p.xMeters==="number")?p.xMeters:p.xCoordinateMeters,
      yCoordinateMeters:(typeof p.depthMeters==="number")?p.depthMeters:p.yCoordinateMeters,
      confidence:p.confidence};
    if(Object.prototype.hasOwnProperty.call(p,"sourcePixel"))
      adapted.sourcePixel=p.sourcePixel;
    return adapted;
  };
  const layers=(d.layers||[]).map((l,i)=>{
    const num=String(l.locusNumber??"").trim();
    const name=num?(munsell[num]?`Locus ${num} (${munsell[num]})`:`Locus ${num}`):`layer_${i}`;
    return {layerName:name, inferredMaterial:name,
            topBoundary:(l.topBoundary||[]).map(pt),
            bottomBoundary:(l.bottomBoundary||[]).map(pt),
            _labelBoundary:"inside",
            featuresInLayer:(l.featuresInLayer||[]).map(ft=>({
              feature:ft.feature, description:ft.description,
              shapePoints:(ft.shapePoints||[]).map(pt),
              approxXMeters:ft.approxXMeters, approxYMeters:ft.approxDepthMeters,
              approxWidthMeters:ft.approxWidthMeters, approxHeightMeters:ft.approxHeightMeters}))};
  });
  return {metadata:{trenchLabel:d.trenchLabel||d.faceLabel||"field wall"},
          trenchProfiles:[{face:d.faceLabel||d.trenchLabel||"field wall", layers}]};
}
