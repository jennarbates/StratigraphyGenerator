const PALETTE=["#c9b79c","#a8895f","#8a6d45","#6f5637","#4f3b26","#b98b63",
  "#9a9384","#7d7361","#c4a878","#8f7a52","#b0997a","#5c5240","#d8c8a8","#3a3128"];
const MATERIAL_COLORS={};
export function colorFor(m){const k=(m||"?").toUpperCase().trim();
  if(!(k in MATERIAL_COLORS))MATERIAL_COLORS[k]=PALETTE[Object.keys(MATERIAL_COLORS).length%PALETTE.length];
  return MATERIAL_COLORS[k];}
