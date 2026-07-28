const EPSILON = 1e-9;

function finitePoint(point) {
  return (
    point
    && Number.isFinite(point.x)
    && Number.isFinite(point.y)
  );
}

function samePoint(a, b) {
  return (
    Math.abs(a.x - b.x) <= EPSILON
    && Math.abs(a.y - b.y) <= EPSILON
  );
}

function withAlongValues(topPoints, bottomPoints) {
  const allPoints = [...topPoints, ...bottomPoints];
  if (allPoints.every((point) => Number.isFinite(point.along))) {
    return {
      top: topPoints.map((point) => ({ ...point })),
      bottom: bottomPoints.map((point) => ({ ...point })),
    };
  }

  const candidates = [topPoints, bottomPoints]
    .map((points) => {
      const start = points[0];
      const end = points[points.length - 1];
      const dx = end.x - start.x;
      const dy = end.y - start.y;
      return { dx, dy, length: Math.hypot(dx, dy) };
    })
    .sort((a, b) => b.length - a.length);
  const axis = candidates[0];
  if (!axis || axis.length <= EPSILON) return null;

  const ux = axis.dx / axis.length;
  const uy = axis.dy / axis.length;
  const addAlong = (point) => ({
    ...point,
    along: (point.x * ux) + (point.y * uy),
  });
  return {
    top: topPoints.map(addAlong),
    bottom: bottomPoints.map(addAlong),
  };
}

function normalizeDirection(points) {
  const normalized = points[points.length - 1].along < points[0].along
    ? [...points].reverse()
    : [...points];
  for (let index = 1; index < normalized.length; index += 1) {
    if (normalized[index].along + EPSILON < normalized[index - 1].along) {
      return null;
    }
  }
  return normalized;
}

function interpolate(a, b, along) {
  const span = b.along - a.along;
  if (Math.abs(span) <= EPSILON) return { ...a };
  const ratio = (along - a.along) / span;
  return {
    x: a.x + ((b.x - a.x) * ratio),
    y: a.y + ((b.y - a.y) * ratio),
    along,
  };
}

function appendDistinct(points, point) {
  if (!points.length || !samePoint(points[points.length - 1], point)) {
    points.push(point);
  }
}

function clipPolyline(points, low, high) {
  const clipped = [];
  for (let index = 0; index < points.length - 1; index += 1) {
    const start = points[index];
    const end = points[index + 1];
    if (end.along < low - EPSILON || start.along > high + EPSILON) {
      continue;
    }
    if (Math.abs(end.along - start.along) <= EPSILON) {
      if (start.along >= low - EPSILON && start.along <= high + EPSILON) {
        appendDistinct(clipped, start);
        appendDistinct(clipped, end);
      }
      continue;
    }
    const segmentLow = Math.max(low, start.along);
    const segmentHigh = Math.min(high, end.along);
    if (segmentLow > segmentHigh + EPSILON) continue;
    appendDistinct(clipped, interpolate(start, end, segmentLow));
    appendDistinct(clipped, interpolate(start, end, segmentHigh));
  }
  return clipped;
}

function orientation(a, b, c) {
  return (
    ((b.x - a.x) * (c.y - a.y))
    - ((b.y - a.y) * (c.x - a.x))
  );
}

function onSegment(a, b, point) {
  return (
    Math.abs(orientation(a, b, point)) <= EPSILON
    && point.x >= Math.min(a.x, b.x) - EPSILON
    && point.x <= Math.max(a.x, b.x) + EPSILON
    && point.y >= Math.min(a.y, b.y) - EPSILON
    && point.y <= Math.max(a.y, b.y) + EPSILON
  );
}

function segmentsIntersect(a, b, c, d) {
  const abC = orientation(a, b, c);
  const abD = orientation(a, b, d);
  const cdA = orientation(c, d, a);
  const cdB = orientation(c, d, b);
  if (
    ((abC > EPSILON && abD < -EPSILON) || (abC < -EPSILON && abD > EPSILON))
    && ((cdA > EPSILON && cdB < -EPSILON) || (cdA < -EPSILON && cdB > EPSILON))
  ) {
    return true;
  }
  return (
    onSegment(a, b, c)
    || onSegment(a, b, d)
    || onSegment(c, d, a)
    || onSegment(c, d, b)
  );
}

function selfIntersects(points) {
  for (let first = 0; first < points.length; first += 1) {
    const firstEnd = (first + 1) % points.length;
    for (let second = first + 1; second < points.length; second += 1) {
      const secondEnd = (second + 1) % points.length;
      const adjacent = (
        first === second
        || firstEnd === second
        || secondEnd === first
      );
      if (adjacent) continue;
      if (
        segmentsIntersect(
          points[first],
          points[firstEnd],
          points[second],
          points[secondEnd],
        )
      ) {
        return true;
      }
    }
  }
  return false;
}

function polygonArea(points) {
  return Math.abs(points.reduce((sum, point, index) => {
    const next = points[(index + 1) % points.length];
    return sum + ((point.x * next.y) - (next.x * point.y));
  }, 0)) / 2;
}

export function layerFillPolygon(topPoints, bottomPoints) {
  if (
    topPoints.length < 2
    || bottomPoints.length < 2
    || !topPoints.every(finitePoint)
    || !bottomPoints.every(finitePoint)
  ) {
    return null;
  }

  const projected = withAlongValues(topPoints, bottomPoints);
  if (!projected) return null;
  const top = normalizeDirection(projected.top);
  const bottom = normalizeDirection(projected.bottom);
  if (!top || !bottom) return null;

  const low = Math.max(top[0].along, bottom[0].along);
  const high = Math.min(
    top[top.length - 1].along,
    bottom[bottom.length - 1].along,
  );
  if (high - low <= EPSILON) return null;

  const clippedTop = clipPolyline(top, low, high);
  const clippedBottom = clipPolyline(bottom, low, high);
  if (clippedTop.length < 2 || clippedBottom.length < 2) return null;

  const polygon = [];
  clippedTop.forEach((point) => appendDistinct(polygon, point));
  [...clippedBottom].reverse().forEach((point) => {
    appendDistinct(polygon, point);
  });
  if (polygon.length > 1 && samePoint(polygon[0], polygon.at(-1))) {
    polygon.pop();
  }
  if (
    polygon.length < 3
    || polygonArea(polygon) <= EPSILON
    || selfIntersects(polygon)
  ) {
    return null;
  }
  return polygon.map(({ x, y }) => ({ x, y }));
}

export function layerFillPath(topPoints, bottomPoints) {
  const polygon = layerFillPolygon(topPoints, bottomPoints);
  if (!polygon) return null;
  return polygon
    .map((point, index) => `${index ? "L" : "M"}${point.x},${point.y}`)
    .join(" ") + " Z";
}
