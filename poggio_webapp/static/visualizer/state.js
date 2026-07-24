export const state = {
  dataA: null,
  dataB: null,
  imageUrl: null,
  imageKey: null,   // identity of the currently loaded image (filename or job+url) — alignment is keyed on this, not just ?job=, so switching images via the file pickers doesn't reapply a stale align box from a different image
  markerCalib: null, // {origin_px:[x,y], px_per_m} from the field-wall marker-detection stage, when the server has it and it matches the served image — lets svg.js place the overlay exactly instead of falling back to the manual drag-box
  activeFace: 0,
  compare: false,
};