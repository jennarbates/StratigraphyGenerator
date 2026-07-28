import assert from "node:assert/strict";
import test from "node:test";

import {
  modelRendererTypeModel,
  viewModeModel,
} from "./view-mode.mjs";

test("no model exposes only the 2D mode", () => {
  assert.deepEqual(
    viewModeModel({
      hasModel3d: false,
      hasExtraction: false,
      openedFromJob: false,
    }),
    {
      mode: "2d",
      canSelect2d: true,
      canSelect3d: false,
      show2dControls: true,
      show3dControls: false,
    },
  );
});

test("a job with a model and extraction defaults to 3D", () => {
  assert.deepEqual(
    viewModeModel({
      hasModel3d: true,
      hasExtraction: true,
      openedFromJob: true,
    }),
    {
      mode: "3d",
      canSelect2d: true,
      canSelect3d: true,
      show2dControls: false,
      show3dControls: true,
    },
  );
});

test("model-only job data initializes the 3D mode", () => {
  assert.deepEqual(
    viewModeModel({
      hasModel3d: true,
      hasExtraction: false,
      openedFromJob: true,
    }),
    {
      mode: "3d",
      canSelect2d: false,
      canSelect3d: true,
      show2dControls: false,
      show3dControls: true,
    },
  );
});

test("explicit switches select the matching view and control group", () => {
  const common = {
    hasModel3d: true,
    hasExtraction: true,
    openedFromJob: true,
  };

  assert.deepEqual(
    viewModeModel({ ...common, requestedMode: "2d" }),
    {
      mode: "2d",
      canSelect2d: true,
      canSelect3d: true,
      show2dControls: true,
      show3dControls: false,
    },
  );
  assert.deepEqual(
    viewModeModel({ ...common, requestedMode: "3d" }),
    {
      mode: "3d",
      canSelect2d: true,
      canSelect3d: true,
      show2dControls: false,
      show3dControls: true,
    },
  );
});

test("a rejected invalid model leaves valid extraction in 2D", () => {
  assert.deepEqual(
    viewModeModel({
      hasModel3d: false,
      hasExtraction: true,
      openedFromJob: true,
      requestedMode: "3d",
    }),
    {
      mode: "2d",
      canSelect2d: true,
      canSelect3d: false,
      show2dControls: true,
      show3dControls: false,
    },
  );
});

test("surface rendering remains the default when surfaces and volume exist", () => {
  assert.deepEqual(
    modelRendererTypeModel({
      hasSurfaces: true,
      hasVolume: true,
    }),
    {
      type: "surfaces",
      canSelectSurfaces: true,
      canSelectVolume: true,
      showSurfaceControls: true,
      showVolumeControls: false,
    },
  );
});

test("renderer type selection exposes only the matching 3D controls", () => {
  assert.deepEqual(
    modelRendererTypeModel({
      hasSurfaces: true,
      hasVolume: true,
      requestedType: "volume",
    }),
    {
      type: "volume",
      canSelectSurfaces: true,
      canSelectVolume: true,
      showSurfaceControls: false,
      showVolumeControls: true,
    },
  );
  assert.deepEqual(
    modelRendererTypeModel({
      hasSurfaces: true,
      hasVolume: false,
      requestedType: "surfaces",
    }),
    {
      type: "surfaces",
      canSelectSurfaces: true,
      canSelectVolume: false,
      showSurfaceControls: true,
      showVolumeControls: false,
    },
  );
});

test("a volume-only model selects the volume renderer", () => {
  assert.deepEqual(
    modelRendererTypeModel({
      hasSurfaces: false,
      hasVolume: true,
    }),
    {
      type: "volume",
      canSelectSurfaces: false,
      canSelectVolume: true,
      showSurfaceControls: false,
      showVolumeControls: true,
    },
  );
});

test("renderer selection rejects unavailable or invalid states", () => {
  assert.throws(
    () => modelRendererTypeModel({
      hasSurfaces: false,
      hasVolume: false,
    }),
    /at least one 3D renderer must be available/,
  );
  assert.throws(
    () => modelRendererTypeModel({
      hasSurfaces: true,
      hasVolume: true,
      requestedType: "voxels",
    }),
    /requestedType must be null, "surfaces", or "volume"/,
  );
});
