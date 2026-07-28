const SUPPORTED_SCHEMA_VERSION = 1;
const SUPPORTED_FORMAT = "raw";
const SUPPORTED_DTYPE = "uint16-le";
const SUPPORTED_LAYOUT = "C";
const SUPPORTED_AXES = Object.freeze(["x", "y", "z"]);
const MAX_UINT16 = 65535;

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function validatedShape(shape) {
  if (
    !Array.isArray(shape)
    || shape.length !== 3
    || !shape.every((value) => Number.isSafeInteger(value) && value > 0)
  ) {
    throw new TypeError("volume.shape must contain three positive integers");
  }

  const elementCount = shape.reduce((product, value) => product * value, 1);
  if (!Number.isSafeInteger(elementCount)) {
    throw new TypeError("volume.shape element count must be a safe integer");
  }
  return shape.slice();
}

function validatedExtent(extent) {
  if (
    !Array.isArray(extent)
    || extent.length !== 6
    || !extent.every((value) => typeof value === "number" && Number.isFinite(value))
  ) {
    throw new TypeError("extent must contain six finite numbers");
  }

  for (let axis = 0; axis < 3; axis += 1) {
    if (extent[axis * 2] >= extent[(axis * 2) + 1]) {
      throw new TypeError(
        `extent ${SUPPORTED_AXES[axis]} minimum must be less than maximum`,
      );
    }
  }
  return extent;
}

function validatedVolumeUrl(value) {
  const expected = "volume.url must be a same-origin /api/jobs/ URL";
  if (
    typeof value !== "string"
    || value.trim() !== value
    || !value.startsWith("/api/jobs/")
    || /[\u0000-\u0020\\]/u.test(value)
  ) {
    throw new TypeError(expected);
  }

  let parsed;
  try {
    parsed = new URL(value, "https://volume.invalid");
  } catch {
    throw new TypeError(expected);
  }
  if (
    parsed.origin !== "https://volume.invalid"
    || !parsed.pathname.startsWith("/api/jobs/")
  ) {
    throw new TypeError(expected);
  }
  return value;
}

function validatedLithologies(lithologies) {
  if (!Array.isArray(lithologies)) {
    throw new TypeError("volume.lithologies must be an array");
  }

  const seenIds = new Set();
  return lithologies.map((lithology, index) => {
    const path = `volume.lithologies[${index}]`;
    if (!isObject(lithology)) {
      throw new TypeError(`${path} must be an object`);
    }

    const { id, name } = lithology;
    if (!Number.isInteger(id) || id < 0 || id > MAX_UINT16) {
      throw new TypeError(
        `${path}.id must be an integer from 0 through ${MAX_UINT16}`,
      );
    }
    if (seenIds.has(id)) {
      throw new TypeError(`volume contains duplicate lithology id ${id}`);
    }
    if (typeof name !== "string" || name.trim() === "") {
      throw new TypeError(`${path}.name must be a non-empty string`);
    }

    seenIds.add(id);
    return { id, name };
  });
}

function validatedCoordinate(value, axis, dimension) {
  if (!Number.isInteger(value)) {
    throw new TypeError(`${axis} coordinate must be an integer`);
  }
  if (value < 0 || value >= dimension) {
    throw new RangeError(
      `${axis} coordinate ${value} is out of range (0 through ${dimension - 1})`,
    );
  }
  return value;
}

/**
 * Validate API volume metadata and return a detached, normalized copy.
 */
export function validateVolumeMetadata(raw) {
  if (!isObject(raw)) {
    throw new TypeError("volume metadata must be an object");
  }
  if (raw.schema_version !== SUPPORTED_SCHEMA_VERSION) {
    throw new TypeError("volume.schema_version must be 1");
  }
  if (raw.format !== SUPPORTED_FORMAT) {
    throw new TypeError('volume.format must be "raw"');
  }
  if (raw.dtype !== SUPPORTED_DTYPE) {
    throw new TypeError('volume.dtype must be "uint16-le"');
  }
  if (raw.layout !== SUPPORTED_LAYOUT) {
    throw new TypeError('volume.layout must be "C"');
  }
  if (
    !Array.isArray(raw.axes)
    || raw.axes.length !== SUPPORTED_AXES.length
    || raw.axes.some((axis, index) => axis !== SUPPORTED_AXES[index])
  ) {
    throw new TypeError('volume.axes must be ["x", "y", "z"]');
  }

  return {
    schema_version: SUPPORTED_SCHEMA_VERSION,
    format: SUPPORTED_FORMAT,
    dtype: SUPPORTED_DTYPE,
    layout: SUPPORTED_LAYOUT,
    axes: [...SUPPORTED_AXES],
    shape: validatedShape(raw.shape),
    url: validatedVolumeUrl(raw.url),
    lithologies: validatedLithologies(raw.lithologies),
  };
}

/**
 * Decode a raw little-endian uint16 payload without relying on host byte order.
 */
export function decodeUint16LE(arrayBuffer, expectedCount) {
  if (!(arrayBuffer instanceof ArrayBuffer)) {
    throw new TypeError("volume payload must be an ArrayBuffer");
  }
  if (
    !Number.isSafeInteger(expectedCount)
    || expectedCount < 0
    || expectedCount > Math.floor(Number.MAX_SAFE_INTEGER / 2)
  ) {
    throw new TypeError("expectedCount must be a non-negative safe integer");
  }
  if (arrayBuffer.byteLength % 2 !== 0) {
    throw new RangeError("volume payload byte length must be even");
  }

  const actualCount = arrayBuffer.byteLength / 2;
  if (actualCount !== expectedCount) {
    throw new RangeError(
      `volume payload contains ${actualCount} elements; expected ${expectedCount}`,
    );
  }

  const view = new DataView(arrayBuffer);
  const values = new Uint16Array(expectedCount);
  for (let index = 0; index < expectedCount; index += 1) {
    values[index] = view.getUint16(index * 2, true);
  }
  return values;
}

/**
 * Return the flat C-order index for shape [nx, ny, nz].
 */
export function volumeIndex(x, y, z, shape) {
  const [nx, ny, nz] = validatedShape(shape);
  const validX = validatedCoordinate(x, "x", nx);
  const validY = validatedCoordinate(y, "y", ny);
  const validZ = validatedCoordinate(z, "z", nz);
  return ((validX * ny) + validY) * nz + validZ;
}

/**
 * Return a cell's world-space center for extent
 * [xmin, xmax, ymin, ymax, zmin, zmax].
 */
export function cellCenter(x, y, z, shape, extent) {
  const validShape = validatedShape(shape);
  const validExtent = validatedExtent(extent);
  const [nx, ny, nz] = validShape;
  const coordinates = [
    validatedCoordinate(x, "x", nx),
    validatedCoordinate(y, "y", ny),
    validatedCoordinate(z, "z", nz),
  ];

  return coordinates.map((coordinate, axis) => {
    const minimum = validExtent[axis * 2];
    const maximum = validExtent[(axis * 2) + 1];
    const cellSize = (maximum - minimum) / validShape[axis];
    return minimum + ((coordinate + 0.5) * cellSize);
  });
}

/**
 * Normalize inclusive maximum slice indices.
 *
 * Omitted axes expose their complete range. A maximum of zero therefore
 * includes exactly the first cell along that axis.
 */
export function visibleCellRange(shape, slices = {}) {
  const validShape = validatedShape(shape);
  if (!isObject(slices)) {
    throw new TypeError("slices must be an object");
  }

  return Object.fromEntries(SUPPORTED_AXES.map((axis, index) => {
    const maximum = slices[axis] === undefined
      ? validShape[index] - 1
      : validatedCoordinate(slices[axis], `${axis} slice`, validShape[index]);
    return [axis, { min: 0, max: maximum }];
  }));
}

function validatedValues(values, expectedCount) {
  const isTypedArray = ArrayBuffer.isView(values) && !(values instanceof DataView);
  if (!Array.isArray(values) && !isTypedArray) {
    throw new TypeError("volume values must be an array or typed array");
  }
  if (values.length !== expectedCount) {
    throw new RangeError(
      `volume values contain ${values.length} elements; expected ${expectedCount}`,
    );
  }
  for (let index = 0; index < values.length; index += 1) {
    const value = values[index];
    if (
      typeof value !== "number"
      || !Number.isInteger(value)
      || value < 0
      || value > MAX_UINT16
    ) {
      throw new TypeError(
        `volume value at index ${index} must be an integer from 0 through ${MAX_UINT16}`,
      );
    }
  }
  return values;
}

/**
 * Group visible cells by numeric lithology ID.
 *
 * Groups are sorted numerically. Within each group, `[x, y, z]` coordinates
 * retain C-order traversal. IDs missing from the metadata receive the
 * conservative `Lithology <id>` fallback label.
 */
export function groupCellsByLithology(values, metadata, slices = {}) {
  const volume = validateVolumeMetadata(metadata);
  const [nx, ny, nz] = volume.shape;
  const expectedCount = nx * ny * nz;
  const validValues = validatedValues(values, expectedCount);
  const range = visibleCellRange(volume.shape, slices);
  const namesById = new Map(
    volume.lithologies.map(({ id, name }) => [id, name]),
  );
  const cellsById = new Map();

  for (let x = range.x.min; x <= range.x.max; x += 1) {
    for (let y = range.y.min; y <= range.y.max; y += 1) {
      for (let z = range.z.min; z <= range.z.max; z += 1) {
        const index = ((x * ny) + y) * nz + z;
        const id = validValues[index];
        if (!cellsById.has(id)) {
          cellsById.set(id, []);
        }
        cellsById.get(id).push([x, y, z]);
      }
    }
  }

  return [...cellsById.entries()]
    .sort(([firstId], [secondId]) => firstId - secondId)
    .map(([id, cells]) => ({
      id,
      name: namesById.get(id) ?? `Lithology ${id}`,
      cells,
    }));
}
