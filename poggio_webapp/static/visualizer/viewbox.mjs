// Pure coordinate-space sizing for the legacy (non-calibrated) overlay.
// pad is a fraction of maxX/maxY added as margin around the data on every
// side. The overlay's viewBox must match whatever box the user dragged in
// alignment.js 1:1 — any margin here shows up as the overlay sitting
// inset from the dragged box instead of flush with it. Default pad is 0
// for that reason; a nonzero pad is only safe if the alignment box itself
// is inflated by the same fraction, which alignment.js currently does not
// do.
export function legacyViewBox(maxX, maxY, pad = 0) {
  const vbW = maxX * (1 + 2 * pad);
  const vbH = maxY * (1 + 2 * pad);
  const ox = maxX * pad;
  const oy = maxY * pad;
  return { vbW, vbH, ox, oy };
}
