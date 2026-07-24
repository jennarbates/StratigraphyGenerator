/**
 * The canvas uses 200 pixels per metre: at this scale the fixed 3m × 2m face
 * is 600 × 400 CSS pixels, large enough to work with on a typical laptop, and
 * the default 0.25m grid lands on exact 50-pixel intervals. Keep every future
 * geometry conversion anchored to this constant so display and saved real-world
 * measurements remain consistent.
 */
export const PIXELS_PER_METER = 200;
export const CANVAS_WIDTH_METERS = 3;
export const CANVAS_HEIGHT_METERS = 2;
export const GRID_SPACING_METERS = 0.25;

export function metersToPixels(meters, pixelsPerMeter) {
  return meters * pixelsPerMeter;
}

export function pixelsToMeters(pixels, pixelsPerMeter) {
  return pixels / pixelsPerMeter;
}

/**
 * Snap to the closest grid intersection. A point exactly halfway between two
 * grid lines rounds to the line with the higher coordinate.
 */
export function nearestGridPoint(x, y, gridSpacingPixels) {
  if (gridSpacingPixels <= 0) {
    throw new RangeError("Grid spacing must be greater than zero.");
  }

  const snapCoordinate = (coordinate) => (
    Math.floor((coordinate / gridSpacingPixels) + 0.5) * gridSpacingPixels
  );

  return {
    x: snapCoordinate(x),
    y: snapCoordinate(y),
  };
}
