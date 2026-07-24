---
title: Pipeline architecture
audience: developer
status: current
source_files:
  - poggio_webapp/pipeline/preprocess.py
  - poggio_webapp/pipeline/extract_illustrator.py
  - poggio_webapp/pipeline/extract_fieldwall.py
  - poggio_webapp/pipeline/normalizer.py
  - poggio_webapp/pipeline/validator.py
  - poggio_webapp/pipeline/convert_coords.py
  - poggio_webapp/pipeline/build_gempy.py
  - poggio_webapp/pipeline/editor.py
verified_against: a8b58f1
---

# Pipeline architecture

The pipeline modules turn a drawing into normalized geometry, converted coordinates, and optionally a 3D model. They are organized by family rather than by a single monolithic step.

## Responsibilities

- Preprocess the source image or PDF into a working copy for later stages.
- Extract structured drawing data from either illustrator-style or field-wall-style sheets.
- Normalize and validate the extracted data before coordinate conversion.
- Convert the validated geometry into coordinate CSVs and, where available, build a GemPy model.
- Support the newer editor flow with its own session metadata, structural validation, and find logging.

## Inputs

- An uploaded scan or PDF.
- A chosen sheet type and any calibration or registration values entered by the user.
- Previously generated extraction or normalization outputs that later stages need.

## Outputs

- Working images and intermediate JSON files in the job folders.
- Normalized JSON, validation reports, and coordinate CSV outputs.
- Optional model files and meshes when the GemPy build step succeeds.

## Main source files

- `poggio_webapp/pipeline/preprocess.py`
- `poggio_webapp/pipeline/extract_illustrator.py`
- `poggio_webapp/pipeline/extract_fieldwall.py`
- `poggio_webapp/pipeline/normalizer.py`
- `poggio_webapp/pipeline/validator.py`
- `poggio_webapp/pipeline/convert_coords.py`
- `poggio_webapp/pipeline/build_gempy.py`
- `poggio_webapp/pipeline/editor.py`

## Failure boundaries

- Each stage writes into its own subfolder so a failure in one stage does not erase the earlier outputs.
- AI extraction and GemPy build depend on optional dependencies and credentials that are not part of the baseline runtime.
- Validation and coordinate conversion can fail when the input structure is incomplete or the registration values are not usable.
- The editor pipeline has its own validation logic and is not interchangeable with the older upload-based extraction path.

## Related tests

- `tests/test_editor_routes.py`
- `tests/test_editor_status.py`
- `tests/test_finds_routes.py`

## Related workflow pages

- [Prepare the image](../workflows/02-prepare-image.md)
- [Clean up the data](../workflows/04-clean-data.md)
- [Place on site](../workflows/06-place-on-site.md)

## Under the hood

The Flask routes in `poggio_webapp/backend/routes/preprocess.py`, `poggio_webapp/backend/routes/extraction.py`, `poggio_webapp/backend/routes/processing.py`, and `poggio_webapp/backend/routes/gempy.py` call the pipeline modules with the current job directory and metadata. The modules themselves stay focused on transformation logic and file output; the route layer remains responsible for request handling and persistence state.

The current documentation should therefore describe the pipeline as a set of families that compose into a workflow, not as a single fully automated path. Some pieces are supported by the visible UI, while others remain optional or backend-only depending on the runtime environment and the current frontend wiring.
