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

export function edgeMidpoint(start, end) {
  return {
    x: (start.x + end.x) / 2,
    y: (start.y + end.y) / 2,
  };
}

export function isShapeClosed(points) {
  if (points.length < 4) {
    return false;
  }

  const first = points[0];
  const last = points[points.length - 1];
  return first.x === last.x && first.y === last.y;
}

function pointOnSegment(point, start, end) {
  const crossProduct = (
    ((point.y - start.y) * (end.x - start.x))
    - ((point.x - start.x) * (end.y - start.y))
  );

  if (Math.abs(crossProduct) > Number.EPSILON) {
    return false;
  }

  return (
    point.x >= Math.min(start.x, end.x)
    && point.x <= Math.max(start.x, end.x)
    && point.y >= Math.min(start.y, end.y)
    && point.y <= Math.max(start.y, end.y)
  );
}

function direction(start, end, point) {
  return (
    ((end.x - start.x) * (point.y - start.y))
    - ((end.y - start.y) * (point.x - start.x))
  );
}

function segmentsIntersect(firstStart, firstEnd, secondStart, secondEnd) {
  const firstDirection = direction(firstStart, firstEnd, secondStart);
  const secondDirection = direction(firstStart, firstEnd, secondEnd);
  const thirdDirection = direction(secondStart, secondEnd, firstStart);
  const fourthDirection = direction(secondStart, secondEnd, firstEnd);

  if (
    ((firstDirection > 0 && secondDirection < 0)
      || (firstDirection < 0 && secondDirection > 0))
    && ((thirdDirection > 0 && fourthDirection < 0)
      || (thirdDirection < 0 && fourthDirection > 0))
  ) {
    return true;
  }

  return (
    (firstDirection === 0 && pointOnSegment(secondStart, firstStart, firstEnd))
    || (secondDirection === 0 && pointOnSegment(secondEnd, firstStart, firstEnd))
    || (thirdDirection === 0 && pointOnSegment(firstStart, secondStart, secondEnd))
    || (fourthDirection === 0 && pointOnSegment(firstEnd, secondStart, secondEnd))
  );
}

export function hasSelfIntersection(vertices) {
  if (vertices.length < 4) {
    return false;
  }

  for (let firstEdge = 0; firstEdge < vertices.length; firstEdge += 1) {
    const firstEdgeEnd = (firstEdge + 1) % vertices.length;

    for (
      let secondEdge = firstEdge + 1;
      secondEdge < vertices.length;
      secondEdge += 1
    ) {
      const secondEdgeEnd = (secondEdge + 1) % vertices.length;
      const edgesAreAdjacent = (
        firstEdgeEnd === secondEdge
        || secondEdgeEnd === firstEdge
      );

      if (edgesAreAdjacent) {
        continue;
      }

      if (
        segmentsIntersect(
          vertices[firstEdge],
          vertices[firstEdgeEnd],
          vertices[secondEdge],
          vertices[secondEdgeEnd],
        )
      ) {
        return true;
      }
    }
  }

  return false;
}
