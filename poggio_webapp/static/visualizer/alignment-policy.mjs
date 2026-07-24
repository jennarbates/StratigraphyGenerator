import { calibrationAxes } from "./coordinates.mjs";

const EXACT_MESSAGE = "Exact source-image alignment is active.";
const APPROXIMATE_MESSAGE = (
  "The overlay has no source-image calibration. "
  + "Drag a box over the drawing to align it."
);

export function hasExactCalibration(calibration) {
  try {
    if (
      calibration === null
      || typeof calibration !== "object"
      || Array.isArray(calibration)
      || calibration.kind !== "manual"
      || !Number.isFinite(calibration.ref_meters)
      || calibration.ref_meters <= 0
    ) {
      return false;
    }

    calibrationAxes(calibration);
    return true;
  } catch {
    return false;
  }
}

export function alignmentUiModel(calibration) {
  const exact = hasExactCalibration(calibration);
  return {
    exact,
    controlsDisabled: exact,
    message: exact ? EXACT_MESSAGE : APPROXIMATE_MESSAGE,
  };
}
