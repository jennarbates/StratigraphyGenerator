function requireObject(value, name) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError(`${name} must be an object.`);
  }
}

function requireFiniteNumber(value, name) {
  if (!Number.isFinite(value)) {
    throw new TypeError(`${name} must be a finite number.`);
  }
  return value;
}

function requirePixelPair(value, name) {
  if (!Array.isArray(value) || value.length !== 2) {
    throw new TypeError(`${name} must be a two-number array.`);
  }

  return {
    x: requireFiniteNumber(value[0], `${name}[0]`),
    y: requireFiniteNumber(value[1], `${name}[1]`),
  };
}

function meterCoordinates(point) {
  requireObject(point, "point");

  const hasFieldWallCoordinate = (
    Object.prototype.hasOwnProperty.call(point, "xMeters")
    || Object.prototype.hasOwnProperty.call(point, "depthMeters")
  );

  if (hasFieldWallCoordinate) {
    return {
      x: requireFiniteNumber(point.xMeters, "point.xMeters"),
      depth: requireFiniteNumber(point.depthMeters, "point.depthMeters"),
    };
  }

  const hasIllustratorCoordinate = (
    Object.prototype.hasOwnProperty.call(point, "xCoordinateMeters")
    || Object.prototype.hasOwnProperty.call(point, "yCoordinateMeters")
  );

  if (hasIllustratorCoordinate) {
    return {
      x: requireFiniteNumber(
        point.xCoordinateMeters,
        "point.xCoordinateMeters",
      ),
      depth: requireFiniteNumber(
        point.yCoordinateMeters,
        "point.yCoordinateMeters",
      ),
    };
  }

  throw new TypeError(
    "point must contain xMeters and depthMeters, or "
      + "xCoordinateMeters and yCoordinateMeters.",
  );
}

function projectMeters(point, axes) {
  const coordinates = meterCoordinates(point);
  const xPixels = coordinates.x * axes.pxPerMeter;
  const depthPixels = coordinates.depth * axes.pxPerMeter;

  return {
    x: axes.origin.x + (xPixels * axes.u.x) + (depthPixels * axes.v.x),
    y: axes.origin.y + (xPixels * axes.u.y) + (depthPixels * axes.v.y),
  };
}

function projectPoint(point, axes) {
  requireObject(point, "point");

  if (Object.prototype.hasOwnProperty.call(point, "sourcePixel")) {
    return requirePixelPair(point.sourcePixel, "point.sourcePixel");
  }

  return projectMeters(point, axes);
}

export function calibrationAxes(calibration) {
  requireObject(calibration, "calibration");

  if (
    calibration.kind !== undefined
    && calibration.kind !== "manual"
  ) {
    throw new TypeError('calibration.kind must be "manual" when provided.');
  }

  const origin = requirePixelPair(
    calibration.origin_px,
    "calibration.origin_px",
  );
  const reference = requirePixelPair(
    calibration.ref_px,
    "calibration.ref_px",
  );
  const lowest = requirePixelPair(
    calibration.lowest_px,
    "calibration.lowest_px",
  );
  const pxPerMeter = requireFiniteNumber(
    calibration.px_per_m,
    "calibration.px_per_m",
  );

  if (pxPerMeter <= 0) {
    throw new RangeError("calibration.px_per_m must be greater than zero.");
  }

  if (calibration.ref_meters !== undefined) {
    const referenceMeters = requireFiniteNumber(
      calibration.ref_meters,
      "calibration.ref_meters",
    );
    if (referenceMeters <= 0) {
      throw new RangeError(
        "calibration.ref_meters must be greater than zero.",
      );
    }
  }

  const referenceX = reference.x - origin.x;
  const referenceY = reference.y - origin.y;
  const referenceLength = Math.hypot(referenceX, referenceY);

  if (referenceLength === 0) {
    throw new RangeError(
      "calibration origin_px and ref_px must be different points.",
    );
  }

  const u = {
    x: referenceX / referenceLength,
    y: referenceY / referenceLength,
  };
  let v = {
    x: -u.y,
    y: u.x,
  };
  const lowestX = lowest.x - origin.x;
  const lowestY = lowest.y - origin.y;

  if ((lowestX * v.x) + (lowestY * v.y) < 0) {
    v = { x: -v.x, y: -v.y };
  }

  return {
    origin,
    u,
    v,
    pxPerMeter,
  };
}

export function metersToSourcePixel(point, calibration) {
  return projectMeters(point, calibrationAxes(calibration));
}

export function pointToSourcePixel(point, calibration) {
  return projectPoint(point, calibrationAxes(calibration));
}

export function projectPolyline(points, calibration) {
  if (!Array.isArray(points)) {
    throw new TypeError("points must be an array.");
  }

  const axes = calibrationAxes(calibration);
  return points.map((point) => projectPoint(point, axes));
}
