function numericPoints(points, getX, getY) {
  return (points || [])
    .map((point) => ({ x: getX(point), y: getY(point) }))
    .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
    .sort((a, b) => a.x - b.x || a.y - b.y);
}

function yAtX(points, x) {
  if (x <= points[0].x) return points[0].y;
  if (x >= points[points.length - 1].x) return points[points.length - 1].y;

  for (let i = 0; i < points.length - 1; i += 1) {
    const left = points[i];
    const right = points[i + 1];
    if (left.x <= x && x <= right.x) {
      if (Math.abs(right.x - left.x) < Number.EPSILON) {
        return (left.y + right.y) / 2;
      }
      const amount = (x - left.x) / (right.x - left.x);
      return left.y + amount * (right.y - left.y);
    }
  }
  return null;
}

export function pointInsideBand(
  topBoundary,
  bottomBoundary,
  getX = (point) => point.x,
  getY = (point) => point.y,
) {
  const top = numericPoints(topBoundary, getX, getY);
  const bottom = numericPoints(bottomBoundary, getX, getY);
  if (top.length < 2 || bottom.length < 2) return null;

  const left = Math.max(top[0].x, bottom[0].x);
  const right = Math.min(top[top.length - 1].x, bottom[bottom.length - 1].x);
  if (left > right) return null;

  const x = (left + right) / 2;
  const topY = yAtX(top, x);
  const bottomY = yAtX(bottom, x);
  if (!Number.isFinite(topY) || !Number.isFinite(bottomY)) return null;

  return { x, y: (topY + bottomY) / 2 };
}
