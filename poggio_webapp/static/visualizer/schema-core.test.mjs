// Run with: node poggio_webapp/static/visualizer/schema-core.test.mjs
import assert from "node:assert/strict";
import { ingest } from "./schema-core.mjs";

function test(name, callback) {
  callback();
  console.log(`✓ ${name}`);
}

function fieldWallPoint(overrides = {}) {
  return {
    xMeters: 1,
    depthMeters: 0.5,
    confidence: "human-traced",
    ...overrides,
  };
}

function fieldWallInput(layer) {
  return {
    faceLabel: "north",
    layers: [layer],
  };
}

function firstLayer(input) {
  return ingest(input).trenchProfiles[0].layers[0];
}

test("field-wall top boundary preserves sourcePixel", () => {
  const sourcePixel = [200, 250];
  const layer = firstLayer(fieldWallInput({
    topBoundary: [fieldWallPoint({ sourcePixel })],
  }));

  assert.deepEqual(layer.topBoundary[0], {
    xCoordinateMeters: 1,
    yCoordinateMeters: 0.5,
    confidence: "human-traced",
    sourcePixel: [200, 250],
  });
  assert.equal(layer.topBoundary[0].sourcePixel, sourcePixel);
});

test("field-wall bottom boundary preserves sourcePixel", () => {
  const sourcePixel = [210, 275];
  const layer = firstLayer(fieldWallInput({
    bottomBoundary: [fieldWallPoint({ sourcePixel })],
  }));

  assert.deepEqual(layer.bottomBoundary[0], {
    xCoordinateMeters: 1,
    yCoordinateMeters: 0.5,
    confidence: "human-traced",
    sourcePixel: [210, 275],
  });
  assert.equal(layer.bottomBoundary[0].sourcePixel, sourcePixel);
});

test("field-wall feature shape preserves sourcePixel", () => {
  const sourcePixel = [225, 300];
  const layer = firstLayer(fieldWallInput({
    featuresInLayer: [{
      feature: "stone",
      shapePoints: [fieldWallPoint({ sourcePixel })],
    }],
  }));

  assert.deepEqual(layer.featuresInLayer[0].shapePoints[0], {
    xCoordinateMeters: 1,
    yCoordinateMeters: 0.5,
    confidence: "human-traced",
    sourcePixel: [225, 300],
  });
  assert.equal(layer.featuresInLayer[0].shapePoints[0].sourcePixel, sourcePixel);
});

test("illustrator-shaped input preserves sourcePixel", () => {
  const sourcePixel = [120.25, 260.5];
  const input = {
    trenchProfiles: [{
      face: "north",
      layers: [{
        topBoundary: [{
          xCoordinateMeters: 0.2,
          yCoordinateMeters: 0.6,
          confidence: "human-traced",
          sourcePixel,
        }],
      }],
    }],
  };

  const result = ingest(input);

  assert.equal(result, input);
  assert.equal(
    result.trenchProfiles[0].layers[0].topBoundary[0].sourcePixel,
    sourcePixel,
  );
});

test("input without sourcePixel remains supported", () => {
  const layer = firstLayer(fieldWallInput({
    topBoundary: [fieldWallPoint()],
  }));

  assert.deepEqual(layer.topBoundary[0], {
    xCoordinateMeters: 1,
    yCoordinateMeters: 0.5,
    confidence: "human-traced",
  });
});

test("alternate metre field names still adapt correctly", () => {
  const layer = firstLayer(fieldWallInput({
    topBoundary: [{
      xCoordinateMeters: 1.25,
      yCoordinateMeters: 0.75,
      confidence: "model",
    }],
  }));

  assert.deepEqual(layer.topBoundary[0], {
    xCoordinateMeters: 1.25,
    yCoordinateMeters: 0.75,
    confidence: "model",
  });
});

test("ingest does not invent sourcePixel", () => {
  const layer = firstLayer(fieldWallInput({
    topBoundary: [fieldWallPoint()],
    bottomBoundary: [fieldWallPoint({ depthMeters: 1 })],
    featuresInLayer: [{
      feature: "stone",
      shapePoints: [fieldWallPoint({ xMeters: 2 })],
    }],
  }));
  const points = [
    ...layer.topBoundary,
    ...layer.bottomBoundary,
    ...layer.featuresInLayer[0].shapePoints,
  ];

  points.forEach(point => {
    assert.equal(
      Object.prototype.hasOwnProperty.call(point, "sourcePixel"),
      false,
    );
  });
});
