export const state = {
  dataA: null,
  dataB: null,
  imageUrl: null,
  imageKey: null,   // identity of the currently loaded image (filename or job+url) — alignment is keyed on this, not just ?job=, so switching images via the file pickers doesn't reapply a stale align box from a different image
  calibration: null,
  activeFace: 0,
  compare: false,
};
