---
title: Create the model
audience: beginner
status: current
source_files:
  - poggio_webapp/pipeline/build_gempy.py
  - poggio_webapp/backend/routes/gempy.py
verified_against: a8b58f1
---

# Create the model

Build a GemPy model from the converted point and orientation exports, while keeping the output clearly marked as a placeholder example when you use synthetic values.

> [!warning]
> Synthetic documentation example only. The generated model is a smoke-test output and is not a scientific model.

## Before you start

You need the converted CSV files from the registration step. The full GemPy build is optional in the repository: the core app can run without `gempy` and `gempy_viewer`, but the model step needs them installed to build and render the 3D outputs.

## Do this

1. Start the model build from the job results.
   - Action: use the point and orientation CSVs created in the previous step.
   - Artifact: a GemPy project file and related model outputs.
2. Review the build settings.
   - Series order: the app can infer the order from the surface elevations, or you can supply the order explicitly. Keep the order simple for a placeholder example.
   - Resolution: the default build uses a $50 \times 50 \times 30$ grid.
   - Extent: the app infers an extent from the point data and padding values unless you provide one.
   - Section direction: the default is `y`.
   - Vertical exaggeration: the default is `5.0`.
3. Let the build finish.
   - Artifact: a `.gempy` file, a lith-block file, mesh files, and section images.

### Synthetic example

For a documentation walkthrough, use a simple synthetic surface order such as `Layer A; Layer B` and keep the rest of the parameters at the defaults. Do not present the output as an archaeological interpretation.

## What the application creates

- `trench_model.gempy`
- `trench_model_lith_block.npz`
- one or more `.obj` mesh files in a meshes folder
- a section image such as `trench_model_section_y.png`
- an optional zoomed section image when the builder can create it

## Check your result

- The model file exists in the job folder.
- The section image and other outputs are present or the build logs explain why one was skipped.
- The output is clearly treated as a placeholder example rather than a scientific result.

## Common problems

- `gempy` or `gempy_viewer` is not installed, so the model step cannot render the section image.
- The supplied series order does not match the surface names in the CSV, so the build stops with an error.
- The build produces a section image but you assume the plot proves the geology; the plot is only a visualization aid.

## Under the hood

The build step in `poggio_webapp/pipeline/build_gempy.py` reads the converted CSVs, creates a GemPy model, saves the model file, writes a lith block, exports meshes, and optionally renders section images. The plot step can fail independently of the model computation, so a missing image does not always mean the model build failed.

## Next

Continue to [View and download](08-view-and-download.md) to inspect the outputs and export the traced data.
